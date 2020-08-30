#!/usr/bin/python3
import requests
import re

from tqdm import tqdm
from response_pb2 import Response, MangaViewer, TitleDetailView

class MangaPlus:

    def __init__(self, chapter_data, chapter_instance):
        self.chapter_data = chapter_data
        self.chapter_instance = chapter_instance
        self.api_url = self.idChecker()
        self.extension = 'jpg'

    def idChecker(self):
        mplus_url = re.compile(r"(?:https:\/\/mangaplus\.shueisha\.co\.jp\/viewer\/)([0-9]+)")
        mplus_id = mplus_url.match(self.chapter_data["external"]).group(1)
        url = f"https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer?chapter_id={mplus_id}&split=no&img_quality=super_high"
        
        return url


    def decryptImage(self, url, encryption_hex):
        resp = requests.get(url)
        data = bytearray(resp.content)
        key = bytes.fromhex(encryption_hex)
        a = len(key)
        for s in range(len(data)):
            data[s] ^= key[s % a]
        return data


    def plusImages(self):

        try:
            response = requests.get(self.api_url)
            viewer = Response.FromString(response.content).success.manga_viewer
            pages = [p.manga_page for p in viewer.pages if p.manga_page.image_url]

            for page in tqdm(pages):
                image = self.decryptImage(page.image_url, page.encryption_key)
                page_no = pages.index(page) + 1
                self.chapter_instance.add_image(image, page_no, self.extension)

            self.chapter_instance.close

        except (TimeoutError, KeyboardInterrupt, ConnectionResetError):
            self.chapter_instance.remove