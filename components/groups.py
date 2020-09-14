#!/usr/bin/python3
import requests
import re

from math import ceil
from bs4 import BeautifulSoup
from components.chapters import downloadChapter
from components.__version__ import __version__


class CLI:
    
    def __init__(self, route, languages, make_folder, save_format):
        self.route = route
        self.languages = languages
        self.make_folder = make_folder
        self.save_format = save_format



class Groups(CLI):

    def __init__(self, group_id, route, languages, make_folder, save_format):
        super().__init__(route, languages, make_folder, save_format)
        self.group_id = group_id
        self.num = 1
        self.cookies = dict(mangadex_h_toggle='1')
        self.domain  = f'https://mangadex.org/group/{self.group_id}/{self.group_id}'
        self.headers = {'User-Agent': f'mDownloader/{__version__}'}
        self.id_regex = re.compile(r'(?:\/chapter\/)([0-9]+)')
        self.ids = []
        self.soup = self.requestGroup()
        self.group_name = self.groupName()
        self.group_chapters = self.groupChap()
        self.pages = self.getPages()


    def requestGroup(self):
        self.link = f'{self.domain}/chapters/{self.num}'
        response = requests.get(self.link, headers=self.headers, cookies=self.cookies)
        soup = BeautifulSoup(response.content, 'html.parser')
        self.getIDS(soup)
        return soup


    def getIDS(self, soup):
        releases_1 = soup.find_all('div', class_="row no-gutters")
        for find in releases_1:
            releases_2 = find.find('a', class_="text-truncate", href=self.id_regex)
            if releases_2 is not None:
                link = self.id_regex.match(releases_2['href']).group(1)
                self.ids.append(link)   


    def getPages(self):
        return ceil(int(self.group_chapters.replace(',', '')) / 100) + 1


    def groupChap(self):
        return self.soup.find_all('li', class_='list-inline-item')[2].getText().strip()


    def groupName(self):
        return (self.soup.find_all('div', class_='card mb-3')[0]).find('span', class_='mx-1').getText()


    def Loop(self):
        print('Getting the chapter ids...')
        while self.num < self.pages:
            self.num += 1
            self.requestGroup()


    def getChapters(self):
        print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')
        print(f"Downloading [{self.group_name}]'s chapters, [{self.group_chapters}] in total.")
        self.Loop()

        for id in self.ids:
            downloadChapter(id, '', self.route, '', 2, self.languages, self.make_folder, self.save_format, '')
        print("All the group's chapters have been downloaded.")
