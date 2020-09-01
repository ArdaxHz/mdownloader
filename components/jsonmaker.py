#!/usr/bin/python3
import os
import re
import html
import json
import requests

from pathlib import Path



class titleJson:

    def __init__(self, data, manga_id, route, save_covers):
        self.data = data["manga"]
        self.manga_id = manga_id
        self.route = Path(route)
        self.save_covers = save_covers
        self.route.mkdir(parents=True, exist_ok=True)
        if self.save_covers == 'save':
            self.cover_route = self.route.joinpath('!covers')
            self.cover_route.mkdir(parents=True, exist_ok=True)
        self.regex = re.compile('[\\\\/:*?"<>|]')
        self.domain = 'https://mangadex.org'
        self.cover_regex = re.compile(r'(?:https\:\/\/mangadex\.org\/images\/(?:manga|covers)\/)(.+)')
        self.cover_url = re.sub(r'\?[0-9]+', '', self.data["cover_url"])
        self.links = self.Link()
        self.title_json = self.title()
        self.covers = self.Covers()
        self.chapter_json = []
        self.json_data = self.core()


    def Link(self):
        json_links = {}
        try:
            if 'al' in self.data["links"]:
                json_links["anilist"] = f'https://anilist.co/manga/{self.data["links"]["al"]}'
            if 'ap' in self.data["links"]:
                json_links["anime_planet"] = f'https://www.anime-planet.com/manga/{self.data["links"]["ap"]}'
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
                json_links["novel_updates"] = f'https://www.novelupdates.com/series/{self.data["links"]["nu"]}'
            if 'amz' in self.data["links"]:
                json_links["amazon_jp"] = self.data["links"]["amz"]
            if 'cdj' in self.data["links"]:
                json_links["cd_japan"] = self.data["links"]["cdj"]
            if 'ebj' in self.data["links"]:
                json_links["ebookjapan"] = self.data["links"]["ebj"]
            if 'mal' in self.data["links"]:
                json_links["myanimelist"] = f'https://myanimelist.net/manga/{self.data["links"]["mal"]}'
            if 'raw' in self.data["links"]:
                json_links["raw"] = self.data["links"]["raw"]
            if 'engtl' in self.data["links"]:
                json_links["official_english"] = self.data["links"]["engtl"] 
        except TypeError:
            pass

        return json_links


    def downloadCover(self, cover, cover_name):
        cover_response = requests.get(cover).content

        with open(os.path.join(self.cover_route, cover_name), 'wb') as file:
            file.write(cover_response)


    def saveCovers(self):
        json_covers = self.covers
        cover = json_covers["latest_cover"]
        cover_name = self.cover_regex.match(cover).group(1)

        self.downloadCover(cover, cover_name)

        for c in json_covers["alt_covers"]:
            cover_name = f'alt_{self.cover_regex.match(c).group(1)}'
            self.downloadCover(c, cover_name)


    def Covers(self):
        json_covers = {"latest_cover": f'{self.domain}{self.cover_url}'}
        json_covers["alt_covers"] = []
        for cover in self.data["covers"]:
            cover = f'{self.domain}{cover}'
            json_covers["alt_covers"].append(cover)

        return json_covers


    def title(self):
        json_title = {"id": self.manga_id}
        json_title["title"] = self.data['title']
        json_title["language"] = self.data["lang_name"]
        json_title["author"] = self.data["author"]
        json_title["artist"] = self.data["artist"]
        json_title["last_chapter"] = self.data["last_chapter"]
        json_title["hentai"] = "Yes" if self.data["hentai"] == 1 else "No"
        json_title["link"] = f'{self.domain}/manga/{self.manga_id}'
        return json_title


    def chapters(self, chapter_data):
        if chapter_data is not None:
            json_chapter = {"chapter_id": chapter_data["id"]}
            json_chapter["volume"] = chapter_data["volume"]
            json_chapter["chapter"] = chapter_data["chapter"]
            json_chapter["title"] = chapter_data["title"]
            json_chapter["lang_name"] = chapter_data["lang_name"]
            json_chapter["lang_code"] = chapter_data["lang_code"]
            json_chapter["group(s)"] = self.regex.sub('_', html.unescape( ', '.join(filter(None, [chapter_data[x] for x in filter(lambda s: s.startswith('group_name'), chapter_data.keys()) ])) ))
            
            if chapter_data["status"] == "external":
                json_chapter["images"] = 'This chapter is external to MangaDex so an image list is not available.'
            else:
                json_chapter["images"] = {"url": chapter_data["server"]}
                
                try:
                    json_chapter["images"]["backup_url"] = chapter_data["server_fallback"]
                except KeyError:
                    pass
                
                json_chapter["images"]["pages"] = chapter_data["page_array"]
            
            self.chapter_json.append(json_chapter)
            
            return self.chapter_json
        
        else:
            json_chapter = 'This title has no chapters.'
            self.chapter_json = json_chapter
            return self.chapter_json


    def saveJson(self):
        if self.save_covers == 'save':
            self.saveCovers()
        
        with open(os.path.join(self.route, f'{self.manga_id}_data.json'), 'w') as json_file:
            json.dump(self.json_data, json_file, indent=4, ensure_ascii=False)


    def core(self):
        json_data = self.title_json
        json_data["covers"] = self.covers
        json_data["chapters"] = self.chapter_json

        return json_data
