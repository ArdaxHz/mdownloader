#!/usr/bin/python3
import asyncio
from components.mangaplus import MangaPlus
import html
import json
import os
import re
from datetime import datetime
from typing import Type, Union

import requests
from aiohttp import ClientSession, ClientError
from tqdm import tqdm

from .constants import ImpVar
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
    response = md_model.requestData(chapter_id, 'chapter')
    md_model.checkForError(chapter_id, response)
    data = md_model.getData(response)
    md_model.chapter_data = data

    # Make sure only downloadable chapters are downloaded
    if data["result"] not in ('ok', 'external', 'delayed'):
        return
    # Only MangaPlus external chapters supported
    elif data["result"] == 'external':
        print('Chapter external to MangaDex, skipping...')
        return
    # Delayed chapters can't be downloaded
    elif data["result"] == 'delayed':
        print('Delayed chapter, skipping...')
        return
    
    if data["result"] == 'external':
        external = True
    else:
        external = False

    chapter_data = data["data"]["attributes"]

    # chapter, group, user downloads
    if md_model.type_id == 0:
        manga_id = [c["id"] for c in data["relationships"] if c["type"] == 'manga'][0]
        manga_response = requests.get(f'{domain}/manga/{manga_id}')
        if manga_response.status_code in range(200, 300):
            manga_data = manga_response.json()
            title = manga_data["data"]["attributes"]["title"]["en"]
            title = re_regrex.sub('_', html.unescape(title)).rstrip(' .')

    md_model.prefix = md_model.chapter_prefix_dict.get(chapter_data["volume"], 'c')

    # Make the files
    if md_model.make_folder:
        exporter = FolderExporter(md_model)
    else:
        exporter = ArchiveExporter(md_model)
    
    md_model.exporter = exporter
    
    # Add chapter data to the json for title, group or user downloads
    if md_model.type_id in (1, 2):
        md_model.title_json.chapters(chapter_data)
        if md_model.type_id == 2:
            md_model.account_json.chapters(chapter_data)

    print(f'Downloading "" | Volume: {chapter_data["volume"]} | Chapter: {chapter_data["chapter"]} | Title: {chapter_data["title"]}')

    # External chapters
    if external:
        # Call MangaPlus downloader
        print('External chapter. Connecting to MangaPlus to download.')
        MangaPlus(md_model).plusImages()
        return

    url_response = md_model.session.get(f"{ImpVar.MANGADEX_API_URL.format('at-home', 'server')}{chapter_id}")
    url = f'{url_response.json()["baseUrl"]}/data/{chapter_data["hash"]}/'
    pages = chapter_data["data"]

    # Check if the chapter has been downloaded already
    exists = md_model.checkExist(pages, exporter)
    md_model.existsBeforeDownload(exists)

    # ASYNC FUNCTION
    loop  = asyncio.get_event_loop()
    tasks = []

    # Download images
    for image in pages:
        task = asyncio.ensure_future(imageDownloader(url, '', image, pages, exporter))
        tasks.append(task)

    runner = displayProgress(tasks)
    loop.run_until_complete(runner)

    downloaded_all = md_model.checkExist(pages, exporter)
    md_model.existsAfterDownload(downloaded_all)
    return
