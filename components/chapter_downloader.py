#!/usr/bin/python3
import asyncio
import html
import os
import re
from datetime import datetime
from typing import Optional, Type, Union

import requests
from aiohttp import ClientSession, ClientError
from tqdm import tqdm

from . import constants
from .exporter import ArchiveExporter, FolderExporter
from .jsonmaker import AccountJson, TitleJson
from .response_pb2 import Response

headers = constants.HEADERS
domain = constants.MANGADEX_API_URL
re_regrex = re.compile(constants.REGEX)


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
        image: str,
        pages: list,
        exporter: Type[Union[ArchiveExporter, FolderExporter]]):
    # pylint: disable=unsubscriptable-object
    retry = 0

    # Try to download it 5 times
    while retry < 5:
        async with ClientSession() as session:
            try:
                async with session.get(url + image) as response:

                    assert response.status == 200
                    response = await response.read()

                    page_no = pages.index(image) + 1
                    extension = image.split('.', 1)[1]

                    # Add image to archive
                    exporter.addImage(response, page_no, extension)

                    retry = 5
                    return

            except (ClientError, AssertionError, ConnectionResetError, asyncio.TimeoutError):
                await asyncio.sleep(3)

                retry += 1

                if retry == 5:
                    print(f'Could not download image {image} after 5 times.')
                    return


# download_type 0 -> chapter
# download_type 1 -> title
# download_type 2 -> group/user
def chapterDownloader(
        chapter_id: Union[int, str],
        route: str,
        save_format: str,
        make_folder: bool,
        add_data: bool,
        chapter_prefix_dict: dict={},
        download_type: int=0,
        title: Optional[str]='',
        title_json: Optional[Type[TitleJson]]=None,
        account_json: Optional[Type[AccountJson]]=None):
    # pylint: disable=unsubscriptable-object

    # Connect to API and get chapter info
    params = {'saver': '0'}
    url = domain.format('chapter', chapter_id)
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        if response.status_code >= 500: # Unknown Error
            print(f"{chapter_id} - Something went wrong. Error: {response.status_code}")
        if response.status_code == 451: # Unavailable chapters
            print(f"{chapter_id} - Unavailable Chapter. This could be because the chapter was deleted by the group or you're not allowed to read it. Error: {response.status_code}")
        elif response.status_code == 403: # Restricted Chapters. Like korean webtoons
            print(f"{chapter_id} - Restricted Chapter. You're not allowed to read this chapter. Error: {response.status_code}")
        elif response.status_code == 410: # Deleted Chapters.
            print(f"{chapter_id} - Deleted Chapter. Error: {response.status_code}")
        else:
            print(f"{chapter_id} - Chapter ID doesn't exist. Error: {response.status_code}")
        return

    chapter_data = response.json()
    chapter_data = chapter_data["data"]

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
    if download_type == 0:
        title = re_regrex.sub('_', html.unescape(chapter_data["mangaTitle"]))

        title = title.rstrip()
        title = title.rstrip('.')
        title = title.rstrip()

    series_route = os.path.join(route, title)
    chapter_prefix = chapter_prefix_dict.get(chapter_data["volume"], 'c')

    # Make the files
    if make_folder:
        exporter = FolderExporter(title, chapter_data, series_route, chapter_prefix, add_data)
    else:
        exporter = ArchiveExporter(title, chapter_data, series_route, chapter_prefix, add_data, save_format)
    
    # Add chapter data to the json for title, group or user downloads
    if download_type in (1, 2):
        title_json.chapters(chapter_data)
        if download_type == 2:
            account_json.chapters(chapter_data)

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
        pages = chapter_data["pages"]

    # Check if the chapter has been downloaded already
    exists = checkExist(pages, exporter)

    if exists:
        print('File already downloaded.')
        if download_type in (1, 2):
            title_json.core()
            if download_type == 2:
                account_json.core()
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
            task = asyncio.ensure_future(imageDownloader(url, image, pages, exporter))
            tasks.append(task)

        runner = displayProgress(tasks)
        loop.run_until_complete(runner)

    downloaded_all = checkExist(pages, exporter)

    # If all the images are downloaded, save the json file with the latest downloaded chapter
    if downloaded_all and download_type in (1, 2):
        title_json.core()
        if download_type == 2:
            account_json.core()

    # Close the archive
    exporter.close()
    del exporter
    return
