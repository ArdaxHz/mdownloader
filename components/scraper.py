#!/usr/bin/python3
import requests
import re

from math import ceil
from bs4 import BeautifulSoup
from components.chapters import downloadChapter
from components.__version__ import __version__


class CLI:
    
    def __init__(self, type, hentai, route, languages, make_folder, save_format):
        self.type = type
        self.hentai = hentai
        self.route = route
        self.languages = languages
        self.make_folder = make_folder
        self.save_format = save_format



class Scraper(CLI):

    def __init__(self, group_id, type, hentai, route, languages, make_folder, save_format):
        super().__init__(type, hentai, route, languages, make_folder, save_format)
        self.group_id = group_id
        self.num = 1
        self.cookies = dict(mangadex_h_toggle='1')
        self.domain  = f'https://mangadex.org/{self.type}/{self.group_id}/{self.group_id}'
        self.headers = {'User-Agent': f'mDownloader/{__version__}'}
        self.id_regex = re.compile(r'(?:\/chapter\/)([0-9]+)')
        self.ids = []
        self.hentai_ids = []
        self.soup = self.requestGroup()
        self.name = self.groupName() if self.type == 'group' else self.userName()
        self.chapters = self.groupChap() if self.type == 'group' else self.userChap()
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
            try:
                find.find('span', class_='badge badge-danger ml-1').getText()
            except AttributeError:
                pass
            else:
                releases_2 = find.find('div', class_="chapter-row d-flex row no-gutters p-2 align-items-center border-bottom odd-row")
                self.hentai_ids.append(releases_2['data-id'])
            
            try:
                releases_2 = find.find('div', class_="chapter-row d-flex row no-gutters p-2 align-items-center border-bottom odd-row")
                self.ids.append(releases_2['data-id'])
            except KeyError:
                pass  


    def getPages(self):
        return ceil(int(self.chapters.replace(',', '')) / 100) + 1


    def groupChap(self):
        return self.soup.find_all('li', class_='list-inline-item')[2].getText().strip()


    def groupName(self):
        return (self.soup.find_all('div', class_='card mb-3')[0]).find('span', class_='mx-1').getText()


    def userChap(self):
        return self.soup.find_all('li', class_='list-inline-item')[-1].getText().strip()


    def userName(self):
        return self.soup.find_all('span', class_='mx-1')[0].getText()


    def Loop(self):
        print('Getting the chapter ids...')
        while self.num < self.pages:
            self.num += 1
            self.requestGroup()


    def getChapters(self):
        print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')
        if self.chapters == '0':
            print(f'This {self.type} has no chapters.')
            return
        print(f"Downloading [{self.name}]'s chapters, [{self.chapters}] in total.")
        self.Loop()

        if self.hentai == 'skip':
            [self.ids.remove(h) for h in self.ids if h in self.hentai_ids]
        
        if self.hentai == 'only':
            self.ids = self.hentai_ids
        
        for id in self.ids:
            downloadChapter(id, '', self.route, '', 2, self.languages, self.make_folder, self.save_format, '')
        print(f"All the {self.type}'s chapters have been downloaded.")
