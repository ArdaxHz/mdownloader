#!/usr/bin/python3
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

import requests

from .languages import languages_names



class JsonBase:

    def __init__(self, data: dict, route: str, form: str):
        self.type = form
        self.data = data[self.type]
        self.id = self.data["id"]
        self.route = Path(route)
        self.route.mkdir(parents=True, exist_ok=True)
        self.domain = 'https://mangadex.org'

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

            if isinstance(series_json["chapters"], dict):
                chapters_json_to_list = []

                for chapter_id in series_json["chapters"]:
                    chapter_data = series_json["chapters"][chapter_id]
                    
                    temp_json = {
                        "id": int(chapter_id)
                        }
                    
                    if 'lang_name' in series_json["chapters"][chapter_id]:
                        temp_json["volume"] = chapter_data["volume"]
                        temp_json["chapter"] = chapter_data["chapter"]
                        temp_json["title"] = chapter_data["title"]
                        temp_json["langName"] = chapter_data["lang_name"]
                        temp_json["langCode"] = chapter_data["lang_code"]
                        temp_json["groups"] = chapter_data["group(s)"]
                        temp_json["timestamp"] = chapter_data["timestamp"]
                        temp_json["link"] = f'{self.domain}/chapter/{chapter_id}'
                        temp_json["images"] = {}
                        
                        try:
                            temp_json["images"]["url"] = chapter_data["images"]["backup_url"]
                        except KeyError:
                            temp_json["images"]["url"] = chapter_data["images"]["url"]

                        temp_json["images"]["pages"] = chapter_data["images"]["pages"]
                        
                        try:
                            temp_json["mangaData"] = {
                                "mangaId": chapter_data["manga_id"],
                                "mangaTitle": chapter_data["manga_title"],
                                "mangaLink": f'{self.domain}/manga/{chapter_data["manga_id"]}'
                            }
                        except KeyError:
                            if self.type == 'manga':
                                temp_json["mangaData"] = {
                                    "mangaId": self.id,
                                    "mangaTitle": self.data["title"],
                                    "mangaLink": f'{self.domain}/manga/{self.id}'
                                }
                    else:
                        temp_json.update(chapter_data)

                    chapters_json_to_list.append(temp_json)

                series_json["chapters"] = chapters_json_to_list

            return series_json
        except (FileNotFoundError, json.JSONDecodeError):
            return {}


    # Format the chapter data
    def chapters(self, chapter_data: dict) -> dict:

        json_chapter = {
            "id": chapter_data["id"],
            "chapter": chapter_data["chapter"],
            "volume": chapter_data["volume"],
            "title": chapter_data["title"],
            "langName": languages_names.get(chapter_data["language"], "Other"),
            "langCode": chapter_data["language"],
            "groups": chapter_data["groups"],
            "timestamp": chapter_data["timestamp"],
            "hash": chapter_data["hash"],
            "link": f'{self.domain}/chapter/{chapter_data["id"]}'
        }

        if chapter_data["status"] == "external":
            json_chapter["images"] = 'This chapter is external to MangaDex so an image list is not available.'
        else:
            json_chapter["images"] = {}

            if 'serverFallback' in chapter_data:
                json_chapter["images"]["url"] = f'{chapter_data["serverFallback"]}{chapter_data["hash"]}/'
            else:
                json_chapter["images"]["url"] = f'{chapter_data["server"]}{chapter_data["hash"]}/'                   

            json_chapter["images"]["pages"] = chapter_data["pages"]

        if self.type != 'manga':
            json_chapter["mangaData"] = {
                "mangaId": chapter_data["mangaId"],
                "mangaTitle": chapter_data["mangaTitle"],
                "mangaLink": f'{self.domain}/manga/{chapter_data["mangaId"]}'
            }

        self.chapter_json = json_chapter
        return self.chapter_json


    # Save the json
    def saveJson(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
        with open(self.json_path, 'w', encoding='utf8') as json_file:
            json.dump(self.new_data, json_file, indent=4, ensure_ascii=False)
        return

    
    # Add the chapter data to the json
    def addChaptersJson(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
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

    def __init__(self, data: dict, route: str, save_covers: bool):
        super().__init__(data, route, 'manga')
        self.save_covers = save_covers
        self.regex = re.compile('[\\\\/:*?"<>|]')
        
        # Make the covers folder in the manga folder
        if self.save_covers:
            self.cover_route = self.route.joinpath('!covers')
            self.cover_route.mkdir(parents=True, exist_ok=True)
        
        self.cover_regex = re.compile(r'(?:https\:\/\/mangadex\.org\/images\/(?:manga|covers)\/)(.+)(?:(?:\?.+)|$)')
        self.cover_url = re.sub(r'\?[0-9]+', '', self.data["mainCover"])
        self.links = self.getLinks()
        self.social = self.getSocials()
        self.title_json = self.title()
        self.covers = self.getCovers()


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
                    new_ebj_link = re.sub(r'https://www.ebookjapan.jp/ebj/', r'https://ebookjapan.yahoo.co.jp/books/', ebj_link)
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
        cover_response = requests.get(cover).content

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
        response = requests.get(f'https://api.mangadex.org/v2/manga/{self.id}/covers')
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
        json_title["language"] = self.data["publication"]["language"]
        json_title["author"] = ', '.join(self.data["author"])
        json_title["artist"] = ', '.join(self.data["artist"])
        json_title["lastChapter"] = self.data["lastChapter"]
        json_title["isHentai"] = "Yes" if self.data["isHentai"] == True else "No"
        json_title["link"] = f'{self.domain}/manga/{self.id}'
        json_title["social"] = self.social
        return json_title


    # Format the json for exporting
    def core(self, save_type: int):
        self.new_data = self.title_json
        self.new_data["externalLinks"] = self.links
        self.new_data["covers"] = self.covers

        self.addChaptersJson()

        if save_type and self.save_covers:
            self.saveCovers()

        self.saveJson()
        return



class AccountJson(JsonBase):

    def __init__(self, data: dict, route: str, form: str):
        super().__init__(data, route, form)
        self.account_data = self.accountData()


    # Get the account name
    def accountData(self) -> dict:
        json_account = {"id": self.id}
        json_account["name"] =  self.data["name"] if self.type == 'group' else self.data["username"]
        json_account["link"] = f'{self.domain}/{self.type}/{self.id}'
        return json_account


    # Format the json for exporting
    def core(self, save_type: int):
        self.new_data = self.account_data

        self.addChaptersJson()
        self.saveJson()
        return
