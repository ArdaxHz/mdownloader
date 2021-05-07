#!/usr/bin/python3
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

import requests

from .constants import ImpVar



class JsonBase:

    def __init__(self, md_model):
        self.session = md_model.session
        self.type = md_model.download_type
        self.data = md_model.data["data"]
        self.relationsips = md_model.data["relationships"]
        self.id = self.data["id"]
        self.route = Path(md_model.route)
        self.route.mkdir(parents=True, exist_ok=True)
        self.domain = ImpVar.MANGADEX_URL
        self.api_url = ImpVar.MANGADEX_API_URL

        # Format json name
        if self.type == 'manga':
            self.json_path = self.route.joinpath(f'{self.id}_data').with_suffix('.json')
        else:
            self.json_path = self.route.joinpath(f'{self.type}_{self.id}_data').with_suffix('.json')

        self.data_json = self.checkExist()


    # Check if the json already exists
    def checkExist(self) -> dict:
        try:
            with open(self.json_path, 'r', encoding='utf8') as file:
                series_json = json.load(file)

            return series_json
        except (FileNotFoundError, json.JSONDecodeError):
            return {}


    # Format the chapter data
    def chapters(self, chapter_data: dict) -> dict:
        self.chapter_json = chapter_data
        return self.chapter_json


    # Save the json
    def saveJson(self):
        with open(self.json_path, 'w', encoding='utf8') as json_file:
            json.dump(self.new_data, json_file, indent=4, ensure_ascii=False)
        return

    
    # Add the chapter data to the json
    def addChaptersJson(self):
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
        return



class TitleJson(JsonBase):

    def __init__(self, md_model):
        super().__init__(md_model)
        self.download_type = md_model.download_type
        self.save_covers = md_model.save_covers
        self.regex = re.compile(ImpVar.REGEX)

        # Make the covers folder in the manga folder
        if self.save_covers:
            self.cover_route = self.route.joinpath('!covers')
            self.cover_route.mkdir(parents=True, exist_ok=True)

        self.cover_regex = re.compile(r'(?:https\:\/\/mangadex\.org\/images\/(?:manga|covers)\/)(.+)(?:(?:\?.+)|$)')
        self.cover_url = re.sub(r'\?[0-9]+', '', self.data["mainCover"])
        self.links = self.getLinks()
        # self.social = self.getSocials()
        # self.covers = self.getCovers()
        self.title_json = self.title()


    # All the manga page's external links
    def getLinks(self) -> dict:
        json_links = {}
        try:
            if 'al' in self.data["links"]:
                json_links["anilist"] = f'https://anilist.co/manga/{self.data["links"]["al"]}'
            if 'ap' in self.data["links"]:
                json_links["anime_planet"] = f'https://www.anime-planet.com/manga/{quote(self.data["links"]["ap"])}'
            if 'bw' in self.data["links"]:
                if re.match(r'series/[0-9]+', self.data["links"]["bw"]):
                    json_links["bookwalker"] = f'https://bookwalker.jp/{self.data["links"]["bw"]}/list'
                else:
                    json_links["bookwalker"] = f'https://bookwalker.jp/{self.data["links"]["bw"]}'
            if 'kt' in self.data["links"]:
                json_links["kitsu"] = f'https://kitsu.io/manga/{self.data["links"]["kt"]}'
            if 'mu' in self.data["links"]:
                json_links["manga_updates"] = f'https://www.mangaupdates.com/series.html?id={self.data["links"]["mu"]}'
            if 'nu' in self.data["links"]:
                json_links["novel_updates"] = f'https://www.novelupdates.com/series/{quote(self.data["links"]["nu"])}'
            if 'amz' in self.data["links"]:
                json_links["amazon_jp"] = self.data["links"]["amz"]
            if 'cdj' in self.data["links"]:
                json_links["cd_japan"] = self.data["links"]["cdj"]
            if 'ebj' in self.data["links"]:
                ebj_link = self.data["links"]["ebj"]
                if 'https://www.ebookjapan.jp/ebj/' in ebj_link:
                    new_ebj_link = re.sub('https://www.ebookjapan.jp/ebj/', 'https://ebookjapan.yahoo.co.jp/books/', ebj_link)
                    json_links["ebookjapan"] = new_ebj_link
                else:
                    json_links["ebookjapan"] = ebj_link
            if 'mal' in self.data["links"]:
                json_links["myanimelist"] = f'https://myanimelist.net/manga/{self.data["links"]["mal"]}'
            if 'raw' in self.data["links"]:
                json_links["raw"] = self.data["links"]["raw"]
            if 'engtl' in self.data["links"]:
                json_links["official_english"] = self.data["links"]["engtl"]
        except TypeError:
            pass
        return json_links


    # Download the cover
    def downloadCover(self, cover: str, cover_name: str):
        cover_response = self.session.get(cover)

        if cover_response.status_code != 200:
            print(f'Could not save {cover_name}...')
            return
        else:
            cover_response = cover_response.content

        if not os.path.exists(os.path.join(self.cover_route, cover_name)):
            print(f'Saving cover {cover_name}...')
            with open(os.path.join(self.cover_route, cover_name), 'wb') as file:
                file.write(cover_response)
        return


    # Get the covers to download
    def saveCovers(self):
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
        return


    # Format the covers into the json
    def getCovers(self) -> dict:
        response = self.session.get(f'{self.api_url}/manga/{self.id}/covers')
        data = response.json()
        covers_data = data["data"]

        json_covers = {"mainCover": self.cover_url}
        
        if covers_data:
            json_covers["altCovers"] = covers_data
        else:
            json_covers["altCovers"] = 'This title has no other covers.'
        
        return json_covers


    # The social data of the manga
    def getSocials(self) -> dict:
        json_social = {"views": self.data["views"]}
        json_social["follows"] = self.data["follows"]
        json_social["comments"] = self.data["comments"]
        json_social["rating"] = self.data["rating"]
        return json_social


    # General manga information
    def title(self) -> dict:
        json_title = {"id": self.id}
        json_title["title"] = self.data["title"]
        json_title["link"] = self.domain.format('manga', self.id)
        json_title["language"] = self.data["publication"]["language"]
        json_title["author"] = ', '.join(self.data["author"])
        json_title["artist"] = ', '.join(self.data["artist"])
        json_title["lastChapter"] = self.data["lastChapter"]
        json_title["isHentai"] = "Yes" if self.data["isHentai"] == True else "No"
        # json_title["social"] = self.social
        return json_title


    # Format the json for exporting
    def core(self, save_type: int=0):
        self.new_data = self.title_json

        self.new_data["externalLinks"] = self.links
        # self.new_data["covers"] = self.covers
        
        if save_type and self.save_covers:
            self.saveCovers()
        
        self.addChaptersJson()
        self.saveJson()
        return



class AccountJson(JsonBase):

    def __init__(self, md_model):
        super().__init__(md_model)
        self.account_data = self.accountData()


    # Get the account name
    def accountData(self) -> dict:
        json_account = {"id": self.id}
        json_account["name"] = self.data["name"] if self.type == 'group' else self.data["username"]
        json_account["link"] = self.domain.format(self.type, self.id)
        return json_account


    # Format the json for exporting
    def core(self, save_type: int=0):
        self.new_data = self.account_data
        self.addChaptersJson()
        self.saveJson()
        return
