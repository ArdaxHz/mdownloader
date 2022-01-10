#!/usr/bin/python3
import re
from datetime import datetime

import requests
from tqdm import tqdm

from .response_pb2 import Response
from .model import MDownloader



class ExternalBase:

    def __init__(self, md_model: MDownloader) -> None:
        self.md_model = md_model
        self.chapter_data = md_model.chapter_data
        self.type = md_model.download_type
        self.exporter = md_model.exporter
        self.extension = 'jpg'

    def download_chapter(self, pages: list, download_site: str) -> None:
        exists = self.md_model.exist.check_exist(pages)
        self.md_model.exist.before_download(exists)

        # Decrypt then save each image
        for page in tqdm(pages, desc=(str(datetime.now(tz=None))[:-7])):
            if download_site == 'mangaplus':
                image = self.decrypt_image(page.image_url, page.encryption_key)
            page_no = pages.index(page) + 1
            self.exporter.add_image(image, page_no, self.extension, '')

        downloaded_all = self.md_model.exist.check_exist(pages)
        self.md_model.exist.after_download(downloaded_all)



class MangaPlus(ExternalBase):

    def __init__(
            self,
            md_model: MDownloader,
            mplus_url: str) -> None:
        super().__init__(md_model)

        self.api_url = self.check_id(mplus_url)

    def check_id(self, mplus_url: str) -> str:
        """Get the MangaPlus id for the api.

        Args:
            mplus_url (dict): Mangaplus url to get the mplus id from.

        Returns:
            str: The MangaPlus url to get the images array.
        """
        mplus_url_regex = re.compile(r'(?:https:\/\/mangaplus\.shueisha\.co\.jp\/viewer\/)([0-9]+)')
        mplus_id = mplus_url_regex.match(mplus_url).group(1)
        url = f'https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer?chapter_id={mplus_id}&split=no&img_quality=super_high'
        return url

    def decrypt_image(self, url: str, encryption_hex: str) -> bytearray:
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

    def download_mplus_chap(self) -> None:
        """Get the images from the MangaPlus api."""
        response = requests.get(self.api_url)
        if self.md_model.debug: print(response.url)
        viewer = Response.FromString(response.content).success.manga_viewer
        pages = [p.manga_page for p in viewer.pages if p.manga_page.image_url]
        self.download_chapter(pages, 'mangaplus')
