#!/usr/bin/python3
import os
import re

import requests
from tqdm import tqdm

from .response_pb2 import Response, MangaViewer, TitleDetailView



class MangaPlus:

    def __init__(self, chapter_data, type, chapter_instance, json_file):
        self.chapter_data = chapter_data
        self.type = type
        self.chapter_instance = chapter_instance
        self.json_file = json_file
        self.api_url = self.idChecker()
        self.extension = 'jpg'


    # Get the MangaPlus id for the api
    def idChecker(self):
        mplus_url = re.compile(r'(?:https:\/\/mangaplus\.shueisha\.co\.jp\/viewer\/)([0-9]+)')
        mplus_id = mplus_url.match(self.chapter_data["pages"]).group(1)
        url = f'https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer?chapter_id={mplus_id}&split=no&img_quality=super_high'
        return url


    # Decrypt the image so it can be saved
    def decryptImage(self, url, encryption_hex):
        resp = requests.get(url)
        data = bytearray(resp.content)
        key = bytes.fromhex(encryption_hex)
        a = len(key)
        for s in range(len(data)):
            data[s] ^= key[s % a]
        return data


    # Check if all the images are downloaded    
    def checkExist(self, pages):
        exists = 0

        zip_count = [i for i in self.chapter_instance.archive.namelist() if not i.endswith('.json')]

        if len(pages) == len(zip_count):
            if self.chapter_instance.make_folder == 'no':
                exists = 1
            else:
                if len(pages) == len(os.listdir(self.chapter_instance.folder_path)):
                    exists = 1
                else:
                    exists = 0
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
        for page in tqdm(pages):
            image = self.decryptImage(page.image_url, page.encryption_key)
            page_no = pages.index(page) + 1
            self.chapter_instance.addImage(image, page_no, self.extension)

        downloaded_all = self.checkExist(pages)

        # If all the images are downloaded, save the json file with the latest downloaded chapter
        if downloaded_all and self.type in (1, 2, 3):
            self.json_file.core(0)

        self.chapter_instance.close()
        return
