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
        self.volume = chapter_data["volume"]
        self.chapter_number = chapter_data["chapter"]
        self.chapter_title = chapter_data["title"]
        self.language = languages[chapter_data["lang_code"]]
        self.lang_code = chapter_data["lang_code"]
        self.regex = re.compile('[\\\\/:*?"<>|]')
        self.groups = self.regex.sub('_', html.unescape( ', '.join(filter(None, [chapter_data[x] for x in filter(lambda s: s.startswith('group_name'), chapter_data.keys()) ])) ))
        self.prefix = self.prefixName()
        self.suffix = self.suffixName()
        self.folder_name = self.folderName()


    def prefixName(self):
        
        chapter_regrex = re.compile(r'([0-9]+)\.([0-9]+)')

        if chapter_regrex.match(self.chapter_number):
            pattern = chapter_regrex.match(self.chapter_number)
            chap_no = pattern.group(1).zfill(3)
            decimal_no = pattern.group(2)
            self.chapter_number = f'c{chap_no}.{decimal_no}'
        elif self.chapter_title == 'Oneshot':
            self.chapter_number = self.chapter_number.zfill(3)
        else:
            self.chapter_number = f'c{self.chapter_number.zfill(3)}'
        
        if self.lang_code == 'gb':
            name_prefix = self.series_title
        else:
            name_prefix = f'{self.series_title} [{self.language}]'

        if self.volume == '':
            prefix = f'{name_prefix} - {self.chapter_number}'
        else:
            prefix = f'{name_prefix} - {self.chapter_number} (v{self.volume.zfill(2)})'

        return prefix


    def suffixName(self):
        if self.chapter_title == 'Oneshot':
            return f'[{self.chapter_title}] [{self.groups}]'
        else:
            return f'[{self.groups}]'


    def folderName(self):
        return f'{self.prefix} {self.suffix}'


    def pageName(self, page_no, ext):
        return f'{self.prefix} - p{page_no:0>3} {self.suffix}.{ext}'



class ChapterSaver(Base):
    def __init__(self, series_title, chapter_data, languages, destination, save_format, make_folder):
        super().__init__(series_title, chapter_data, languages)
        self.path = Path(destination)
        self.make_folder = make_folder
        self.path.mkdir(parents=True, exist_ok=True)
        self.archive_path = os.path.join(destination, f'{self.folder_name}.{save_format}')
        self.folder_path = self.path.joinpath(self.folder_name)
        self.archive = self.makeZip()
        self.folder = 'no' if self.make_folder == 'no' else self.makeFolder()


    def remove(self):
        try:
            os.remove(self.archive_path)
        except FileNotFoundError:
            pass


    def makeZip(self):
        try:
            self.archive = zipfile.ZipFile(self.archive_path, mode="a", compression=zipfile.ZIP_DEFLATED, compresslevel=9)
            return self.archive
        except zipfile.BadZipFile:
            self.remove()
            sys.exit('Bad zip file detected, deleting.')


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