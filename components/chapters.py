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



class Chapter:

    def __init__(self, chapter_id, series_route, route, languages, type, title, make_folder, save_format, json_file, bulk):
        self.chapter_id = chapter_id
        self.route = route
        self.title = title
        self.headers = {'User-Agent': f'mDownloader/{__version__}'}
        self.domain = 'https://mangadex.org/api'
        self.chapter_api = self.chapterApi()
        self.regrex = re.compile('[\\\\/:*?"<>|]')
        self.type = type
        self.bulk = bulk
        self.languages = languages
        self.series_route = series_route
        self.make_folder = make_folder
        self.save_format = save_format
        self.json_file = json_file


    async def wait_with_progress(self, coros):
        for f in tqdm(asyncio.as_completed(coros), total=len(coros)):
            try:
                await f
            except Exception as e:
                print(e)


    async def downloadImages(self, url, image, retry):

        #try to download it 5 times
        while retry < 5:
            async with ClientSession() as session:
                try:
                    async with session.get(url + image) as response:
        
                        assert response.status == 200
                        response = await response.read()

                        page_no = self.chapter_data["page_array"].index(image) + 1
                        extension = image.rsplit('.')[1]

                        self.instance.add_image(response, page_no, extension)
                        
                        retry = 5

                except (ClientError, AssertionError, ConnectionResetError, asyncio.TimeoutError):
                    await asyncio.sleep(3)

                    retry += 1

                    if retry == 5:
                        print(f'Could not download image {image} after 5 times.')


    #Read languages file
    def Languages(self):
        with open('languages.json', 'r') as lang_file:
            languages = json.load(lang_file)
        return languages


    def destination(self):
        return os.path.join(self.route, self.title)


    def chapterApi(self):
        return requests.get(self.domain, params= {"id": self.chapter_id, "type": "chapter", "saver": 0}, headers= self.headers)


    def mangaTitle(self):
        try:
            manga_id = self.chapter_data["manga_id"]
            manga_data = requests.get(self.domain, params= {"id": manga_id, "type": "manga"}, headers= self.headers).json()
            
            title = self.regrex.sub('_', html.unescape(manga_data['manga']['title']))

            title = title.rstrip()
            title = title.rstrip('.')
            title = title.rstrip()

        except json.JSONDecodeError:
            print("Could not call the api of the title page.")
            return 

        return title  


    def checkExists(self):
        exists = 0

        if len(self.chapter_data['page_array']) == len(self.instance.archive.namelist()):
            if self.make_folder == 'no':
                exists = 1
            else:
                if len(self.chapter_data['page_array']) == len(os.listdir(self.instance.folder_path)):
                    exists = 1
                else:
                    exists = 0
        return exists

    def chapterInstance(self):
        return ChapterSaver(self.title, self.chapter_data, self.iso_languages, self.folder, self.save_format, self.make_folder)


    # type 0 -> chapter
    # type 1 -> title
    def downloadChapter(self):

        try:
            if not self.bulk and not self.type:
                print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

            self.response = self.chapterApi()

            if self.response.status_code != 200:
                #Unavailable chapters
                if self.response.status_code == 300:
                    print("Unavailable Chapter. This could be because the chapter was deleted by the group or you're not allowed to read it.")
                else:
                    #Restricted Chapters. Like korean webtoons
                    if self.response.status_code == 451:
                        print("Restricted Chapter. You're not allowed to read this chapter.")
                    else:
                        print(f'Request status error: {self.response.status_code}')
                return
            
            else:
                self.chapter_data = self.response.json()
                self.title = self.mangaTitle() if self.languages == '' else self.title
                self.folder = self.destination() if self.languages == '' else self.series_route
                self.iso_languages = self.Languages() if self.languages == '' else self.languages
                self.instance = self.chapterInstance()
                
                
                #Connect to API and get chapter info
                server_url = self.chapter_data["server"]
                url = f'{server_url}{self.chapter_data["hash"]}/'
                
                if self.type == 1:
                    self.json_file.chapters(self.chapter_data)

                print(f'Downloading {self.title} - Volume {self.chapter_data["volume"]} - Chapter {self.chapter_data["chapter"]} - Title: {self.chapter_data["title"]}')

                #Extenal chapters
                if self.chapter_data["status"] == 'external':
                    MangaPlus(self.chapter_data, self.instance).plusImages()
                else:

                    if self.checkExists():
                        print('Chapter already downloaded.')
                        return

                    # ASYNC FUNCTION
                    loop  = asyncio.get_event_loop()
                    tasks = []
                    
                    for image in self.chapter_data['page_array']:
                        task = asyncio.ensure_future(self.downloadImages(url, image, 0))
                        tasks.append(task)

                    runner = self.wait_with_progress(tasks)
                    loop.run_until_complete(runner)
                    
                    self.instance.close()

        except (TimeoutError, KeyboardInterrupt, ConnectionResetError):
            self.instance.close()
            self.instance.remove()
