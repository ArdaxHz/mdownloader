#!/usr/bin/python3
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional
from urllib.parse import quote

from .args import ProcessArgs, MDArgs
from .constants import ImpVar
from .errors import MDRequestError


if TYPE_CHECKING:
    from .image_downloader import ImageDownloader


class JsonBase:

    def __init__(self, args: ProcessArgs, manga_args_obj: MDArgs, img_dl_obj: Optional['ImageDownloader']=None) -> None:
        self._args = args
        self._manga_args_obj = manga_args_obj
        self._img_dl_obj = img_dl_obj
        self.domain = ImpVar.MANGADEX_URL
        self.api_url = ImpVar.MANGADEX_API_URL
        self.new_data = {}

        data = self._manga_args_obj.data
        if self._manga_args_obj.type == 'manga':
            file_prefix = ''
            self._route = self._img_dl_obj._download_route
        else:
            file_prefix = f'{self._manga_args_obj.type}_'
            self._route = self._args.directory

        self._route.mkdir(parents=True, exist_ok=True)
        self.json_path = self._route.joinpath(f'{file_prefix}{self._manga_args_obj.id}_data').with_suffix('.json')

        self.data_json = self._check_json_exist()
        self.downloaded_ids = self._get_downloaded_chapters()

    def _get_downloaded_chapters(self) -> List[str]:
        downloaded_ids = []
        self.chapters = self.data_json.get('chapters', [])
        self.json_ids = [c["id"] for c in self.chapters] if self.chapters else []
        self.chapters_archive = [c["id"] for c in self.chapters if 'chapters_archive' in c and c["chapters_archive"]] if self.chapters else []
        self.chapters_folder = [c["id"] for c in self.chapters if 'chapters_folder' in c and c["chapters_folder"]] if self.chapters else []

        if self._args.folder_download:
            downloaded_ids.extend(self.chapters_folder)
        else:
            downloaded_ids.extend(self.chapters_archive)

        return list(set(downloaded_ids))

    def _check_json_exist(self) -> dict:
        """Loads the json if it exists."""
        try:
            with open(self.json_path, 'r', encoding='utf8') as file:
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
                    self.add_chapter_data(chapter_id, chapter_data)

    def remove_chapter(self, chapter_data: dict) -> None:
        """Remove the chapter data from the data json."""

        chapter_id = chapter_data["id"]
        self.downloaded_ids.remove(chapter_id)

        chapter_data_json = [c for c in self.chapters if c["id"] == chapter_id]
        for chapter in chapter_data_json:
            self.chapters.remove(chapter)

    def _save_json(self) -> None:
        """Save the json."""
        with open(self.json_path, 'w', encoding='utf8') as json_file:
            json.dump(self.new_data, json_file, indent=4, ensure_ascii=False)

    def _core(self, save_type: int=0) -> None:
        """Format the json for exporting.

        Args:
            save_type (int, optional): Save the covers after all the manga's chapters have been downloaded. Defaults to 0.
        """
        self.new_data["chapters"] = self.chapters
        self._save_json()



class TitleJson(JsonBase):

    def __init__(self, args: ProcessArgs, manga_args_obj: MDArgs, img_dl_obj: 'ImageDownloader') -> None:
        super().__init__(args, manga_args_obj, img_dl_obj)
        self._regex = re.compile(ImpVar.CHARA_REGEX)
        self._cover_route = self._route.joinpath('!covers')
        self._links = self._format_links()
        # self._covers = self._get_covers()
        self._title_json = self._title()

    def _format_links(self) -> dict:
        """Formats the manga's external links by name and url."""
        _links = self._manga_args_obj.data.links
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
            if l == 'bw':
                if re.match(r'series/[0-9]+', l):
                    newl = f'{_links[l]}/list'
                else:
                    newl = _links[l]
            elif l == 'nu':
                newl = quote(_links[l])
            elif l == 'ebj':
                newl = re.sub('https://www.ebookjapan.jp/ebj/', '', _links[l])
            else:
                newl = _links[l]

            if l in formats:
                formats[l]["url"] = formats[l]["url"].format(newl)
                json_links.update({l: formats[l]})
            else:
                json_links.update({l: {"name": l, "url": newl}})
        return json_links

    def _download_covers(self) -> None:
        """Download the covers."""
        covers = self._covers

        if covers:
            # Make the covers folder in the manga folder
            self._cover_route.mkdir(parents=True, exist_ok=True)
            print('Downloading covers.')
            for cover in covers:
                cover_name = cover["attributes"]["fileName"]
                cover_volume = cover["attributes"]["volume"]
                cover_volume = cover_volume if cover_volume is not None else '0'
                cover_response = self.md_model.api.request_data(f'{self.md_model.cover_cdn_url}/{self.id}/{cover_name}')
                self.md_model.api.check_response_error(cover_response, 'cover', cover_response)

                if cover_response.status_code != 200:
                    print(f'Could not save {cover_name}.')
                    continue

                downloaded_cover_name = f'v{cover_volume.zfill(2)}_{cover_name}'
                cover_response = cover_response.content
                cover_path = os.path.join(self.cover_route, downloaded_cover_name)

                if not os.path.exists(cover_path):
                    print(f'Saving cover {downloaded_cover_name}.')
                    with open(cover_path, 'wb') as file:
                        file.write(cover_response)

            print('Finished downloadng covers.')
        else:
            print('This title has no covers to download.')

    def _get_covers(self) -> dict:
        """Fetches a dict of the manga's covers."""
        refresh_cache = self._manga_args_obj.cache.check_cache_time()

        if refresh_cache or not bool(self._manga_args_obj.cache.cache.covers):
            cover_response = self.md_model.api.request_data(f'{self.md_model.cover_api_url}', **{"manga[]": self.id, "limit": 100})

            try:
                data = self.md_model.api.convert_to_json(self.id, 'manga-cover', cover_response)
            except MDRequestError:
                print("Couldn't get the covers data.")
                return

            covers = data.get('data', [])
            self.md_model.cache.save_cache(cache_json.get("cache_date", datetime.now()), self.id, cache_json.get("data", []), cache_json.get("chapters", []), covers)

        return covers

    def _format_socials(self) -> dict:
        """The social data of the manga."""
        json_social = {"views": self.data["views"]}
        json_social["follows"] = self.data["follows"]
        json_social["comments"] = self.data["comments"]
        json_social["rating"] = self.data["rating"]
        return json_social

    def _title(self) -> dict:
        """General manga information."""
        json_title = {"id": self._manga_args_obj.data.id}
        json_title["url"] = self._manga_args_obj.data.url
        json_title["attributes"] = self._manga_args_obj.data._attributes
        # json_title["social"] = self.social
        return json_title

    def core(self, save_type: int=0) -> None:
        """Format the json for exporting.

        Args:
            save_type (int, optional): Save the covers after all the manga's chapters have been downloaded. Defaults to 0.
        """
        self.new_data = self._title_json
        self.new_data["externalLinks"] = self._links
        # self.new_data["covers"] = self._covers

        # if save_type and self._args.cover_download:
        #     self._download_covers()

        super()._core(save_type)



class BulkJson(JsonBase):

    def __init__(self, md_model) -> None:
        super().__init__(md_model)
        self.bulk_data = self._format_bulk_data()

    def _format_bulk_data(self) -> dict:
        """Get the download type's data and name."""
        json_account = {"id": self.id}
        json_account["link"] = f'{self.domain}/{self.type}/{self.id}'
        json_account["attributes"] = self.data
        return json_account

    def core(self, save_type: int=0) -> None:
        """Format the json for exporting.

        Args:
            save_type (int, optional): Save the covers after all the manga's chapters have been downloaded. Defaults to 0.
        """
        self.new_data = self.bulk_data
        super()._core(save_type)
