#!/usr/bin/python3
from datetime import datetime
import html
import os
from pathlib import Path
import re
import time
from typing import TYPE_CHECKING, AsyncGenerator, Tuple, Type, Union


import hondana
from tqdm import tqdm

from .constants import ImpVar

from .errors import MDownloaderError
from .exporter import ArchiveExporter, FolderExporter

if TYPE_CHECKING:
    
    from .main import MDArgs, ProcessArgs
    from .cache import CacheRead
    from aiohttp import ClientResponse


class ImageDownloader:
    
    def __init__(self, args: 'ProcessArgs', manga_data: 'hondana.Manga') -> None:
        self._args = args
        self._hondana_client = args._hondana_client
        self._manga_data = manga_data
        self._manga_title = self._format_title()
        self._download_route = self._format_save_route(self._manga_title)
        # if self._args.rename_files:
        #     self._check_downloaded_files()
        
    def _strip_illegal_characters(self, name: str) -> str:
        """Remove illegal characters from the specified name."""
        return re.sub(ImpVar.CHARA_REGEX, '_', html.unescape(name)).rstrip(' .')

    def _format_save_route(self, title: str) -> Path:
        """The location files will be saved to."""
        new_path = self._args.directory.joinpath(title)
        new_path.mkdir(parents=True, exist_ok=True)
        return new_path

    def _format_title(self) -> str:
        """Remove illegal characters from the manga title."""
        title = self._strip_illegal_characters(self._manga_data.title)
        return title

    def check_exist(self, pages: list, exporter) -> bool:
        """Check if the number of images in the archive or folder match that of the API."""
        # Only image files are counted
        if self._args.folder_download:
            files_path = os.listdir(self._download_route)
        else:
            files_path = self.model.exporter.archive.namelist()

        zip_count = [i for i in files_path if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

        if len(pages) == len(zip_count):
            return True
        return False

    def _save_json(self) -> None:
        """Save the chapter data to the data json and save the json."""
        if self.model.type_id in (1,):
            self.model.title_json.core()

        if self.model.type_id in (2, 3):
            self.model.manga_download = False
            self.model.bulk_json.core()
            self.model.manga_download = True

    def before_download(self, exists: bool) -> None:
        """Skip chapter if its already downloaded."""
        if exists:
            # Add chapter data to the json for title, group or user downloads
            self._save_json()
            self.model.exporter.close()
            raise MDownloaderError('File already downloaded.')

    def after_download(self, downloaded_all: bool) -> None:
        """Save json if all the images were downloaded and close the archive."""
        # If all the images are downloaded, save the json file with the latest downloaded chapter
        if downloaded_all:
            self._save_json()

        # Close the archive
        self.model.exporter.close()

    async def _pages(
        self, *, chapter: hondana.Chapter, data_saver: bool, ssl: bool
    ) -> AsyncGenerator[tuple[bytes, str, str], None]:
        at_home_data = await chapter.get_at_home(ssl=ssl)
        _at_home_url = at_home_data.base_url
        print(_at_home_url)

        _pages = at_home_data.data_saver if data_saver else at_home_data.data
        for i, url in enumerate(_pages[0:], start=1):
            route = hondana.utils.CustomRoute(
                "GET",
                _at_home_url,
                f"/{'data-saver' if data_saver else 'data'}/{at_home_data.hash}/{url}",
            )
            # LOGGER.debug("Attempting to download: %s", route.url)
            _start = time.monotonic()
            response: tuple[bytes, 'ClientResponse'] = await chapter._http.request(route)
            data, page_resp = response
            _end = time.monotonic()
            _total = _end - _start
            # LOGGER.debug("Downloaded: %s", route.url)

            if _at_home_url != "https://uploads.mangadex.org":
                await chapter._http._at_home_report(
                    url=route.url,
                    success=page_resp.status == 200,
                    cached=("X-Cache" in page_resp.headers),
                    size=(page_resp.content_length or 0),
                    duration=int(_total * 1000),
                )

            if page_resp.status != 200:
                _at_home_url = None
                break
            else:
                yield data, url.rsplit(".")[0], url.rsplit(".")[-1]

        else:
            return

        async for page in self._pages(chapter=chapter, data_saver=data_saver, ssl=ssl):
            yield page

    async def chapter_downloader(self, chapter_args_obj: 'MDArgs'):
        """Use the chapter data for image downloads and file name export.

        download_type: 0 = chapter
        download_type: 1 = manga
        download_type: 2 = group|user|list
        download_type: 3 = follows
        """
        chapter_data: hondana.Chapter = chapter_args_obj.data
        chapter_id = chapter_data.id
        # md_model.prefix = md_model.chapter_prefix_dict.get(chapter_data.volume, 'c')

        print(f'Downloading {chapter_data.title} | Volume: {chapter_data.volume} | Chapter: {chapter_data.chapter} | Title: {chapter_data.title}')

        page_data = await chapter_data.get_at_home()
        if not page_data.data:
            raise MDownloaderError('This chapter has no pages.')

        chapter_args_obj.cache.cache.data.update({"at-home": page_data._data})
        chapter_args_obj.cache.save_cache()

        {"args": self._args, "chapter_args_obj": chapter_args_obj, "page_data": page_data, "manga_title": self._manga_title, "download_path": self._download_route}

        # exporter = FolderExporter if self._args.folder_download else ArchiveExporter

        # Add chapter data to the json for title, group or user downloads
        # if md_model.type_id in (1,):
        #     md_model.title_json.add_chapter(data)
        # if md_model.type_id in (2, 3):
        #     md_model.bulk_json.add_chapter(data)

        # # External chapters
        # if chapter_data.external_url is not None:
        #     if 'mangaplus' in chapter_data.external_url:
        #         from .external import MangaPlus
        #         # Call MangaPlus downloader
        #         print('External chapter. Connecting to MangaPlus to download.')
        #         MangaPlus(md_model, chapter_data.external_url).download_mplus_chap()
        #         return
        #     raise MDownloaderError('Chapter external to MangaDex, unable to download. Skipping...')

        # Check if the chapter has been downloaded already
        exists = self.check_exist(page_data.data)
        self.before_download(exists)

        async for page_data, page_name, page_ext in self._pages(chapter=chapter_data, data_saver=False, ssl=False):
            print(page_name, page_ext)

        downloaded_all = self.check_exist(page_data.data)
        self.after_download(downloaded_all)

        await self._hondana_client.close()
        exit()