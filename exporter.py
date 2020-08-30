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

headers = {'User-Agent': 'mDownloader/2.2.9'}
domain  = 'https://mangadex.org'
re_regrex = re.compile('[\\\\/:*?"<>|]')
md_url = re.compile(r'https\:\/\/mangadex\.org\/(title|chapter|manga)\/([0-9]+)')
url_re = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')



class Base:

    def __init__(self, title, image_data, languages):
        self.title = title
        self.volume = image_data["volume"]
        self.chapter_number = image_data["chapter"]
        self.language = languages[image_data["lang_code"]]
        self.lang_code = image_data["lang_code"]
        self.groups = re_regrex.sub('_', html.unescape(', '.join(filter(None, [image_data[x] for x in filter(lambda s: s.startswith('group_name'), image_data.keys())]))))
        self.prefix = self.prefixName()
        self.suffix = self.suffixName()
        self.folder_name = self.folderName()

    def prefixName(self):
        
        chapter_regrex = re.compile(r'([0-9]+)\.([0-9]+)')

        if chapter_regrex.match(self.chapter_number):
            pattern = chapter_regrex.match(self.chapter_number)
            chap_no = pattern.group(1).zfill(3)
            decimal_no = pattern.group(2)
            chapter_number = (f'{chap_no}.{decimal_no}')
        else:
            chapter_number = self.chapter_number.zfill(3)
        
        if self.lang_code == 'gb':
            name_prefix = self.title
        else:
            name_prefix = f'{self.title} [{self.language}]'
        
        if self.volume == '':
            prefix = f'{name_prefix} - c{chapter_number}'
        else:
            prefix = f'{name_prefix} - c{chapter_number} (v{self.volume.zfill(2)})'

        return prefix

    def suffixName(self):
        return f'[{self.groups}]'

    def folderName(self):
        return f'{self.prefix} {self.suffix}'

    def pageName(self, page_no, ext):
        return f'{self.prefix} - p{page_no:0>3} {self.suffix}.{ext}'



class CBZSaver(Base):
    def __init__(self, title, image_data, languages, destination, check_images):
        super().__init__(title, image_data, languages)
        self.path = Path(destination)
        self.path.mkdir(parents=True, exist_ok=True)
        self.zip_files = f'{self.folder_name}_tmp'
        self.archive_path = self.path.joinpath(self.folder_name).with_suffix(".cbz")
        self.check_images = check_images
        self.archive = zipfile.ZipFile(self.archive_path, mode="a", compression=zipfile.ZIP_DEFLATED)
        if self.check_images == 'data':
            self.cbzFiles()

    
    def imageCompress(self):
        self.archive.writestr(self.page_name, self.response)


    def imageChecker(self):
        for filename in os.listdir(self.zip_files):
            with open (f'{self.zip_files}/{filename}', 'rb') as file:
                f = file.read() 
                b = bytearray(f)
                if b == self.response:
                    self.response = b
                    self.page_name = filename
                else:
                    self.response = self.response
                    self.page_name = filename


    def add_image(self, response, page_no, ext):
        self.page_name = self.pageName(page_no, ext)
        self.response = response

        if self.check_images == 'data':
            self.imageChecker()
        else:
            if self.page_name in self.archive.namelist():
                pass
            else:
                self.archive.writestr(self.page_name, response)


    def cbzFiles(self):
        self.archive.extractall(self.zip_files)
        os.remove(self.archive_path)
        self.archive

    def remove(self):
        try:
            os.remove(self.archive)
            shutil.rmtree(self.zip_files)
        except FileNotFoundError:
            pass

    def close(self):
        self.archive.close()