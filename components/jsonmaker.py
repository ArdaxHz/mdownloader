#!/usr/bin/python3
import sys
import os
import time
import requests
import argparse
import re
import html
import json



class titleJson:

    def __init__(self, data, manga_id, route):
        self.data = data["manga"]
        self.manga_id = manga_id
        self.route = route
        self.regex = re.compile('[\\\\/:*?"<>|]')
        self.domain = 'https://mangadex.org'
        self.cover_url = re.sub(r'\?[0-9]+', '', self.data["cover_url"])
        self.links = self.Link()
        self.title_json = self.title()
        # self.chapter_data = self.chapters
        self.chapter_json = []
        self.json_data = self.core


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


    def title(self):
        json_title = {"id": self.manga_id}
        json_title["title"] = self.data['title']
        json_title["language"] = self.data["lang_name"]
        json_title["author"] = self.data["author"]
        json_title["artist"] = self.data["artist"]
        json_title["last_chapter"] = self.data["last_chapter"]
        json_title["hentai"] = "Yes" if self.data["hentai"] == 1 else "No"
        json_title["link"] = f'{self.domain}/manga/{self.manga_id}'
        json_title["cover_url"] = f'{self.domain}{self.cover_url}'
        return json_title


    def chapters(self, chapter_data):
        if chapter_data is not None:
            json_chapter = {"chapter_id": chapter_data["id"]}
            json_chapter["volume"] = chapter_data["volume"]
            json_chapter["chapter"] = chapter_data["chapter"]
            json_chapter["title"] = chapter_data["title"]
            json_chapter["lang_name"] = chapter_data["lang_name"]
            json_chapter["lang_code"] = chapter_data["lang_code"]
            json_chapter["group(s)"] = self.regex.sub('_', html.unescape(', '.join(filter(None, [chapter_data[x] for x in filter(lambda s: s.startswith('group_name'), chapter_data.keys())]))))
            if chapter_data["status"] == "external":
                json_chapter["images"] = 'This chapter is external to MangaDex so image list is not available.'
            else:
                json_chapter["images"] = {"url": chapter_data["server"], "pages": chapter_data["page_array"]}
            
            self.chapter_json.append(json_chapter)
            
            return self.chapter_json
        
        else:
            json_chapter = 'This title has no chapters.'
            self.chapter_json = json_chapter
            return self.chapter_json


    def core(self):
        json_data = self.title_json
        json_data["chapters"] = self.chapter_json
        if not os.path.isdir(self.route):
            os.makedirs(self.route)
        with open(os.path.join(self.route, f'{self.manga_id}_data.json'), 'w') as json_file:
            json.dump(json_data, json_file, indent=4, ensure_ascii=False)        