#!/usr/bin/python3
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

import requests


class Base:

    def __init__(self, data, route, form):
        self.type = form
        self.data = data[self.type]
        self.id = self.data["id"]
        self.route = Path(route)
        self.route.mkdir(parents=True, exist_ok=True)
        self.domain = 'https://mangadex.org'
        
        if self.type == 'manga':
            self.json_path = self.route.joinpath(f'{self.id}_data').with_suffix('.json')
        else:
            self.json_path = self.route.joinpath(f'{self.type.lower()}_{self.id}_data').with_suffix('.json')
        
        self.data_json = self.checkExist()
        self.lang_name = self.getLangs()
        self.lang_name = self.lang_name["md"]
        self.chapter_json = {}


    def getLangs(self):
        with open('languages.json', 'r') as file:
            languages = json.load(file)
        return languages


    def checkExist(self):
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r') as file:
                    series_json = json.load(file)
                return series_json
            except json.JSONDecodeError:
                return {}
        else:
            return {}


    def chapters(self, chapter_data):
        if chapter_data is not None:
            chapter_id = chapter_data["id"]

            json_chapter = {}
            json_chapter[chapter_id] = {
                "volume": chapter_data["volume"],
                "chapter": chapter_data["chapter"],
                "title": chapter_data["title"],
                "langName": self.lang_name[chapter_data["language"]],
                "langCode": chapter_data["language"],
                "groups": chapter_data["groups"],
                "timestamp": chapter_data["timestamp"],
                "link": f'{self.domain}/chapter/{chapter_data["id"]}'
            }

            if self.type != 'manga':
                json_chapter[chapter_id]["mangaData"] = {
                    "mangaId": chapter_data["mangaId"],
                    "mangaTitle": chapter_data["mangaTitle"],
                    "mangaLink": f'{self.domain}/manga/{chapter_data["mangaId"]}'
                }

            if chapter_data["status"] == "external":
                json_chapter[chapter_id]["images"] = 'This chapter is external to MangaDex so an image list is not available.'
            else:
                json_chapter[chapter_id]["images"] = {}

                try:
                    chapter_data["serverFallback"]
                except KeyError:
                    json_chapter[chapter_id]["images"]["url"] = f'{chapter_data["server"]}{chapter_data["hash"]}/'
                else:
                    json_chapter[chapter_id]["images"]["url"] = f'https://s2.mangadex.org/data/{chapter_data["hash"]}/'

                json_chapter[chapter_id]["images"]["pages"] = chapter_data["pages"]

            self.chapter_json.update(json_chapter)
            return self.chapter_json
        
        else:
            json_chapter = 'This title has no chapters.'
            self.chapter_json = json_chapter
            return self.chapter_json


    def saveJson(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
        with open(self.json_path, 'w') as json_file:
            json.dump(self.new_data, json_file, indent=4, ensure_ascii=False)
        return

    
    def addChaptersJson(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
        if not self.data_json:
            self.new_data["chapters"] = self.chapter_json
        else:
            self.new_data["chapters"] = self.data_json["chapters"]
            self.new_data["chapters"].update(self.chapter_json)
        return


class TitleJson(Base):

    def __init__(self, manga_data, route, save_covers):
        super().__init__(manga_data, route, 'manga')
        self.save_covers = save_covers
        self.regex = re.compile('[\\\\/:*?"<>|]')
        if self.save_covers == 'save':
            self.cover_route = self.route.joinpath('!covers')
            self.cover_route.mkdir(parents=True, exist_ok=True)
        self.cover_regex = re.compile(r'(?:https\:\/\/mangadex\.org\/images\/(?:manga|covers)\/)(.+)(?:(?:\?.+)|$)')
        self.cover_url = re.sub(r'\?[0-9]+', '', self.data["mainCover"])
        self.links = self.getLinks()
        self.social = self.getSocials()
        self.title_json = self.title()
        self.covers = self.getCovers()


    def getLinks(self):
        json_links = {}
        try:
            if 'al' in self.data["links"]:
                json_links["anilist"] = quote(f'https://anilist.co/manga/{self.data["links"]["al"]}')
            if 'ap' in self.data["links"]:
                json_links["anime_planet"] = quote(f'https://www.anime-planet.com/manga/{self.data["links"]["ap"]}')
            if 'bw' in self.data["links"]:
                if re.match(r'series/[0-9]+', self.data["links"]["bw"]):
                    json_links["bookwalker"] = quote(f'https://bookwalker.jp/{self.data["links"]["bw"]}/list')
                else:
                    json_links["bookwalker"] = quote(f'https://bookwalker.jp/{self.data["links"]["bw"]}')
            if 'kt' in self.data["links"]:
                json_links["kitsu"] = quote(f'https://kitsu.io/manga/{self.data["links"]["kt"]}')
            if 'mu' in self.data["links"]:
                json_links["manga_updates"] = quote(f'https://www.mangaupdates.com/series.html?id={self.data["links"]["mu"]}')
            if 'nu' in self.data["links"]:
                json_links["novel_updates"] = quote(f'https://www.novelupdates.com/series/{self.data["links"]["nu"]}')
            if 'amz' in self.data["links"]:
                json_links["amazon_jp"] = quote(self.data["links"]["amz"])
            if 'cdj' in self.data["links"]:
                json_links["cd_japan"] = quote(self.data["links"]["cdj"])
            if 'ebj' in self.data["links"]:
                ebj_link = self.data["links"]["ebj"]
                if 'https://www.ebookjapan.jp/ebj/' in ebj_link:
                    new_ebj_link = re.sub(r'https://www.ebookjapan.jp/ebj/', r'https://ebookjapan.yahoo.co.jp/books/', ebj_link)
                    json_links["ebookjapan"] = quote(new_ebj_link)
                else:
                    json_links["ebookjapan"] = quote(ebj_link)
            if 'mal' in self.data["links"]:
                json_links["myanimelist"] = quote(f'https://myanimelist.net/manga/{self.data["links"]["mal"]}')
            if 'raw' in self.data["links"]:
                json_links["raw"] = quote(self.data["links"]["raw"])
            if 'engtl' in self.data["links"]:
                json_links["official_english"] = quote(self.data["links"]["engtl"] )
        except TypeError:
            pass
        return json_links


    def downloadCover(self, cover, cover_name):
        cover_response = requests.get(cover).content
        print(f'Saving cover {cover_name}...')

        if not os.path.exists(os.path.join(self.cover_route, cover_name)):
            with open(os.path.join(self.cover_route, cover_name), 'wb') as file:
                file.write(cover_response)
        return


    def saveCovers(self):
        json_covers = self.covers
        cover = json_covers["mainCover"]
        cover_name = self.cover_regex.match(cover).group(1)
        cover_name = self.regex.sub('_', html.unescape(cover_name))

        self.downloadCover(cover, cover_name)

        if not isinstance(json_covers, str):
            for c in json_covers["altCovers"]:
                cover_url = c["url"]
                cover_ext = self.cover_regex.match(cover_url).group(1).rsplit('?', 1)[0].rsplit('.', 1)[-1]
                cover_prefix = c["volume"].replace('.', '-')
                cover_prefix = self.regex.sub('_', html.unescape(cover_prefix))
                cover_name = f'alt_{self.id}v{cover_prefix}.{cover_ext}'
                self.downloadCover(cover_url, cover_name)
        return


    def getCovers(self):
        response = requests.get(f'{self.domain}/api/v2/manga/{self.id}/covers')
        data = response.json()
        covers_data = data["data"]

        json_covers = {"mainCover": self.cover_url}
        
        if covers_data:
            json_covers["altCovers"] = covers_data
        else:
            json_covers["altCovers"] = 'This title has no other covers.'
        
        return json_covers


    def getSocials(self):
        json_social = {"views": self.data["views"]}
        json_social["follows"] = self.data["follows"]
        json_social["comments"] = self.data["comments"]
        json_social["rating"] = self.data["rating"]
        return json_social


    def title(self):
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


    def core(self, save_type):
        self.new_data = self.title_json
        self.new_data["externalLinks"] = self.links
        self.new_data["covers"] = self.covers

        self.addChaptersJson()

        if save_type == 1:
            if self.save_covers == 'save':
                self.saveCovers()

        self.saveJson()
        return



class AccountJSON(Base):

    def __init__(self, data, route, form):
        super().__init__(data, route, form)
        self.account_data = self.accountData()


    def accountData(self):
        json_account = {"id": self.id}
        json_account["name"] =  self.data["name"] if self.type == 'group' else self.data["username"]
        json_account["link"] = f'{self.domain}/{self.type.lower()}/{self.id}'
        return json_account


    def core(self, save_type):
        self.new_data = self.account_data

        self.addChaptersJson()
        self.saveJson()
        return
