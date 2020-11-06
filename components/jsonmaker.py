#!/usr/bin/python3
import os
import re
import html
import json
import requests

from pathlib import Path



class TitleJson:

    def __init__(self, manga_data, route, save_covers):
        self.manga_data = manga_data["manga"]
        self.manga_id = self.manga_data['id']
        self.lang_name = self.getLangs()
        self.lang_name = self.lang_name["md"]
        self.route = Path(route)
        self.json_path = self.route.joinpath(f'{self.manga_id}_data').with_suffix('.json')
        self.data_json = self.checkExist()
        self.save_covers = save_covers
        self.route.mkdir(parents=True, exist_ok=True)
        if self.save_covers == 'save':
            self.cover_route = self.route.joinpath('!covers')
            self.cover_route.mkdir(parents=True, exist_ok=True)
        self.regex = re.compile('[\\\\/:*?"<>|]')
        self.domain = 'https://mangadex.org'
        self.cover_regex = re.compile(r'(?:https\:\/\/mangadex\.org\/images\/(?:manga|covers)\/)(.+)?(?:\?.+)')
        self.cover_url = re.sub(r'\?[0-9]+', '', self.manga_data["mainCover"])
        self.links = self.Link()
        self.social = self.Social()
        self.title_json = self.title()
        self.covers = self.Covers()
        self.chapter_json = {}
        self.json_data = self.core


    def getLangs(self):
        with open('languages.json', 'r') as file:
            languages = json.load(file)
        return languages


    def Link(self):
        json_links = {}
        try:
            if 'al' in self.manga_data["links"]:
                json_links["anilist"] = f'https://anilist.co/manga/{self.manga_data["links"]["al"]}'
            if 'ap' in self.manga_data["links"]:
                json_links["anime_planet"] = f'https://www.anime-planet.com/manga/{self.manga_data["links"]["ap"]}'
            if 'bw' in self.manga_data["links"]:
                if re.match(r'series/[0-9]+', self.manga_data["links"]["bw"]):
                    json_links["bookwalker"] = f'https://bookwalker.jp/{self.manga_data["links"]["bw"]}/list'
                else:
                    json_links["bookwalker"] = f'https://bookwalker.jp/{self.manga_data["links"]["bw"]}'
            if 'kt' in self.manga_data["links"]:
                json_links["kitsu"] = f'https://kitsu.io/manga/{self.manga_data["links"]["kt"]}'
            if 'mu' in self.manga_data["links"]:
                json_links["manga_updates"] = f'https://www.mangaupdates.com/series.html?id={self.manga_data["links"]["mu"]}'
            if 'nu' in self.manga_data["links"]:
                json_links["novel_updates"] = f'https://www.novelupdates.com/series/{self.manga_data["links"]["nu"]}'
            if 'amz' in self.manga_data["links"]:
                json_links["amazon_jp"] = self.manga_data["links"]["amz"]
            if 'cdj' in self.manga_data["links"]:
                json_links["cd_japan"] = self.manga_data["links"]["cdj"]
            if 'ebj' in self.manga_data["links"]:
                json_links["ebookjapan"] = self.manga_data["links"]["ebj"]
            if 'mal' in self.manga_data["links"]:
                json_links["myanimelist"] = f'https://myanimelist.net/manga/{self.manga_data["links"]["mal"]}'
            if 'raw' in self.manga_data["links"]:
                json_links["raw"] = self.manga_data["links"]["raw"]
            if 'engtl' in self.manga_data["links"]:
                json_links["official_english"] = self.manga_data["links"]["engtl"] 
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
        cover = json_covers["main_cover"]
        cover_name = self.cover_regex.match(cover).group(1)
        cover_name = self.regex.sub('_', html.unescape(cover_name))

        self.downloadCover(cover, cover_name)

        for c in json_covers["alt_covers"]:
            cover_name = f'alt_{self.cover_regex.match(c["url"]).group(1)}'
            cover_name = self.regex.sub('_', html.unescape(cover_name))
            self.downloadCover(c, cover_name)
        return


    def Covers(self):
        response = requests.get(f'{self.domain}/api/v2/manga/{self.manga_id}/covers')
        data = response.json()
        covers_data = data['data']

        json_covers = {"main_cover": self.cover_url}
        
        if covers_data:
            json_covers["alt_covers"] = covers_data
        else:
            json_covers["alt_covers"] = 'This title has no other covers.'
        
        return json_covers


    def Social(self):
        json_social = {"views": self.manga_data["views"]}
        json_social["follows"] = self.manga_data["follows"]
        json_social["comments"] = self.manga_data["comments"]
        json_social["rating"] = self.manga_data["rating"]
        return json_social


    def title(self):
        json_title = {"id": self.manga_id}
        json_title["title"] = self.manga_data['title']
        json_title["language"] = self.manga_data["publication"]["language"]
        json_title["author"] = ', '.join(self.manga_data["author"])
        json_title["artist"] = ', '.join(self.manga_data["artist"])
        json_title["last_chapter"] = self.manga_data["lastChapter"]
        json_title["hentai"] = "Yes" if self.manga_data["isHentai"] == True else "No"
        json_title["link"] = f'{self.domain}/manga/{self.manga_id}'
        json_title["social"] = self.social
        return json_title


    def chapters(self, chapter_data):
        if chapter_data is not None:
            chapter_id = chapter_data["id"]

            json_chapter = {}
            json_chapter[chapter_id] = {
                "volume": chapter_data["volume"],
                "chapter": chapter_data["chapter"],
                "title": chapter_data["title"],
                "lang_name": self.lang_name[chapter_data["language"]],
                "lang_code": chapter_data["language"],
                "group(s)": self.regex.sub('_', html.unescape(', '.join( [g["name"] for g in chapter_data["groups"]] ))),
                "timestamp": chapter_data["timestamp"],
                "link": f'{self.domain}/chapter/{chapter_data["id"]}'
            }
            
            if chapter_data["status"] == "external":
                json_chapter[chapter_id]["images"] = 'This chapter is external to MangaDex so an image list is not available.'
            else:
                json_chapter[chapter_id]["images"] = {"url": chapter_data["server"]}
                
                try:
                    json_chapter[chapter_id]["images"]["backup_url"] = chapter_data["serverFallback"]
                except KeyError:
                    pass
                
                json_chapter[chapter_id]["images"]["pages"] = chapter_data["pages"]
            
            self.chapter_json.update(json_chapter)
            return self.chapter_json
        
        else:
            json_chapter = 'This title has no chapters.'
            self.chapter_json = json_chapter
            return self.chapter_json


    def checkExist(self):
        if os.path.exists(self.json_path):
            with open(self.json_path, 'r') as file:
                series_json = json.load(file)
            return series_json
        else:
            return {}            


    def saveJson(self, json_data):
        with open(self.json_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4, ensure_ascii=False)
        return


    def core(self, save_type):
        json_data = self.title_json
        json_data["external_links"] = self.links
        json_data["covers"] = self.covers

        if not self.data_json:
            json_data["chapters"] = self.chapter_json
        else:
            json_data["chapters"] = self.data_json["chapters"]
            json_data["chapters"].update(self.chapter_json)

        if save_type == 1:
            if self.save_covers == 'save':
                self.saveCovers()

        self.saveJson(json_data)
        return



class AccountJSON:

    def __init__(self, data, route, form):
        self.type = form
        self.data = data[self.type]
        self.id = self.data["id"]
        self.route = route
        self.regex = re.compile('[\\\\/:*?"<>|]')
        self.domain = 'https://mangadex.org'
        self.json_path = os.path.join(route, f'{self.type.lower()}_{self.id}_data.json')
        self.data_json = self.checkExist()
        self.account_data = self.accountData()
        self.lang_name = self.getLangs()
        self.lang_name = self.lang_name["md"]        
        self.chapter_json = {}


    def getLangs(self):
        with open('languages.json', 'r') as file:
            languages = json.load(file)
        return languages


    def checkExist(self):
        if os.path.exists(self.json_path):
            with open(self.json_path, 'r') as file:
                data_json = json.load(file)
            return data_json
        else:
            return {}


    def chapters(self, chapter_data):
        chapter_id = chapter_data["id"]

        json_chapter = {}
        json_chapter[chapter_id] = {
            "manga_id": chapter_data["mangaId"],
            "manga_title": chapter_data["mangaTitle"],
            "volume": chapter_data["volume"],
            "chapter": chapter_data["chapter"],
            "title": chapter_data["title"],
            "lang_name": self.lang_name[chapter_data["language"]],
            "lang_code": chapter_data["language"],
            "group(s)": self.regex.sub('_', html.unescape(', '.join( [g["name"] for g in chapter_data["groups"]] ))),
            "timestamp": chapter_data["timestamp"],
            "link": f'{self.domain}/chapter/{chapter_data["id"]}'
        }

        if chapter_data["status"] == "external":
                json_chapter[chapter_id]["images"] = 'This chapter is external to MangaDex so an image list is not available.'
        else:
            json_chapter[chapter_id]["images"] = {"url": chapter_data["server"]}
            
            try:
                json_chapter[chapter_id]["images"]["backup_url"] = chapter_data["serverFallback"]
            except KeyError:
                pass
            
            json_chapter[chapter_id]["images"]["pages"] = chapter_data["pages"]

        self.chapter_json.update(json_chapter)
        return self.chapter_json


    def accountData(self):
        json_account = {"id": self.id}
        json_account["name"] =  self.data['name'] if self.type == 'group' else self.data['username']
        json_account["link"] = f'{self.domain}/{self.type.lower()}/{self.id}'
        return json_account


    def saveJson(self, json_data):
        with open(self.json_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4, ensure_ascii=False)
        return


    def core(self, save_type):
        json_data = self.account_data

        if not self.data_json:
            json_data["chapters"] = self.chapter_json
        else:
            json_data["chapters"] = self.data_json["chapters"]
            json_data["chapters"].update(self.chapter_json)

        self.saveJson(json_data)
        return
