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
        self.new_data = {}

        if self.md_model.type_id == 1 or self.md_model.manga_download:
            data = md_model.manga_data
            file_prefix = ''
            self.route = Path(md_model.route)
        else:
            data = md_model.data
            file_prefix = f'{self.type}_'
            self.route = Path(md_model.directory)

        self.id = data["id"]
        self.data = data["attributes"]
        self.route.mkdir(parents=True, exist_ok=True)
        self.json_path = self.route.joinpath(f'{file_prefix}{self.id}_data').with_suffix('.json')

        self.data_json = self.check_json_exist()
        self.get_downloaded_chapters()

    def get_downloaded_chapters(self) -> None:
        self.downloaded_ids = []
        self.chapters = self.data_json.get('chapters', [])
        self.json_ids = [c["id"] for c in self.chapters] if self.chapters else []
        self.chapters_archive = [c["id"] for c in self.chapters if 'chapters_archive' in c and c["chapters_archive"]] if self.chapters else []
        self.chapters_folder = [c["id"] for c in self.chapters if 'chapters_folder' in c and c["chapters_folder"]] if self.chapters else []

        if self.md_model.args.folder_download:
            self.downloaded_ids.extend(self.chapters_folder)
        else:
            self.downloaded_ids.extend(self.chapters_archive)

        self.downloaded_ids = list(set(self.downloaded_ids))

    def check_json_exist(self) -> dict:
        """Loads the json if it exists."""
        try:
            with open(self.json_path, 'r', encoding='utf8') as file:
                series_json = json.load(file)
            return series_json
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def add_chapter_data(self, chapter_id: str, chapter_data: dict) -> None:
        """Add the chapter data to the json."""
        self.chapters.append(chapter_data)
        self.downloaded_ids.append(chapter_id)

    def add_exporter_type(self, chapter_data_json: dict) -> dict:
        """Add the type of exporter used for the chapter download."""
        if self.md_model.args.folder_download:
            chapter_data_json.update({"chapters_folder": True})
        else:
            chapter_data_json.update({"chapters_archive": True})
        return chapter_data_json

    def add_chapter(self, chapter_data: dict) -> None:
        """Check if chapter data already in json."""

        chapter_id = chapter_data["id"]
        chapter_data = self.add_exporter_type(chapter_data)

        if chapter_id not in self.downloaded_ids:
            self.add_chapter_data(chapter_id, chapter_data)
        else:
            chapter_data_json = [c for c in self.chapters if c["id"] == chapter_id]

            # Update the chapter data if it exists
            for chapter in chapter_data_json:
                if chapter["hash"] == chapter_data["hash"]:
                    self.chapters[self.chapters.index(chapter)] = self.add_exporter_type(chapter)
                else:
                    self.add_chapter_data(chapter_id, chapter_data)

    def remove_chapter(self, chapter_data: dict) -> None:
        """Remove the chapter data from the data json."""

        chapter_id = chapter_data["id"]
        self.downloaded_ids.remove(chapter_id)

        chapter_data_json = [c for c in self.chapters if c["id"] == chapter_id]
        for chapter in chapter_data_json:
            self.chapters.remove(chapter)

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

        self.new_data["chapters"] = self.chapters
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
        """Formats the manga's external links by name and url."""
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
                json_links.update({l: {"name": l, "url": newl}})
        return json_links

    def download_covers(self, cover_name: str) -> None:
        """Downloads the cover."""
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
                cover_name = cover["attributes"]["fileName"]
                self.download_covers(cover_name)

    def get_covers(self) -> dict:
        """Fetches a dict of the manga's covers."""
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

            covers = data.get('data', [])
            self.md_model.cache.save_cache(cache_json.get("cache_date", datetime.now()), self.id, cache_json.get("data", []), cache_json.get("chapters", []), covers)

        return covers

    def format_socials(self) -> dict:
        """The social data of the manga."""
        json_social = {"views": self.data["views"]}
        json_social["follows"] = self.data["follows"]
        json_social["comments"] = self.data["comments"]
        json_social["rating"] = self.data["rating"]
        return json_social

    def title(self) -> dict:
        """General manga information."""
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
        """Get the download type's data and name."""
        json_account = {"id": self.id}
        json_account["link"] = f'{self.domain}/{self.type}/{self.id}'
        json_account["attributes"] = self.data
        return json_account
