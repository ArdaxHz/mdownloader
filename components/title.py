#!/usr/bin/python3
import sys
import os
import time
import requests
import re
import html
import json

from aiohttp import ClientSession, ClientError
from components.chapters import Chapter
from components.jsonmaker import titleJson
from components.__version__ import __version__

headers = {'User-Agent': f'mDownloader/{__version__}'}
domain  = 'https://mangadex.org'
re_regrex = re.compile('[\\\\/:*?"<>|]')

class Title:

    def __init__(self, manga_id, language, languages, route, type, make_folder, save_format, covers, bulk):
        self.manga_id = manga_id
        self.type = 1
        self.bulk = bulk
        self.route = route
        self.language = language
        self.make_folder = make_folder
        self.save_format = save_format
        self.covers = covers
        self.headers = {'User-Agent': f'mDownloader/{__version__}'}
        self.domain = 'https://mangadex.org/api'
        self.languages = languages
        self.iso_languages = self.Languages() if self.languages == '' else self.languages
        self.response = self.connectApi()
        self.data = self.mangaData()
        self.title = self.folderTitle()
        self.series_route = self.destination()
        self.json_file = titleJson(self.data, self.manga_id, self.series_route, self.covers)

    #Read languages file
    def Languages(self):
        with open('languages.json', 'r') as lang_file:
            languages = json.load(lang_file)
        return languages


    def destination(self):
        return os.path.join(self.route, self.title)


    def folderTitle(self):

        title = re_regrex.sub('_', html.unescape(self.data['manga']['title']))

        title = title.rstrip()
        title = title.rstrip('.')
        title = title.rstrip()

        return title


    #Connect to API and get manga info
    def connectApi(self):
        return requests.get(self.domain, params= {"id": self.manga_id, "type": "manga"}, headers= self.headers)


    def mangaData(self):
        return self.response.json()


    def downloadTitle(self):

        if not self.bulk:
            print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

        if self.response.status_code != 200:
            print(f"Title {self.manga_id} doesn't exist. Request status error: {self.response.status_code}. Skipping...")
            return

        if 'chapter' not in self.data:
            print(f'Title {self.manga_id} - {self.title} has no chapters. Making json and Skipping...')
            self.json_file.chapters(None)
            self.json_file.core()
            return

        print(f'---------------------------------------------------------------------\nDownloading Title: {self.title}\n---------------------------------------------------------------------')

        # Loop chapters
        for chapter_id in self.data['chapter']:

            # Only chapters of language selected. Default language: English.
            if self.data['chapter'][chapter_id]['lang_code'] == self.language:

                Chapter(chapter_id, self.series_route, self.route, self.iso_languages, 1, self.title, self.make_folder, self.save_format, self.json_file, self.bulk).downloadChapter()

        self.json_file.saveJson()
