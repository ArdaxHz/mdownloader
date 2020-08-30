#!/usr/bin/python3
import requests
import asyncio
import re
import os
import html
import json

from aiohttp import ClientSession, ClientError
from tqdm import tqdm
from exporter import CBZSaver
from mangaplus import MangaPlus

headers = {'User-Agent': 'mDownloader/2.2.9'}
domain  = 'https://mangadex.org'
re_regrex = re.compile('[\\\\/:*?"<>|]')

async def wait_with_progress(coros):
    for f in tqdm(asyncio.as_completed(coros), total=len(coros)):
        try:
            await f
        except Exception as e:
            print(e)


async def downloadImages(image, url, retry, image_data, instance):

    #try to download it 5 times
    while retry < 5:
        async with ClientSession() as session:
            try:
                async with session.get(url + image) as response:
    
                    assert response.status == 200
                    response = await response.read()

                    page_no = image_data["page_array"].index(image) + 1
                    extension = image.rsplit('.')[1]

                    instance.add_image(response, page_no, extension)
                    
                    retry = 5

            except (ClientError, AssertionError, asyncio.TimeoutError):
                await asyncio.sleep(3)

                retry += 1

                if retry == 5:
                    print(f'Could not download image {image} after 5 times.')


# type 0 -> chapter
# type 1 -> title
def downloadChapter(chapter_id, series_route, route, languages, type, remove_folder, title, check_images, save_format):

    try:
        if languages == '':
            #Read languages file
            with open('languages.json', 'r') as json_file:
                languages = json.load(json_file)

            print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

        #Connect to API and get chapter info
        url = f'{domain}/api?id={chapter_id}&type=chapter&saver=0'

        response = requests.get(url, headers = headers)

        if response.status_code != 200:

            #Unavailable chapters
            if response.status_code == 300:
                print("Unavailable Chapter. This could be because the chapter was deleted by the group or you're not allowed to read it.")
            else:
                #Restricted Chapters. Like korean webtoons
                if response.status_code == 451:
                    print("Restricted Chapter. You're not allowed to read this chapter.")
                else:
                    print(f'Request status error: {response.status_code}')

            return {"error": "There was an error while downloading the chapter", "response_code": response.status_code}
        else:
            image_data = response.json()
            
            server_url = image_data["server"]
            url = f'{server_url}{image_data["hash"]}/'
            
            #chapter download
            if type == 0:
                try:
                    manga_id = image_data["manga_id"]
                    manga_url = f'{domain}/api?id={manga_id}&type=manga'

                    manga_data = requests.get(manga_url, headers= headers).json()
                    title = re_regrex.sub('_', html.unescape(manga_data['manga']['title']))

                    folder_title = title.rstrip()
                    folder_title = folder_title.rstrip('.')
                    folder_title = folder_title.rstrip()

                    series_route = os.path.join(route, folder_title)
                except json.JSONDecodeError:
                    print("Could not call the api of the title page.")
                    return

            instance = CBZSaver(title, image_data, languages, series_route, check_images)

            #Extenal chapters
            if image_data["status"] == 'external':
                manga_plus = MangaPlus(image_data, instance)
                manga_plus.plusImages()
            
            else:
                print(f'Downloading {title} - Volume {image_data["volume"]} - Chapter {image_data["chapter"]} - Title: {image_data["title"]}')

                # ASYNC FUNCTION
                loop  = asyncio.get_event_loop()
                tasks = []
                
                for image in image_data['page_array']:
                    task = asyncio.ensure_future(downloadImages(image, url, 0, image_data, instance))
                    tasks.append(task)

                runner = wait_with_progress(tasks)
                loop.run_until_complete(runner)
                
                instance.close

            if type == 1 and image_data["status"] != 'external':
                
                response = {"url": url}
                response["pages"] = image_data["page_array"]

                return response
            elif type == 1 and image_data["status"] == 'external':
                return 'Unable to index MangaPlus pages into a list.'
    
    except (TimeoutError, KeyboardInterrupt, ConnectionResetError):
        instance.remove