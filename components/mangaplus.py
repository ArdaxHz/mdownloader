#!/usr/bin/python3
import os
import re
from datetime import datetime
from typing import Optional, Type, Union

import requests
from tqdm import tqdm

from .exporter import ArchiveExporter, FolderExporter
from .jsonmaker import AccountJson, TitleJson
from .response_pb2 import Response



class MangaPlus:

    def __init__(
            self,
            chapter_data: dict,
            download_type: int,
            chapter_instance: Type[Union[ArchiveExporter, FolderExporter]],
            json_file: Optional[Type[Union[AccountJson, TitleJson]]]):
        # pylint: disable=unsubscriptable-object
        
        self.chapter_data = chapter_data
        self.type = download_type
        self.chapter_instance = chapter_instance
        self.json_file = json_file
        self.api_url = self.idChecker()
        self.extension = 'jpg'


    # Get the MangaPlus id for the api
    def idChecker(self) -> str:
        mplus_url = re.compile(r'(?:https:\/\/mangaplus\.shueisha\.co\.jp\/viewer\/)([0-9]+)')
        mplus_id = mplus_url.match(self.chapter_data["pages"]).group(1)
        url = f'https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer?chapter_id={mplus_id}&split=no&img_quality=super_high'
        return url


    # Decrypt the image so it can be saved
    def decryptImage(self, url: str, encryption_hex: str) -> bytearray:
        resp = requests.get(url)
        data = bytearray(resp.content)
        key = bytes.fromhex(encryption_hex)
        a = len(key)
        for s in range(len(data)):
            data[s] ^= key[s % a]
        return data


    # Check if all the images are downloaded    
    def checkExist(self, pages: list) -> bool:
        exists = 0

        if isinstance(self.chapter_instance, ArchiveExporter):
            zip_count = [i for i in self.chapter_instance.archive.namelist() if i.endswith('.jpg')]
        else:
            zip_count = [i for i in os.listdir(self.chapter_instance.folder_path) if i.endswith('.jpg')]

        if len(pages) == len(zip_count):
            exists = 1

        return exists


    # Get the images from the MangaPlus api
    def plusImages(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
        response = requests.get(self.api_url)
        viewer = Response.FromString(response.content).success.manga_viewer
        pages = [p.manga_page for p in viewer.pages if p.manga_page.image_url]

        exists = self.checkExist(pages)

        if exists:
            print('File already downloaded.')
            if self.type in (1, 2, 3):
                self.json_file.core(0)
            self.chapter_instance.close()
            return

        # Decrypt then save each image
        for page in tqdm(pages, desc=(str(datetime.now(tz=None))[:-7])):
            image = self.decryptImage(page.image_url, page.encryption_key)
            page_no = pages.index(page) + 1
            self.chapter_instance.addImage(image, page_no, self.extension)

        downloaded_all = self.checkExist(pages)

        # If all the images are downloaded, save the json file with the latest downloaded chapter
        if downloaded_all and self.type in (1, 2, 3):
            self.json_file.core(0)

        self.chapter_instance.close()
        return
