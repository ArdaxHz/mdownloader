#!/usr/bin/python3
import asyncio
import html
import json
import os
import re
from datetime import datetime
from typing import Optional, Type, Union

import requests
from aiohttp import ClientSession, ClientError
from tqdm import tqdm

from .__version__ import __version__
from .exporter import ArchiveExporter, FolderExporter
from .jsonmaker import AccountJson, TitleJson
from .mangaplus import MangaPlus

headers = {'User-Agent': f'mDownloader/{__version__}'}
domain  = 'https://api.mangadex.org/v2'
re_regrex = re.compile('[\\\\/:*?"<>|]')


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


async def imageDownloader(
        url: str,
        fallback_url: str,
        image: str,
        pages: list,
        exporter: Type[Union[ArchiveExporter, FolderExporter]]):
    # pylint: disable=unsubscriptable-object
    retry = 0
    fallback_retry = 0

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
                    if fallback_url != '' and fallback_retry == 0:
                        retry = 0
                        fallback_retry = 1
                        url = fallback_url
                    else:
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
        json_file: Optional[Type[Union[AccountJson, TitleJson]]]=None,
        title: Optional[str]=''):
    # pylint: disable=unsubscriptable-object

    # Connect to API and get chapter info
    url = f'{domain}/chapter/{chapter_id}?saver=0'
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        if response.status_code >= 500: # Unknown Error
            print(f"Something went wrong. Error: {response.status_code}")
        if response.status_code == 451: # Unavailable chapters
            print(f"Unavailable Chapter. This could be because the chapter was deleted by the group or you're not allowed to read it. Error: {response.status_code}")
        elif response.status_code == 403: # Restricted Chapters. Like korean webtoons
            print(f"Restricted Chapter. You're not allowed to read this chapter. Error: {response.status_code}")
        elif response.status_code == 410: # Deleted Chapters.
            print(f"Deleted Chapter. Error: {response.status_code}")
        else:
            print(f"Chapter ID doesn't exist. Error: {response.status_code}")
        return
    else:
        chapter_data = response.json()
        chapter_data = chapter_data["data"]

        # Make sure only downloadable chapters are downloaded
        if chapter_data["status"] not in ('OK', 'external', 'delayed'):
            return
        # Only MangaPlus external chapters supported
        elif chapter_data["status"] == 'external' and r'https://mangaplus.shueisha.co.jp/viewer/' not in chapter_data["pages"]:
            print('Chapter external to MangaDex, skipping...')
            return
        # Delayed chapters can't be downloaded
        elif chapter_data["status"] == 'delayed':
            print('Delayed chapter, skipping...')
            return

        #chapter, group, user downloads
        if download_type in (0, 2):
            title = re_regrex.sub('_', html.unescape(chapter_data["mangaTitle"]))

            title = title.rstrip()
            title = title.rstrip('.')
            title = title.rstrip()

        series_route = os.path.join(route, title)

        chapter_prefix = chapter_prefix_dict.get(chapter_data["volume"], 'c')

        # Make the file names
        if make_folder:
            exporter = FolderExporter(title, chapter_data, series_route, chapter_prefix, add_data)
        else:
            exporter = ArchiveExporter(title, chapter_data, series_route, chapter_prefix, add_data, save_format)
        
        # Add chapter data to the json for title, group or user downloads
        if download_type in (1, 2):
            json_file.chapters(chapter_data)

        print(f'Downloading {title} | Volume: {chapter_data["volume"]} | Chapter: {chapter_data["chapter"]} | Title: {chapter_data["title"]}')

        #External chapters
        if chapter_data["status"] == 'external':
            # Call MangaPlus downloader
            print('External chapter... Connecting to MangaPlus to download...')
            MangaPlus(chapter_data, download_type, exporter, json_file).plusImages()
            return
        else:
            url = f'{chapter_data["server"]}{chapter_data["hash"]}/'
            fallback_url = ''
            pages = chapter_data["pages"]
            exists = checkExist(pages, exporter)

            if 'serverFallback' in chapter_data:
                fallback_url = f'{chapter_data["serverFallback"]}{chapter_data["hash"]}/'

            # Check if the chapter has been downloaded already
            if exists:
                print('File already downloaded.')
                if download_type in (1, 2):
                    json_file.core(0)
                exporter.close()
                return

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
            if downloaded_all and download_type in (1, 2):
                json_file.core(0)

            # Close the archive
            exporter.close()
            return


def bulkDownloader(
        id: str,
        language: str,
        route: str,
        form: str,
        save_format: str,
        make_folder: bool,
        covers: bool,
        add_data: bool):
   
    # Connect to API and get info
    url = f'{domain}/{form}/{id}?include=chapters'
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"{form.title()} {id} doesn't exist. Request status error: {response.status_code}. Skipping...")
        return

    data = response.json()
    data = data["data"]
    chapter_count = 0

    # Get the names and amount of chapters
    if form in ('title', 'manga'):
        download_type = 1
        chapter_count = len(data["chapters"])
        title = re_regrex.sub('_', html.unescape(data["manga"]["title"]))
        title = title.rstrip()
        title = title.rstrip('.')
        title = title.rstrip()
        name = title

        series_route = os.path.join(route, title)
    else:
        download_type = 2
        name = data["group"]["name"] if form == 'group' else data["user"]["username"]
        chapter_count = data["group"]["chapters"] if form == 'group' else data["user"]["uploads"]

    # Skip titles/groups/users without chapters
    if not data["chapters"]:
        print(f'{form.title()} {id} - {name} has no chapters.')
        return

    print(f'{"-"*69}\nDownloading {form.title()}: {name}\n{"-"*69}')

    # Filter out the unwanted chapters
    chapters = [c for c in data["chapters"] if c["language"] == language]

    volume_dict = {}
    chapter_prefix_dict = {}

    # No chapters in the selected language
    if not chapters:
        print(f'No chapters found in the selected language, {language}.')
        return

    # Sort each chapter into volumes
    for c in chapters:
        manga_id = c["mangaId"]
        volume_no = c["volume"]
        try:
            volume_dict[manga_id][volume_no].append(c["chapter"])
        except KeyError:
            temp_dict = {volume_no: [c["chapter"]]}
            try:
                volume_dict[manga_id].update(temp_dict)
            except KeyError:
                temp_dict = {manga_id: temp_dict}
                volume_dict.update(temp_dict)

    list_volume_dict = list(reversed(list(volume_dict)))
    prefix = 'b'

    # Check if the volume numbers overlap and assign prefix to each volume
    for manga in list_volume_dict:
        current_manga = volume_dict[manga]
        manga_list = list(reversed(list(current_manga)))
        for current_volume in manga_list:
            next_volume_index = manga_list.index(current_volume) + 1
            previous_volume_index = manga_list.index(current_volume) - 1
            result = False

            try:
                next_volume = manga_list[next_volume_index]
                result = any(elem in current_manga[next_volume] for elem in current_manga[current_volume])
            except (KeyError, IndexError):
                previous_volume = manga_list[previous_volume_index]
                result = any(elem in current_manga[previous_volume] for elem in current_manga[current_volume])

            if current_volume != '':
                if result:
                    temp_json = {current_volume: chr(ord(prefix) + next_volume_index)}
                else:
                    temp_json = {current_volume: 'c'}

                try:
                    chapter_prefix_dict[manga].update(temp_json)
                except KeyError:
                    chapter_prefix_dict[manga] = temp_json

    # Initalise json classes and make series folders
    if download_type == 1:
        json_file = TitleJson(data, series_route, covers)
    else:
        json_file = AccountJson(data, route, form)

    # API displays a maximum of 6000 chapters
    if chapter_count > 6000:
        print(f'Due to API limits, a maximum of 6000 chapters can be downloaded for this {form}.')

    # Check if a json exists
    if json_file.data_json:
        chapters_data = json_file.data_json["chapters"]
        chapters_data = [c["id"] for c in chapters_data]
    else:
        chapters_data = []

    # Loop chapters
    for chapter in chapters:
        chapter_id = chapter["id"]
        chapter_prefixes = chapter_prefix_dict.get(chapter["mangaId"], {})
        if chapter_id not in chapters_data:
            if download_type == 1:
                chapterDownloader(chapter_id, route, save_format, make_folder, add_data, chapter_prefixes, download_type, json_file, title)
            else:
                chapterDownloader(chapter_id, route, save_format, make_folder, add_data, chapter_prefixes, download_type, json_file)

    # print(f'{"-"*69}\nFinished Downloading {form.title()}: {name}\n{"-"*69}')
    
    # Save the json and covers if selected
    json_file.core(1)
    return
