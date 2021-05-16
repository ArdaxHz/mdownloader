#!/usr/bin/python3
import re
from datetime import datetime

import requests
from tqdm import tqdm

from .response_pb2 import Response


class MangaPlus:

    def __init__(
            self,
            md_model) -> None:

        self.md_model = md_model
        self.chapter_data = md_model.chapter_data
        self.type = md_model.download_type
        self.exporter = md_model.exporter
        self.api_url = self.idChecker()
        self.extension = 'jpg'

    def idChecker(self) -> str:
        """Get the MangaPlus id for the api.

        Returns:
            str: The MangaPlus url to request.
        """
        mplus_url = re.compile(r'(?:https:\/\/mangaplus\.shueisha\.co\.jp\/viewer\/)([0-9]+)')
        mplus_id = mplus_url.match(self.chapter_data["data"]["attributes"]["data"][0]).group(1)
        url = f'https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer?chapter_id={mplus_id}&split=no&img_quality=super_high'
        return url

    def decryptImage(self, url: str, encryption_hex: str) -> bytearray:
        """Decrypt the image so it can be saved.

        Args:
            url (str): The image link.
            encryption_hex (str): The key to decrypt the image.

        Returns:
            bytearray: The image data.
        """
        resp = requests.get(url)
        data = bytearray(resp.content)
        key = bytes.fromhex(encryption_hex)
        a = len(key)
        for s in range(len(data)):
            data[s] ^= key[s % a]
        return data

    def plusImages(self) -> None:
        """Get the images from the MangaPlus api."""
        response = requests.get(self.api_url)
        viewer = Response.FromString(response.content).success.manga_viewer
        pages = [p.manga_page for p in viewer.pages if p.manga_page.image_url]

        exists = self.md_model.checkExist(pages)
        self.md_model.existsBeforeDownload(exists)

        # Decrypt then save each image
        for page in tqdm(pages, desc=(str(datetime.now(tz=None))[:-7])):
            image = self.decryptImage(page.image_url, page.encryption_key)
            page_no = pages.index(page) + 1
            self.exporter.addImage(image, page_no, self.extension)

        downloaded_all = self.md_model.checkExist(pages)
        self.md_model.existsAfterDownload(downloaded_all)
