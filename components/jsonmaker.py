#!/usr/bin/python3
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

from .constants import ImpVar
from .errors import MdRequestError


class JsonBase:

    def __init__(self, md_model) -> None:
        self.md_model = md_model
        self.type = md_model.download_type
        self.domain = ImpVar.MANGADEX_URL
        self.api_url = ImpVar.MANGADEX_API_URL

        if self.md_model.type_id in (1, 3):
            self.id = md_model.manga_data["data"]["id"]
            self.data = md_model.manga_data["data"]["attributes"]
            self.relationsips = md_model.manga_data["relationships"]

            self.route = Path(md_model.route)
            self.route.mkdir(parents=True, exist_ok=True)
            self.json_path = self.route.joinpath(f'{self.id}_data').with_suffix('.json')
        else:
            self.id = md_model.group_user_list_data["data"]["id"]
            self.data = md_model.group_user_list_data["data"]["attributes"]
            self.relationsips = md_model.group_user_list_data["relationships"]

            self.route = Path(md_model.directory)
            self.route.mkdir(parents=True, exist_ok=True)
            self.json_path = self.route.joinpath(f'{self.type}_{self.id}_data').with_suffix('.json')

        self.data_json = self.checkExist()

    def checkExist(self) -> dict:
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

    def chapters(self, chapter_data: dict) -> dict:
        """Format the chapter data.

        Args:
            chapter_data (dict): The chapter data returned from the api.

        Returns:
            dict: The chapter data as an instance property.
        """
        self.chapter_json = chapter_data
        return self.chapter_json

    def saveJson(self) -> None:
        """Save the json."""
        with open(self.json_path, 'w', encoding='utf8') as json_file:
            json.dump(self.new_data, json_file, indent=4, ensure_ascii=False)

    def addChaptersJson(self) -> None:
        """Add the chapter data to the json."""
        if not self.data_json:
            try:
                if self.chapter_json not in self.new_data["chapters"]:
                    self.new_data["chapters"].append(self.chapter_json)
            except KeyError:
                self.new_data["chapters"] = [self.chapter_json]
        else:
            self.new_data["chapters"] = self.data_json["chapters"]
            try:
                if self.chapter_json not in self.new_data["chapters"]:
                    self.new_data["chapters"].append(self.chapter_json)
            except AttributeError:
                pass

    def core(self, save_type: int=0) -> None:
        """Format the json for exporting.

        Args:
            save_type (int, optional): Save the covers after all the manga's chapters have been downloaded. Defaults to 0.
        """
        if self.md_model.type_id in (1, 3):
            self.new_data = self.title_json
            self.new_data["externalLinks"] = self.links
            self.new_data["relationships"] = self.relationsips
            # self.new_data["covers"] = self.covers
            
            if save_type and self.save_covers:
                self.saveCovers()
        else:
            self.new_data = self.account_data
        
        self.addChaptersJson()
        self.saveJson()



class TitleJson(JsonBase):

    def __init__(self, md_model) -> None:
        super().__init__(md_model)
        self.download_type = md_model.download_type
        self.save_covers = md_model.covers
        self.regex = re.compile(ImpVar.REGEX)

        ### Cover download is disabled due to not being in the api.
        # # Make the covers folder in the manga folder
        # if self.save_covers:
        #     self.cover_route = self.route.joinpath('!covers')
        #     self.cover_route.mkdir(parents=True, exist_ok=True)

        # self.cover_regex = re.compile(r'(?:https\:\/\/mangadex\.org\/images\/(?:manga|covers)\/)(.+)(?:(?:\?.+)|$)')
        # self.cover_url = re.sub(r'\?[0-9]+', '', self.data["mainCover"])
        self.links = self.getLinks()
        # self.social = self.getSocials()
        # self.covers = self.getCovers()
        self.title_json = self.title()

    def getLinks(self) -> dict:
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
                json_links.update({{l: {"name": l, "url": newl}}})
        return json_links

    def downloadCover(self, cover: str, cover_name: str) -> None:
        """Download the cover.

        Args:
            cover (str): Cover url to download.
            cover_name (str): The cover's name for the save file.
        """
        cover_response = self.md_model.requestData(cover, 'cover')

        self.md_model.checkResponseError(cover_response)

        if cover_response.status_code != 200:
            print(f'Could not save {cover_name}...')
            return

        cover_response = cover_response.content

        if not os.path.exists(os.path.join(self.cover_route, cover_name)):
            print(f'Saving cover {cover_name}...')
            with open(os.path.join(self.cover_route, cover_name), 'wb') as file:
                file.write(cover_response)

    def saveCovers(self) -> None:
        """Get the covers to download."""
        json_covers = self.covers
        cover = json_covers["mainCover"]
        cover_name = self.cover_regex.match(cover).group(1)
        cover_name = self.regex.sub('_', html.unescape(cover_name))

        self.downloadCover(cover, cover_name)

        if not isinstance(json_covers["altCovers"], str):
            for c in json_covers["altCovers"]:
                cover_url = c["url"]
                cover_ext = self.cover_regex.match(cover_url).group(1).rsplit('?', 1)[0].rsplit('.', 1)[-1]
                cover_prefix = c["volume"].replace('.', '-')
                cover_prefix = self.regex.sub('_', html.unescape(cover_prefix))
                cover_name = f'alt_{self.id}v{cover_prefix}.{cover_ext}'
                self.downloadCover(cover_url, cover_name)

    def getCovers(self) -> dict:
        """Format the covers into the json.

        Returns:
            dict: A dict of all the covers a manga has.
        """
        cover_response = self.md_model.requestData(f'{self.id}/covers', 'manga')

        try:
            data = self.md_model.convertJson(self.id, 'manga-cover', cover_response)
        except MdRequestError:
            print("Couldn't get the covers data.")
            return

        covers_data = data["data"]

        json_covers = {"mainCover": self.cover_url}
        
        if covers_data:
            json_covers["altCovers"] = covers_data
        else:
            json_covers["altCovers"] = 'This title has no other covers.'
        
        return json_covers

    def getSocials(self) -> dict:
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
        # json_title["title"] = self.data["title"]
        # json_title["altTitles"] = self.data["altTitles"]
        # json_title["language"] = self.data["publication"]["language"]
        # json_title["author"] = ', '.join(self.data["author"])
        # json_title["artist"] = ', '.join(self.data["artist"])
        # json_title["lastChapter"] = self.data["lastChapter"]
        # json_title["isHentai"] = "Yes" if self.data["isHentai"] == True else "No"
        # json_title["social"] = self.social
        return json_title



class AccountJson(JsonBase):

    def __init__(self, md_model) -> None:
        super().__init__(md_model)
        self.account_data = self.accountData()

    def accountData(self) -> dict:
        """Get the account's data and name.

        Returns:
            dict: The extra information provided by the api.
        """
        json_account = {"id": self.id}
        json_account["link"] = f'{self.domain}/{self.type}/{self.id}'
        json_account["attributes"] = self.data
        return json_account
