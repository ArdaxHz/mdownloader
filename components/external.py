#!/usr/bin/python3
import re
from datetime import datetime
from typing import TYPE_CHECKING, Union

import requests
from tqdm import tqdm

from .response_pb2 import Response


if TYPE_CHECKING:
    from .args import MDArgs
    from .exporter import ArchiveExporter, FolderExporter
    from .image_downloader import ImageDownloader


class ExternalBase:
    def __init__(
        self,
        image_downloader_obj: "ImageDownloader",
        chapter_args_obj: MDArgs,
        exporter: Union["ArchiveExporter", "FolderExporter"],
    ) -> None:
        self._image_downloader_obj = image_downloader_obj
        self._chapter_args_obj = chapter_args_obj
        self._exporter = exporter
        self._extension = "jpg"

    def download_chapter(self, pages: list, download_site: str) -> None:
        exists = self._image_downloader_obj.check_exist(pages)
        self._image_downloader_obj.before_download(exists)

        # Decrypt then save each image
        for page in tqdm(pages, desc=(str(datetime.now(tz=None))[:-7])):
            if download_site == "mangaplus":
                image = self.decrypt_image(page.image_url, page.encryption_key)
            page_no = pages.index(page) + 1
            self._exporter.add_image(response=image, page_no=page_no, ext=self._extension, orig_name=None)

        downloaded_all = self._image_downloader_obj.check_exist(pages)
        self._image_downloader_obj.after_download(downloaded_all)


class MangaPlus(ExternalBase):
    def __init__(
        self,
        image_downloader_obj: "ImageDownloader",
        chapter_args_obj: MDArgs,
        exporter: Union["ArchiveExporter", "FolderExporter"],
    ) -> None:
        super().__init__(image_downloader_obj, chapter_args_obj, exporter)

        self.api_url = self.check_id(self._chapter_args_obj.data.external_url)

    def check_id(self, mplus_url: str) -> str:
        """Get the MangaPlus id for the api.

        Args:
            mplus_url (dict): Mangaplus url to get the mplus id from.

        Returns:
            str: The MangaPlus url to get the images array.
        """
        mplus_url_regex = re.compile(r"(?:https:\/\/mangaplus\.shueisha\.co\.jp\/viewer\/)([0-9]+)")
        mplus_id = mplus_url_regex.match(mplus_url).group(1)
        url = f"https://jumpg-webapi.tokyo-cdn.com/api/manga_viewer?chapter_id={mplus_id}&split=no&img_quality=super_high"
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
        # if self.md_model.debug: print(response.url)
        viewer = Response.FromString(response.content).success.manga_viewer
        pages = [p.manga_page for p in viewer.pages if p.manga_page.image_url]
        self.download_chapter(pages, "mangaplus")
