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

    def __init__(self, title, image_data, languages):
        self.title = title
        self.volume = image_data["volume"]
        self.chapter_number = image_data["chapter"]
        self.language = languages[image_data["lang_code"]]
        self.lang_code = image_data["lang_code"]
        self.regex = re.compile('[\\\\/:*?"<>|]')
        self.groups = self.regex.sub('_', html.unescape(', '.join(filter(None, [image_data[x] for x in filter(lambda s: s.startswith('group_name'), image_data.keys())]))))
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
    def __init__(self, title, image_data, languages, destination, save_format):
        super().__init__(title, image_data, languages)
        self.path = Path(destination)
        self.path.mkdir(parents=True, exist_ok=True)
        self.archive_path = self.path.joinpath(self.folder_name).with_suffix(f".{save_format}")
        self.archive = zipfile.ZipFile(self.archive_path, mode="a", compression=zipfile.ZIP_DEFLATED)

    
    def imageCompress(self):
        self.archive.writestr(self.page_name, self.response)


    def add_image(self, response, page_no, ext):
        self.page_name = self.pageName(page_no, ext)
        self.response = response

        if self.page_name in self.archive.namelist():
            pass
        else:
            self.imageCompress()


    def remove(self):
        try:
            os.remove(self.archive)
        except FileNotFoundError:
            pass


    def close(self):
        self.archive.close()