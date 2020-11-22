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

            chapter_json = {}
            chapter_json[chapter_id] = {
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
                chapter_json[chapter_id]["mangaData"] = {
                    "mangaId": chapter_data["mangaId"],
                    "mangaTitle": chapter_data["mangaTitle"],
                    "mangaLink": f'{self.domain}/manga/{chapter_data["mangaId"]}'
                }

            if chapter_data["status"] == "external":
                chapter_json[chapter_id]["images"] = 'This chapter is external to MangaDex so an image list is not available.'
            else:
                chapter_json[chapter_id]["images"] = {}

                try:
                    chapter_data["serverFallback"]
                except KeyError:
                    chapter_json[chapter_id]["images"]["url"] = f'{chapter_data["server"]}{chapter_data["hash"]}/'
                else:
                    chapter_json[chapter_id]["images"]["url"] = f'https://s2.mangadex.org/data/{chapter_data["hash"]}/'

                chapter_json[chapter_id]["images"]["pages"] = chapter_data["pages"]

            self.chapter_json.update(chapter_json)
            return self.chapter_json
        
        else:
            chapter_json = 'This title has no chapters.'
            self.chapter_json = chapter_json
            return self.chapter_json


    def saveJson(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
        with open(self.json_path, 'w') as json_file:
            json.dump(self.data_json, json_file, indent=4, ensure_ascii=False)
        return

    
    def addChaptersJson(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
        if not self.data_json:
            self.data_json["chapters"] = self.chapter_json
        else:
            self.data_json["chapters"] = self.data_json["chapters"]
            self.data_json["chapters"].update(self.chapter_json)
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
        links_json = {}
        try:
            if 'al' in self.data["links"]:
                links_json["anilist"] = quote(f'https://anilist.co/manga/{self.data["links"]["al"]}')
            if 'ap' in self.data["links"]:
                links_json["anime_planet"] = quote(f'https://www.anime-planet.com/manga/{self.data["links"]["ap"]}')
            if 'bw' in self.data["links"]:
                if re.match(r'series/[0-9]+', self.data["links"]["bw"]):
                    links_json["bookwalker"] = quote(f'https://bookwalker.jp/{self.data["links"]["bw"]}/list')
                else:
                    links_json["bookwalker"] = quote(f'https://bookwalker.jp/{self.data["links"]["bw"]}')
            if 'kt' in self.data["links"]:
                links_json["kitsu"] = quote(f'https://kitsu.io/manga/{self.data["links"]["kt"]}')
            if 'mu' in self.data["links"]:
                links_json["manga_updates"] = quote(f'https://www.mangaupdates.com/series.html?id={self.data["links"]["mu"]}')
            if 'nu' in self.data["links"]:
                links_json["novel_updates"] = quote(f'https://www.novelupdates.com/series/{self.data["links"]["nu"]}')
            if 'amz' in self.data["links"]:
                links_json["amazon_jp"] = quote(self.data["links"]["amz"])
            if 'cdj' in self.data["links"]:
                links_json["cd_japan"] = quote(self.data["links"]["cdj"])
            if 'ebj' in self.data["links"]:
                ebj_link = self.data["links"]["ebj"]
                if 'https://www.ebookjapan.jp/ebj/' in ebj_link:
                    new_ebj_link = re.sub(r'https://www.ebookjapan.jp/ebj/', r'https://ebookjapan.yahoo.co.jp/books/', ebj_link)
                    links_json["ebookjapan"] = quote(new_ebj_link)
                else:
                    links_json["ebookjapan"] = quote(ebj_link)
            if 'mal' in self.data["links"]:
                links_json["myanimelist"] = quote(f'https://myanimelist.net/manga/{self.data["links"]["mal"]}')
            if 'raw' in self.data["links"]:
                links_json["raw"] = quote(self.data["links"]["raw"])
            if 'engtl' in self.data["links"]:
                links_json["official_english"] = quote(self.data["links"]["engtl"] )
        except TypeError:
            pass
        return links_json


    def downloadCover(self, cover, cover_name):
        cover_response = requests.get(cover).content
        print(f'Saving cover {cover_name}...')

        if not os.path.exists(os.path.join(self.cover_route, cover_name)):
            with open(os.path.join(self.cover_route, cover_name), 'wb') as file:
                file.write(cover_response)
        return


    def saveCovers(self):
        covers_json = self.covers
        cover = covers_json["mainCover"]
        cover_name = self.cover_regex.match(cover).group(1)
        cover_name = self.regex.sub('_', html.unescape(cover_name))

        self.downloadCover(cover, cover_name)

        if not isinstance(covers_json, str):
            for c in covers_json["altCovers"]:
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

        covers_json = {"mainCover": self.cover_url}
        
        if covers_data:
            covers_json["altCovers"] = covers_data
        else:
            covers_json["altCovers"] = 'This title has no other covers.'
        
        return covers_json


    def getSocials(self):
        socials_json = {"views": self.data["views"]}
        socials_json["follows"] = self.data["follows"]
        socials_json["comments"] = self.data["comments"]
        socials_json["rating"] = self.data["rating"]
        return socials_json


    def title(self):
        title_json = {"id": self.id}
        title_json["title"] = self.data["title"]
        title_json["language"] = self.data["publication"]["language"]
        title_json["author"] = ', '.join(self.data["author"])
        title_json["artist"] = ', '.join(self.data["artist"])
        title_json["lastChapter"] = self.data["lastChapter"]
        title_json["isHentai"] = "Yes" if self.data["isHentai"] == True else "No"
        title_json["link"] = f'{self.domain}/manga/{self.id}'
        title_json["social"] = self.social
        return title_json


    def core(self, save_type):
        self.data_json = self.title_json
        self.data_json["externalLinks"] = self.links
        self.data_json["covers"] = self.covers

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
        account_json = {"id": self.id}
        account_json["name"] =  self.data["name"] if self.type == 'group' else self.data["username"]
        account_json["link"] = f'{self.domain}/{self.type.lower()}/{self.id}'
        return account_json


    def core(self, save_type):
        self.data_json = self.account_data

        self.addChaptersJson()
        self.saveJson()
        return
