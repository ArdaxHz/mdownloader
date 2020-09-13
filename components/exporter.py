#!/usr/bin/python3
import sys
import os
import time
import requests
import asyncio
import argparse
import re
import html
import json
import zipfile
import shutil

from aiohttp import ClientSession, ClientError
from pathlib import Path
from tqdm import tqdm



class Base:

    def __init__(self, series_title, chapter_data, languages):
        self.series_title = series_title
        self.chapter_data = chapter_data
        self.languages = languages
        self.lang_code = chapter_data["lang_code"]
        self.chapter_title = 1 if chapter_data["title"].lower() == 'oneshot' or chapter_data["title"] == '' else 0
        self.chapter_regrex = re.compile(r'([0-9]+)\.([0-9]+)')
        self.name_regex = re.compile('[\\\\/:*?"<>|]')
        self.groups = self.groupNames()
        self.chapter_number = self.chapterNo()
        self.volume = self.volumeNo()
        self.language = self.langCode()
        self.prefix = self.prefixName()
        self.suffix = self.suffixName()
        self.folder_name = self.folderName()


    def chapterNo(self):
        chapter_number = re.sub(r'\D', '-', self.chapter_data["chapter"])

        if self.chapter_regrex.match(chapter_number):
            pattern = self.chapter_regrex.match(chapter_number)
            chap_no = pattern.group(1).zfill(3)
            decimal_no = pattern.group(2)
            chapter_number = f'c{chap_no}.{decimal_no}'
        elif self.chapter_title:
            chapter_number = chapter_number.zfill(3)
        else:
            chapter_number = f'c{chapter_number.zfill(3)}'
        return chapter_number


    def langCode(self):
        if self.lang_code == 'gb':
            return ''
        else:
            return f' [{self.languages[self.lang_code]}]'

    
    def volumeNo(self):
        if self.chapter_data["volume"] == '' or self.chapter_title == 1:
            return ''
        else:
            return f' (v{self.chapter_data["volume"].zfill(2)})'


    def prefixName(self):
        return f'{self.series_title}{self.language} - {self.chapter_number}{self.volume}'


    def groupNames(self):
        return self.name_regex.sub('_', html.unescape( ', '.join(filter(None, [self.chapter_data[x] for x in filter(lambda s: s.startswith('group_name'), self.chapter_data.keys()) ])) ))


    def suffixName(self):
        if self.chapter_title:
            return f'[Oneshot] [{self.groups}]'
        else:
            return f'[{self.groups}]'


    def folderName(self):
        return f'{self.prefix} {self.suffix}'


    def pageName(self, page_no, ext):
        return f'{self.prefix} - p{page_no:0>3} {self.suffix}.{ext}'



class ChapterSaver(Base):
    def __init__(self, series_title, chapter_data, languages, destination, save_format, make_folder):
        super().__init__(series_title, chapter_data, languages)
        self.destination = destination
        self.save_format = save_format
        self.path = Path(destination)
        self.make_folder = make_folder
        self.path.mkdir(parents=True, exist_ok=True)
        self.archive_path = os.path.join(destination, f'{self.folder_name}.{save_format}')
        self.folder_path = self.path.joinpath(self.folder_name)
        self.archive = self.checkZip()
        self.folder = 'no' if self.make_folder == 'no' else self.makeFolder()


    def remove(self):
        try:
            os.remove(self.archive_path)
        except FileNotFoundError:
            pass


    def makeZip(self):
        return zipfile.ZipFile(self.archive_path, mode="a", compression=zipfile.ZIP_DEFLATED) 


    def checkZip(self):
        archive = self.makeZip()
        comment = archive.comment.decode()
        
        if comment == '':
            archive.comment = str(self.chapter_data["id"]).encode()
        elif comment == str(self.chapter_data["id"]):
            archive.comment = str(self.chapter_data["id"]).encode()
        else:
            archive.close()
            
            print('The archive with the same chapter number and groups exists, but not the same chapter id, making a different archive...')
            
            self.archive_path = os.path.join(self.destination, f'{self.folder_name} {{v2}}.{self.save_format}')
            archive = self.makeZip()
            archive.comment = str(self.chapter_data["id"]).encode()
        
        return archive


    def makeFolder(self):
        try:
            return self.folder_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            sys.exit('Error creating folder')

    
    def imageCompress(self):
        self.archive.writestr(self.page_name, self.response)


    def folderAdd(self):
        with open(self.folder_path.joinpath(self.page_name), 'wb') as file:
            file.write(self.response)


    def checkImages(self):
        if self.page_name in self.archive.namelist():
            pass
        else:
            self.imageCompress()
        
        if self.folder != 'no':
            if self.page_name in os.listdir(self.folder_path):
                pass
            else:
                self.folderAdd()


    def add_image(self, response, page_no, ext):
        self.page_name = self.pageName(page_no, ext)
        self.response = response

        self.checkImages()


    def close(self):
        self.archive.close()