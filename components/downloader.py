#!/usr/bin/python3
import asyncio
import html
import json
import os
import re
from datetime import datetime

import requests
from aiohttp import ClientSession, ClientError
from tqdm import tqdm

from .__version__ import __version__
from .exporter import ChapterExporter
from .jsonmaker import AccountJSON, TitleJson
from .mangaplus import MangaPlus

headers = {'User-Agent': f'mDownloader/{__version__}'}
domain  = 'https://mangadex.org'
re_regrex = re.compile('[\\\\/:*?"<>|]')


# Check if all the images are downloaded
def checkExist(pages, exporter_instance, make_folder):
    exists = 0

    # Only image files are counted
    zip_count = [i for i in exporter_instance.archive.namelist() if not i.endswith('.json')]

    if len(pages) == len(zip_count):
        if make_folder == 'no':
            exists = 1
        else:
            if len(pages) == len(os.listdir(exporter_instance.folder_path)):
                exists = 1
            else:
                exists = 0
    return exists


async def displayProgress(tasks):
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=(str(datetime.now(tz=None))[:-7])):
        try:
            await f
        except ConnectionResetError:
            pass
        except Exception as e:
            print(e)
    return


async def imageDownloader(url, image, pages, exporter_instance):
    retry = 0

    # Try to download it 5 times
    while retry < 5:
        async with ClientSession() as session:
            try:
                async with session.get(url + image) as response:

                    assert response.status == 200
                    response = await response.read()

                    page_no = pages.index(image) + 1
                    extension = image.rsplit('.', 1)[1]

                    # Add image to archive
                    exporter_instance.addImage(response, page_no, extension)

                    retry = 5
                    return

            except (ClientError, AssertionError, ConnectionResetError, asyncio.TimeoutError):
                await asyncio.sleep(3)

                retry += 1

                if retry == 5:
                    print(f'Could not download image {image} after 5 times.')
                return


# type 0 -> chapter
# type 1 -> title
# type 2 -> group
# type 3 -> user
def chapterDownloader(chapter_id, title, route, type, save_format, make_folder, json_file):

    # Connect to API and get chapter info
    url = f'{domain}/api/v2/chapter/{chapter_id}?saver=0'
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        if response.status_code == 451: #Unavailable chapters
            print(f"Unavailable Chapter. This could be because the chapter was deleted by the group or you're not allowed to read it. Error: {response.status_code}")
        elif response.status_code == 403: #Restricted Chapters. Like korean webtoons
            print(f"Restricted Chapter. You're not allowed to read this chapter. Error: {response.status_code}")
        elif response.status_code == 410: #Deleted Chapters.
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
        if type in (0, 2, 3):
            title = re_regrex.sub('_', html.unescape(chapter_data["mangaTitle"]))

            title = title.rstrip()
            title = title.rstrip('.')
            title = title.rstrip()

        series_route = os.path.join(route, title)

        # Make the file names
        exporter_instance = ChapterExporter(title, chapter_data, series_route, save_format, make_folder)
        
        # Add chapter data to the json for title, group or user downloads
        if type in (1, 2, 3):
            json_file.chapters(chapter_data)

        print(f'Downloading {title} | Volume: {chapter_data["volume"]} | Chapter: {chapter_data["chapter"]} | Title: {chapter_data["title"]}')

        #External chapters
        if chapter_data["status"] == 'external':
            # Call MangaPlus downloader
            print('External chapter... Connecting to MangaPlus to download...')
            MangaPlus(chapter_data, type, exporter_instance, json_file).plusImages()
        else:
            server_url = chapter_data["server"]
            url = f'{server_url}{chapter_data["hash"]}/'
            pages = chapter_data["pages"]
            exists = checkExist(pages, exporter_instance, make_folder)

            # Check if the chapter has been downloaded already
            if exists:
                print('File already downloaded.')
                if type in (1, 2, 3):
                    json_file.core(0)
                exporter_instance.close()
                return

            # ASYNC FUNCTION
            loop  = asyncio.get_event_loop()
            tasks = []

            # Download images
            for image in pages:
                task = asyncio.ensure_future(imageDownloader(url, image, pages, exporter_instance))
                tasks.append(task)

            runner = displayProgress(tasks)
            loop.run_until_complete(runner)

            downloaded_all = checkExist(pages, exporter_instance, make_folder)

            # If all the images are downloaded, save the json file with the latest downloaded chapter
            if downloaded_all and type in (1, 2, 3):
                json_file.core(0)

            # Close archive
            exporter_instance.close()
            return


def bulkDownloader(id, language, route, form, save_format, make_folder, covers):
   
    # Connect to API and get info
    url = f'{domain}/api/v2/{form}/{id}?include=chapters'
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"{form.title()} {id} doesn't exist. Request status error: {response.status_code}. Skipping...")
        return

    data = response.json()
    data = data["data"]
    chapter_count = 0

    # Call the relevant jsonmaker class
    if form in ('title', 'manga'):
        type = 1
        chapter_count = len(data["chapters"])
        title = re_regrex.sub('_', html.unescape(data["manga"]["title"]))

        title = title.rstrip()
        title = title.rstrip('.')
        title = title.rstrip()
        name = title

        series_route = os.path.join(route, title)
        json_file = TitleJson(data, series_route, covers)
    
    elif form == 'group':
        type = 2
        name = data["group"]["name"]
        title = ''
        chapter_count = data["group"]["chapters"]

        json_file = AccountJSON(data, route, 'group')

    else:
        type = 3
        name = data["user"]["username"]
        title = ''
        chapter_count = data["user"]["uploads"]

        json_file = AccountJSON(data, route, 'user')

    # Skip titles/groups/users without chapters
    if not data["chapters"]:
        print(f'{form.title()} {id} - {title} has no chapters.')
        if form in ('title', 'manga'):
            json_file.chapters(None)
            json_file.core(1)
        return

    # API displays a maximum of 6000 chapters
    if chapter_count > 6000:
        print(f'Due to API limits, a maximum of 6000 chapters can be downloaded for this {form.lower()}.')

    # Check if a json exists
    if json_file.data_json:
        chapters_data = json_file.data_json["chapters"]
    else:
        chapters_data = {}

    print(f'{"-"*69}\nDownloading {form.title()}: {name}\n{"-"*69}')

    # Check if at least one chapter was downloaded
    downloaded = False

    # Loop chapters
    for chapter in data["chapters"]:

        # Only chapters of language selected. Default language: English.
        if chapter["language"] == language:
            downloaded = True
            chapter_id = chapter["id"]

            if str(chapter_id) not in chapters_data:
                chapterDownloader(chapter_id, title, route, type, save_format, make_folder, json_file)
                continue
            else:
                continue
    
    # No chapters downloaded
    if not downloaded:
        print('No chapters found in the selected language.')

    # print(f'{"-"*69}\nFinished Downloading {form.title()}: {name}\n{"-"*69}')
    
    # Save the json and covers if selected
    json_file.core(1)
    return
