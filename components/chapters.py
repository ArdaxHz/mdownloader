#!/usr/bin/python3
import requests
import asyncio
import re
import os
import html
import json

from aiohttp import ClientSession, ClientError
from tqdm import tqdm
from components.exporter import ChapterSaver
from components.mangaplus import MangaPlus
from components.__version__ import __version__

headers = {'User-Agent': f'mDownloader/{__version__}'}
domain  = 'https://mangadex.org'
re_regrex = re.compile('[\\\\/:*?"<>|]')


async def wait_with_progress(coros):
    for f in tqdm(asyncio.as_completed(coros), total=len(coros)):
        try:
            await f
        except Exception as e:
            print(e)


async def downloadImages(image, url, retry, chapter_data, instance):

    #try to download it 5 times
    while retry < 5:
        async with ClientSession() as session:
            try:
                async with session.get(url + image) as response:
    
                    assert response.status == 200
                    response = await response.read()

                    page_no = chapter_data["page_array"].index(image) + 1
                    extension = image.rsplit('.')[1]

                    instance.add_image(response, page_no, extension)
                    
                    retry = 5

            except (ClientError, AssertionError, ConnectionResetError, asyncio.TimeoutError):
                await asyncio.sleep(3)

                retry += 1

                if retry == 5:
                    print(f'Could not download image {image} after 5 times.')


# type 0 -> chapter
# type 1 -> title
# type 1 -> group
def downloadChapter(chapter_id, series_route, route, languages, type, title, make_folder, save_format, json_file):

    if languages == '':
        #Read languages file
        with open('languages.json', 'r') as lang_file:
            languages = json.load(lang_file)

        if type == 0:
            print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

    #Connect to API and get chapter info
    url = f'{domain}/api?id={chapter_id}&type=chapter&saver=0'

    response = requests.get(url, headers = headers)

    if response.status_code != 200:
        if response.status_code == 300: #Unavailable chapters
            print(f"Unavailable Chapter. This could be because the chapter was deleted by the group or you're not allowed to read it. Error: {response.status_code}")
        elif response.status_code == 451: #Restricted Chapters. Like korean webtoons
            print(f"Restricted Chapter. You're not allowed to read this chapter. Error: {response.status_code}")
        elif response.status_code == 410: #Deleted Chapters.
            print(f"Deleted Chapter. Error: {response.status_code}")
        else:
            print(f"Chapter ID doesn't exist. Error: {response.status_code}")
        return
    else:
        chapter_data = response.json()
        
        server_url = chapter_data["server"]
        url = f'{server_url}{chapter_data["hash"]}/'
        
        #chapter download
        if type == 0 or type == 2:
            try:
                manga_id = chapter_data["manga_id"]
                manga_url = f'{domain}/api?id={manga_id}&type=manga'

                manga_api = requests.get(manga_url, headers= headers)
                manga_data = manga_api.json()
                title = re_regrex.sub('_', html.unescape(manga_data['manga']['title']))

                title = title.rstrip()
                title = title.rstrip('.')
                title = title.rstrip()
                series_title = title

                series_route = os.path.join(route, series_title)
            except json.JSONDecodeError:
                print("Could not call the api of the title page.")
                return

        instance = ChapterSaver(title, chapter_data, languages, series_route, save_format, make_folder)
        
        if type == 1:
            json_file.chapters(chapter_data)

        print(f'Downloading {title} | Volume: {chapter_data["volume"]} | Chapter: {chapter_data["chapter"]} | Title: {chapter_data["title"]}')

        #Extenal chapters
        if chapter_data["status"] == 'external':
            print('External chapter... Connecting to MangaPlus to download...')
            manga_plus = MangaPlus(chapter_data, instance)
            manga_plus.plusImages()
        else:
            exists = 0

            if len(chapter_data['page_array']) == len(instance.archive.namelist()):
                if make_folder == 'no':
                    exists = 1
                else:
                    if len(chapter_data['page_array']) == len(os.listdir(instance.folder_path)):
                        exists = 1
                    else:
                        exists = 0

            if exists:
                print('File already downloaded.')
                return

            # ASYNC FUNCTION
            loop  = asyncio.get_event_loop()
            tasks = []
            
            for image in chapter_data['page_array']:
                task = asyncio.ensure_future(downloadImages(image, url, 0, chapter_data, instance))
                tasks.append(task)

            runner = wait_with_progress(tasks)
            loop.run_until_complete(runner)
            
            instance.close()
