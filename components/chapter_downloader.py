#!/usr/bin/python3
import asyncio
import html
import json
import os
import re
from datetime import datetime
from typing import Type, Union

import requests
from aiohttp import ClientSession, ClientError
from tqdm import tqdm

from .constants import ImpVar, RequestAPI
from .exporter import ArchiveExporter, FolderExporter
from .response_pb2 import Response

headers = ImpVar.HEADERS
domain = ImpVar.MANGADEX_API_URL
re_regrex = re.compile(ImpVar.REGEX)


# Get the MangaPlus api link
def mplusIDChecker(chapter_data: dict) -> str:
    mplus_url = re.compile(r'(?:https:\/\/mangaplus\.shueisha\.co\.jp\/viewer\/)([0-9]+)')
    mplus_id = mplus_url.match(chapter_data["pages"]).group(1)
    url = f'https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer?chapter_id={mplus_id}&split=no&img_quality=super_high'
    return url


# Decrypt the images to download
def mplusDecryptImage(url: str, encryption_hex: str) -> bytearray:
    resp = requests.get(url)
    data = bytearray(resp.content)
    key = bytes.fromhex(encryption_hex)
    a = len(key)
    for s in range(len(data)):
        data[s] ^= key[s % a]
    return data


# Check if all the images are downloaded
def checkExist(pages: list, exporter: Type[Union[ArchiveExporter, FolderExporter]]) -> bool:
    # pylint: disable=unsubscriptable-object
    exists = 0

    # Only image files are counted
    if isinstance(exporter, ArchiveExporter):
        zip_count = [i for i in exporter.archive.namelist() if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    else:
        zip_count = [i for i in os.listdir(exporter.folder_path) if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    if len(pages) == len(zip_count):
        exists = 1
    return exists


# Display progress bar of downloaded images
async def displayProgress(tasks: list):
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=(str(datetime.now(tz=None))[:-7])):
        try:
            await f
        except ConnectionResetError:
            pass
        except Exception as e:
            print(e)
    return


# Download the MD chapter images
async def imageDownloader(
        url: str,
        fallback_url: str,
        image: str,
        pages: list,
        exporter: Type[Union[ArchiveExporter, FolderExporter]]):
    # pylint: disable=unsubscriptable-object
    retry = 0
    fallback_retry = 0
    retry_max_times = 3

    # Try to download it retry_max_times times
    while retry < retry_max_times:
        async with ClientSession() as session:
            try:
                async with session.get(url + image) as response:

                    assert response.status == 200
                    response = await response.read()

                    page_no = pages.index(image) + 1
                    extension = image.split('.', 1)[1]

                    # Add image to archive
                    exporter.addImage(response, page_no, extension)

                    retry = retry_max_times
                    return

            except (ClientError, AssertionError, ConnectionResetError, asyncio.TimeoutError):
                await asyncio.sleep(3)

                retry += 1

                if retry == retry_max_times:
                    if fallback_url != '' and fallback_retry == 0:
                        retry = 0
                        fallback_retry = 1
                        url = fallback_url
                        print(f'Retrying with the fallback url.')
                    else:
                        print(f'Could not download image {image} after {retry} times.')
                        return


# download_type 0 -> chapter
# download_type 1 -> title
# download_type 2 -> group/user
def chapterDownloader(md_model):
    chapter_id = md_model.id

    # Connect to API and get chapter info
    response = RequestAPI.requestData(md_model, **{'saver': '0'})
    RequestAPI.checkForError(chapter_id, response)
    chapter_data = RequestAPI.getData(response)
    md_model.chapter_data = chapter_data

    # Make sure only downloadable chapters are downloaded
    if chapter_data["status"] not in ('OK', 'external', 'delayed'):
        return
    # Only MangaPlus external chapters supported
    elif chapter_data["status"] == 'external' and 'https://mangaplus.shueisha.co.jp/viewer/' not in chapter_data["pages"]:
        print('Chapter external to MangaDex, skipping...')
        return
    # Delayed chapters can't be downloaded
    elif chapter_data["status"] == 'delayed':
        print('Delayed chapter, skipping...')
        return

    if chapter_data["status"] == 'external':
        external = True
    else:
        external = False

    # chapter, group, user downloads
    if md_model.type_id == 0:
        title = re_regrex.sub('_', html.unescape(chapter_data["mangaTitle"]))
        title = title.rstrip(' .')
        md_model.title = title
        md_model.route = os.path.join(md_model.route, title)

    md_model.prefix = md_model.chapter_prefix_dict.get(chapter_data["volume"], 'c')

    # Make the files
    if md_model.make_folder:
        exporter = FolderExporter(md_model)
    else:
        exporter = ArchiveExporter(md_model)
    
    # Add chapter data to the json for title, group or user downloads
    if md_model.type_id in (1, 2):
        md_model.title_json.chapters(chapter_data)
        if md_model.type_id == 2:
            md_model.account_json.chapters(chapter_data)

    print(f'Downloading {title} | Volume: {chapter_data["volume"]} | Chapter: {chapter_data["chapter"]} | Title: {chapter_data["title"]}')

    # External chapters
    if external:
        # Call MangaPlus downloader
        print('External chapter. Connecting to MangaPlus to download.')

        url = mplusIDChecker(chapter_data)
        response = requests.get(url)

        viewer = Response.FromString(response.content).success.manga_viewer
        pages = [p.manga_page for p in viewer.pages if p.manga_page.image_url]
    else:
        url = f'{chapter_data["server"]}{chapter_data["hash"]}/'
        fallback_url = f'{chapter_data["serverFallback"]}{chapter_data["hash"]}/' if 'serverFallback' in chapter_data else ''
        pages = chapter_data["pages"]

    # Check if the chapter has been downloaded already
    exists = checkExist(pages, exporter)

    if exists:
        print('File already downloaded.')
        if md_model.type_id in (1, 2):
            md_model.title_json.core()
            if md_model.type_id == 2:
                md_model.account_json.core()
        exporter.close()
        return

    if external:
        for page in tqdm(pages, desc=(str(datetime.now(tz=None))[:-7])):
            image = mplusDecryptImage(page.image_url, page.encryption_key)
            page_no = pages.index(page) + 1
            exporter.addImage(image, page_no, '.jpg')
    else:
        # ASYNC FUNCTION
        loop  = asyncio.get_event_loop()
        tasks = []

        # Download images
        for image in pages:
            task = asyncio.ensure_future(imageDownloader(url, fallback_url, image, pages, exporter))
            tasks.append(task)

        runner = displayProgress(tasks)
        loop.run_until_complete(runner)

    downloaded_all = checkExist(pages, exporter)

    # If all the images are downloaded, save the json file with the latest downloaded chapter
    if downloaded_all and md_model.type_id in (1, 2):
        md_model.title_json.core()
        if md_model.type_id == 2:
            md_model.account_json.core()

    # Close the archive
    exporter.close()
    del exporter
    return
