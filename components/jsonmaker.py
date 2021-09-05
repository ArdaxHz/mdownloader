#!/usr/bin/python3
from datetime import datetime
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

from .constants import ImpVar
from .errors import MDRequestError
from .model import MDownloader


class JsonBase:

    def __init__(self, md_model: MDownloader) -> None:
        self.md_model: MDownloader = md_model
        self.type = md_model.download_type
        self.domain = ImpVar.MANGADEX_URL
        self.api_url = ImpVar.MANGADEX_API_URL
        self.downloaded_ids = []

        if self.md_model.type_id == 1 or self.md_model.manga_download:
            data = md_model.manga_data
            file_prefix = ''
            self.route = Path(md_model.route)
        else:
            data = md_model.data
            file_prefix = f'{self.type}_'
            self.route = Path(md_model.directory)

        self.id = data["data"]["id"]
        self.data = data["data"]["attributes"]
        self.route.mkdir(parents=True, exist_ok=True)
        self.json_path = self.route.joinpath(f'{file_prefix}{self.id}_data').with_suffix('.json')

        self.data_json = self.check_json_exist()
        self.new_data = {}
        self.chapter_data = self.data_json.get('chapters', [])
        self.json_ids = [c["data"]["id"] for c in self.chapter_data] if (self.chapter_data and not self.md_model.force_refresh) else []
        self.chapters_archive = [c["data"]["id"] for c in self.chapter_data if 'chapters_archive' in c and c["chapters_archive"]] if (self.chapter_data and not self.md_model.force_refresh) else []
        self.chapters_folder = [c["data"]["id"] for c in self.chapter_data if 'chapters_folder' in c and c["chapters_folder"]] if (self.chapter_data and not self.md_model.force_refresh) else []

        if self.md_model.args.folder_download:
            self.downloaded_ids.extend(self.chapters_folder)
        else:
            self.downloaded_ids.extend(self.chapters_archive)

        self.downloaded_ids = list(set(self.downloaded_ids))

    def check_json_exist(self) -> dict:
        """Check if the json already exists.

        Returns:
            dict: The loaded json.
        """
        try:
            with open(self.json_path, 'r', encoding='utf8') as file:
                series_json = json.load(file)
            return series_json
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def chapters(self, chapter_data: dict) -> None:
        """Add the chapter data to the json.

        Args:
            chapter_data (dict): The chapter data returned from the api.
        """
        chapter_id = chapter_data["data"]["id"]

        if self.md_model.args.folder_download:
            chapter_data.update({"chapters_folder": True})
        else:
            chapter_data.update({"chapters_archive": True})

        if chapter_id not in self.downloaded_ids:
            self.chapter_data.append(chapter_data)
            self.downloaded_ids.append(chapter_id)

    def save_json(self) -> None:
        """Save the json."""
        with open(self.json_path, 'w', encoding='utf8') as json_file:
            json.dump(self.new_data, json_file, indent=4, ensure_ascii=False)

    def core(self, save_type: int=0) -> None:
        """Format the json for exporting.

        Args:
            save_type (int, optional): Save the covers after all the manga's chapters have been downloaded. Defaults to 0.
        """
        if self.md_model.type_id == 1 or self.md_model.manga_download:
            self.new_data = self.title_json
            self.new_data["externalLinks"] = self.links
            self.new_data["covers"] = self.covers

            if save_type and self.save_covers:
                self.saveCovers()
        else:
            self.new_data = self.bulk_data

        self.new_data["chapters"] = self.chapter_data
        self.save_json()



class TitleJson(JsonBase):

    def __init__(self, md_model: MDownloader) -> None:
        super().__init__(md_model)
        self.download_type = md_model.download_type
        self.save_covers = md_model.args.cover_download
        self.regex = re.compile(ImpVar.CHARA_REGEX)

        # Make the covers folder in the manga folder
        if self.save_covers:
            self.cover_route = self.route.joinpath('!covers')
            self.cover_route.mkdir(parents=True, exist_ok=True)

        self.links = self.format_links()
        # self.social = self.getSocials()
        self.covers = self.get_covers()
        self.title_json = self.title()

    def format_links(self) -> dict:
        """All the manga page's external links.

        Returns:
            dict: The links formatted by name and url.
        """
        if self.data["links"] is None:
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

        for l in self.data["links"]:
            if l == 'bw':
                if re.match(r'series/[0-9]+', l):
                    newl = f'{self.data["links"][l]}/list'
                else:
                    newl = self.data["links"][l]
            elif l == 'nu':
                newl = quote(self.data["links"][l])
            elif l == 'ebj':
                newl = re.sub('https://www.ebookjapan.jp/ebj/', '', self.data["links"][l])
            else:
                newl = self.data["links"][l]

            if l in formats:
                formats[l]["url"] = formats[l]["url"].format(newl)
                json_links.update({l: formats[l]})
            else:
                json_links.update(
                    {l: {"name": l, "url": newl}})
        return json_links

    def download_covers(self, cover_name: str) -> None:
        """Download the cover.

        Args:
            cover_name (str): The cover's name for the save file.
        """
        cover_response = self.md_model.api.request_data(f'{self.md_model.cover_cdn_url}/{self.id}/{cover_name}')

        self.md_model.api.check_response_error(cover_response)

        if cover_response.status_code != 200:
            print(f'Could not save {cover_name}...')
            return

        cover_response = cover_response.content

        if not os.path.exists(os.path.join(self.cover_route, cover_name)):
            print(f'Saving cover {cover_name}...')
            with open(os.path.join(self.cover_route, cover_name), 'wb') as file:
                file.write(cover_response)

    def save_covers(self) -> None:
        """Get the covers to download."""
        json_covers = self.covers
        covers = json_covers["covers"]

        if covers:
            for cover in covers:
                cover_name = cover["data"]["attributes"]["fileName"]
                self.download_covers(cover_name)

    def get_covers(self) -> dict:
        """Format the covers into the json.

        Returns:
            dict: A dict of all the covers a manga has.
        """
        cache_json = self.md_model.cache.load_cache(self.id)
        refresh_cache = self.md_model.cache.check_cache_time(cache_json)
        covers = cache_json.get('covers', [])

        if refresh_cache or not covers:
            cover_response = self.md_model.api.request_data(f'{self.md_model.cover_api_url}', **{"manga[]": self.id, "limit": 100})

            try:
                data = self.md_model.api.convert_to_json(self.id, 'manga-cover', cover_response)
            except MDRequestError:
                print("Couldn't get the covers data.")
                return

            covers = data.get('results', [])
            self.md_model.cache.save_cache(cache_json.get("cache_date", datetime.now()), self.id, cache_json.get("data", []), cache_json.get("chapters", []), covers)

        return covers

    def format_socials(self) -> dict:
        """The social data of the manga.

        Returns:
            dict: The social data of the manga.
        """
        json_social = {"views": self.data["views"]}
        json_social["follows"] = self.data["follows"]
        json_social["comments"] = self.data["comments"]
        json_social["rating"] = self.data["rating"]
        return json_social

    def title(self) -> dict:
        """General manga information.

        Returns:
            dict: The extra information of the manga.
        """
        data_copy = self.data.copy()
        data_copy.pop('links', None)
        json_title = {"id": self.id}
        json_title["link"] = f'{self.domain}/manga/{self.id}'
        json_title["attributes"] = data_copy
        # json_title["social"] = self.social
        return json_title



class BulkJson(JsonBase):

    def __init__(self, md_model: MDownloader) -> None:
        super().__init__(md_model)
        self.bulk_data = self.format_bulk_data()

    def format_bulk_data(self) -> dict:
        """Get the download type's data and name.

        Returns:
            dict: The extra information provided by the api.
        """
        json_account = {"id": self.id}
        json_account["link"] = f'{self.domain}/{self.type}/{self.id}'
        json_account["attributes"] = self.data
        return json_account
