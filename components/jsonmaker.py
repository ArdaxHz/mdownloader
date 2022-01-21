#!/usr/bin/python3
import asyncio
import json
import os
import re
from copy import copy
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional
from urllib.parse import quote

import aiohttp
import hondana
import requests

from .args import MDArgs, ProcessArgs
from .constants import ImpVar


if TYPE_CHECKING:
    from .image_downloader import ImageDownloader


class JsonBase:
    def __init__(self, args: ProcessArgs, args_obj: MDArgs, img_dl_obj: Optional["ImageDownloader"] = None) -> None:
        self._args = args
        self._args_obj = args_obj
        self._img_dl_obj = img_dl_obj
        self.domain = ImpVar.MANGADEX_URL
        self.api_url = ImpVar.MANGADEX_API_URL
        self.new_data = {}

        data = self._args_obj.data
        if self._args_obj.type == "manga":
            file_prefix = ""
            self._route = self._img_dl_obj._download_route
        else:
            file_prefix = f"{self._args_obj.type}_"
            self._route = self._args.directory

        self._route.mkdir(parents=True, exist_ok=True)
        self.json_path = self._route.joinpath(f"{file_prefix}{self._args_obj.id}_data").with_suffix(".json")

        self.data_json = self._check_json_exist()
        self.downloaded_ids = self._get_downloaded_chapters()

    def _get_downloaded_chapters(self) -> List[str]:
        downloaded_ids = []
        self.chapters = self.data_json.get("chapters", [])
        self.json_ids = [c["id"] for c in self.chapters] if self.chapters else []
        self.chapters_archive = (
            [c["id"] for c in self.chapters if "chapters_archive" in c and c["chapters_archive"]] if self.chapters else []
        )
        self.chapters_folder = (
            [c["id"] for c in self.chapters if "chapters_folder" in c and c["chapters_folder"]] if self.chapters else []
        )

        if self._args.folder_download:
            downloaded_ids.extend(self.chapters_folder)
        else:
            downloaded_ids.extend(self.chapters_archive)

        return list(set(downloaded_ids))

    def _check_json_exist(self) -> dict:
        """Loads the json if it exists."""
        try:
            with open(self.json_path, "r", encoding="utf8") as file:
                series_json = json.load(file)
            return series_json
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _add_chapter_data(self, chapter_id: str, chapter_data: dict) -> None:
        """Add the chapter data to the json."""
        self.chapters.append(chapter_data)
        self.downloaded_ids.append(chapter_id)

    def _add_exporter_type(self, chapter_data_json: dict) -> dict:
        """Add the type of exporter used for the chapter download."""
        if self._args.folder_download:
            chapter_data_json.update({"chapters_folder": True})
        else:
            chapter_data_json.update({"chapters_archive": True})
        return chapter_data_json

    def add_chapter(self, chapter_data: dict) -> None:
        """Check if chapter data already in json."""

        chapter_id = chapter_data["id"]
        chapter_data = self._add_exporter_type(chapter_data)

        if chapter_id not in self.downloaded_ids:
            self._add_chapter_data(chapter_id, chapter_data)
        else:
            chapter_data_json = [c for c in self.chapters if c["id"] == chapter_id]

            # Update the chapter data if it exists
            for chapter in chapter_data_json:
                if chapter["at-home"]["hash"] == chapter_data["at-home"]["hash"]:
                    self.chapters[self.chapters.index(chapter)] = self._add_exporter_type(chapter)
                else:
                    self._add_chapter_data(chapter_id, chapter_data)

    def remove_chapter(self, chapter_data: dict) -> None:
        """Remove the chapter data from the data json."""

        chapter_id = chapter_data["id"]
        self.downloaded_ids.remove(chapter_id)

        chapter_data_json = [c for c in self.chapters if c["id"] == chapter_id]
        for chapter in chapter_data_json:
            self.chapters.remove(chapter)

    def _save_json(self) -> None:
        """Save the json."""
        with open(self.json_path, "w", encoding="utf8") as json_file:
            json.dump(self.new_data, json_file, indent=4, ensure_ascii=False)

    async def _core(self, save_type: int = 0) -> None:
        """Format the json for exporting.

        Args:
            save_type (int, optional): Save the covers after all the manga's chapters have been downloaded. Defaults to 0.
        """
        self.new_data["chapters"] = self.chapters
        self._save_json()


class TitleJson(JsonBase):
    def __init__(self, args: ProcessArgs, manga_args_obj: MDArgs, img_dl_obj: Optional["ImageDownloader"] = None) -> None:
        super().__init__(args, manga_args_obj, img_dl_obj)
        self._regex = re.compile(ImpVar.CHARA_REGEX)
        self._cover_route = self._route.joinpath("!covers")
        self._links = self._format_links()
        self._covers: Optional[List[hondana.Cover]] = None
        self._title_json = self._title()

    def _format_links(self) -> dict:
        """Formats the manga's external links by name and url."""
        _links = self._args_obj.data.links
        if _links is None:
            return {}

        json_links = {}
        formats = {
            "al": {"name": "AniList", "url": "https://anilist.co/manga/{}"},
            "ap": {"name": "Anime-Planet", "url": "https://www.anime-planet.com/manga/{}"},
            "bw": {"name": "Bookwalker", "url": "https://bookwalker.jp/{}"},
            "mu": {"name": "MangaUpdates", "url": "https://www.mangaupdates.com/series.html?id={}"},
            "nu": {"name": "NovelUpdates", "url": "https://www.novelupdates.com/series/{}"},
            "kt": {"name": "kitsu.io", "url": "https://kitsu.io/manga/{}"},
            "amz": {"name": "Amazon", "url": "{}"},
            "cdj": {"name": "CDJapan", "url": "{}"},
            "ebj": {"name": "EBookJapan", "url": "https://ebookjapan.yahoo.co.jp/books/{}"},
            "mal": {"name": "MyAnimeList", "url": "https://myanimelist.net/manga/{}"},
            "raw": {"name": "Raw", "url": "{}"},
            "engtl": {"name": "Official English Link", "url": "{}"},
        }

        for l in _links:
            if l == "bw":
                if re.match(r"series/[0-9]+", l):
                    newl = f"{_links[l]}/list"
                else:
                    newl = _links[l]
            elif l == "nu":
                newl = quote(_links[l])
            elif l == "ebj":
                newl = re.sub("https://www.ebookjapan.jp/ebj/", "", _links[l])
            else:
                newl = _links[l]

            if l in formats:
                formats[l]["url"] = formats[l]["url"].format(newl)
                json_links.update({l: formats[l]})
            else:
                json_links.update({l: {"name": l, "url": newl}})
        return json_links

    async def _download_covers(self) -> None:
        """Download the covers."""
        covers = self._covers

        if covers:
            # Make the covers folder in the manga folder
            self._cover_route.mkdir(parents=True, exist_ok=True)
            print("Downloading covers.")

            for cover in covers:
                cover_name = cover.file_name
                cover_volume = cover.volume or "0"
                try:
                    response = requests.get(cover.url())
                    if response.status_code != 200:
                        raise AssertionError
                    image_bytes = response.content
                except AssertionError:
                    print(f"Could not save {cover_name}.")
                    continue
                else:
                    downloaded_cover_name = f"v{cover_volume.zfill(2)}_{cover_name}"
                    cover_path = self._cover_route.joinpath(downloaded_cover_name)

                    if not os.path.exists(cover_path):
                        print(f"Saving cover {downloaded_cover_name}.")
                        with open(cover_path, "wb") as file:
                            file.write(image_bytes)

            print("Finished downloadng covers.")
        else:
            print("This title has no covers to download.")

    async def _get_covers(self) -> List[hondana.Cover]:
        """Fetches a dict of the manga's covers."""
        refresh_cache = self._args_obj.cache.check_cache_time()

        if refresh_cache or not bool(self._args_obj.cache.cache.covers):
            cover_response = await self._args._hondana_client.cover_art_list(limit=None, manga=[self._args_obj.id])
            self._args_obj.cache.save_cache(covers=copy(cover_response))
            covers = cover_response.covers
        else:
            covers = [hondana.Cover(self._args._hondana_client._http, c) for c in self._args_obj.cache.cache.covers]

        return covers

    async def _format_socials(self) -> dict:
        """The social data of the manga."""
        json_social = {"views": self.data["views"]}
        json_social["follows"] = self.data["follows"]
        json_social["comments"] = self.data["comments"]
        json_social["rating"] = self.data["rating"]
        return json_social

    def _title(self) -> dict:
        """General manga information."""
        json_title = {"id": self._args_obj.data.id}
        json_title["url"] = self._args_obj.data.url
        json_title["attributes"] = self._args_obj.data._attributes
        # json_title["social"] = self.social
        return json_title

    async def core(self, save_type: int = 0) -> None:
        """Format the json for exporting.

        Args:
            save_type (int, optional): Save the covers after all the manga's chapters have been downloaded. Defaults to 0.
        """
        self.new_data = self._title_json
        self.new_data["externalLinks"] = self._links

        if self._covers is None:
            self._covers = await self._get_covers()

        self.new_data["covers"] = [c._data for c in self._covers]

        if save_type and self._args.cover_download:
            await self._download_covers()

        await super()._core(save_type)


class BulkJson(JsonBase):
    def __init__(self, args: ProcessArgs, bulk_args_obj: MDArgs, img_dl_obj: Optional["ImageDownloader"] = None) -> None:
        super().__init__(args, bulk_args_obj, img_dl_obj)
        self.bulk_data = self._format_bulk_data()

    def _format_bulk_data(self) -> dict:
        """Get the download type's data and name."""
        json_account = {"id": self._args_obj.id}
        json_account["link"] = f"{self.domain}/{self._args_obj.type}/{self._args_obj.id}"
        json_account["attributes"] = self._args_obj.cache.cache.data
        return json_account

    async def core(self, save_type: int = 0) -> None:
        """Format the json for exporting.

        Args:
            save_type (int, optional): Save the covers after all the manga's chapters have been downloaded. Defaults to 0.
        """
        self.new_data = self.bulk_data
        await super()._core(save_type)
