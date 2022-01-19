#!/usr/bin/python3
from copy import copy
from dataclasses import dataclass
import dataclasses
from datetime import datetime
from pathlib import Path
# import math
# from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import hondana

from .args import ProcessArgs, MDArgs
from .cache import CacheRead
from .image_downloader import ImageDownloader
from .errors import MDownloaderError
from .jsonmaker import BulkJson, TitleJson
from .constants import ImpVar



class Filtering:

    def __init__(self) -> None:
        self.root = Path(".")
        self._group_blacklist_file = self.root.joinpath(ImpVar.GROUP_BLACKLIST_FILE)
        self._group_whitelist_file = self.root.joinpath(ImpVar.GROUP_WHITELIST_FILE)
        self._user_blacklist_file = self.root.joinpath(ImpVar.USER_BLACKLIST_FILE)
        self._user_userlist_file = self.root.joinpath(ImpVar.USER_WHITELIST_FILE)

        self.group_blacklist = self._read_file(self._group_blacklist_file)
        self.group_whitelist = self._read_file(self._group_whitelist_file)
        self.user_blacklist = self._read_file(self._user_blacklist_file)
        self.user_whitelist = self._read_file(self._user_userlist_file)

    def _read_file(self, file_path: str) -> Optional[List[str]]:
        """Opens the text file and loads the ids to filter."""
        try:
            with open(file_path, 'r') as fp:
                filter_list = [line.rstrip('\n') for line in fp.readlines()]
                if not filter_list:
                    return
                return filter_list
        except FileNotFoundError:
            return



async def download_chapters(args: ProcessArgs, manga_args_obj: MDArgs, *, image_downloader_obj: Optional[ImageDownloader]=None, chapters_to_download: List[MDArgs], json_chapters_ids: List[str]) -> None:
    """Loop chapters and call the baseDownloader function.

    Args:
        chapters (list): The chapters to download.
        chapters_data (list): The ids of the downloaded chapters from the data json.
    """
    for chapter in chapters_to_download:

        # if md_model.args.download_in_order and md_model.type_id in (2, 3):
        #     manga_data = md_model.misc.check_manga_data(chapter)
        #     md_model.formatter.format_title(manga_data)

        try:
            await image_downloader_obj.chapter_downloader(chapter)
            # md_model.wait(1)
        except MDownloaderError as e:
            if e: print(e)



async def manga_download(args: ProcessArgs, manga_args_obj: MDArgs, *, chapters: hondana.ChapterFeed=None, bulk_json_obj: BulkJson=None) -> None:
    """Download manga."""
    manga_id = manga_args_obj.id
    download_type = manga_args_obj.type

    manga_cache_obj = CacheRead(args, cache_id=manga_id, cache_type='manga')
    refresh_cache = manga_cache_obj.check_cache_time()

    if manga_args_obj.data or refresh_cache or not bool(manga_cache_obj.cache.data):
        if manga_args_obj.data:
            manga_data: hondana.Manga = manga_args_obj.data
        else:
            manga_data = await args._hondana_client.view_manga(manga_id)
        manga_cache_obj.save_cache(cache_time=datetime.now(), data=manga_data)
    else:
        manga_data = hondana.Manga(args._hondana_client._http, manga_cache_obj.cache.data.copy())

    image_downloader_obj = ImageDownloader(args, manga_data=manga_data)
    manga_args_obj.cache = manga_cache_obj
    manga_args_obj.data = manga_data
    # Initalise json classes and make series folders
    title_json_obj = TitleJson(args, manga_args_obj, image_downloader_obj)
    image_downloader_obj.json_exporter = title_json_obj
    
    manga_args_obj = dataclasses.replace(manga_args_obj, **{"cache": manga_cache_obj, "json_obj": title_json_obj})

    if download_type == 'manga':
        json_chapters_ids = title_json_obj.downloaded_ids

        if refresh_cache or not bool(manga_cache_obj.cache.chapters):
            filtering_obj = Filtering()

            feed_response = await manga_data.feed(
                limit=None,
                translated_language=[args.language],
                excluded_groups=filtering_obj.group_blacklist,
                excluded_uploaders=filtering_obj.user_blacklist,
                includes=hondana.query.ChapterIncludes(manga=False),
                content_rating=[
                    hondana.ContentRating.safe, hondana.ContentRating.suggestive,
                    hondana.ContentRating.erotica, hondana.ContentRating.pornographic],
                order=hondana.query.FeedOrderQuery(
                    volume=hondana.query.Order.descending, chapter=hondana.query.Order.descending))

            manga_cache_obj.save_cache(cache_time=datetime.now(), chapters=copy(feed_response))
            chapters = feed_response.chapters
        else:
            chapters: List[hondana.Chapter] = [hondana.Chapter(args._hondana_client._http, x) for x in manga_cache_obj.cache.chapters]
        # chapter_prefix_dict = await args._hondana_client.get_manga_volumes_and_chapters(manga_id)
        # chapter_prefix_dict.volumes
    else:
        chapters = manga_args_obj.chapters.chapters
        json_chapters_ids = bulk_json_obj.downloaded_ids
        download_type = f'{download_type}-manga'

    chapters_to_download = [MDArgs(id=x.id, type='chapter', data=x, json_obj=title_json_obj if download_type=='manga' else bulk_json_obj) for x in chapters if x.id not in json_chapters_ids]
    # md_model.misc.download_message(0, download_type, title)

    # if args.range_download and download_type == 'manga':
    #     chapters_to_download = md_model.title_misc.download_range_chapters(chapters_to_download)

    await download_chapters(args, manga_args_obj, image_downloader_obj=image_downloader_obj, chapters_to_download=chapters_to_download, json_chapters_ids=json_chapters_ids)
    # md_model.misc.download_message(1, download_type, title)

    # Save the json and covers if selected
    title_json_obj.core(1)


# def bulk_download(md_model) -> None:
#     """Download group, user and list chapters."""
#     download_type = md_model.download_type

#     if md_model.type_id == 2:
#         cache_json = md_model.cache.load_cache(md_model.id)
#         refresh_cache = md_model.cache.check_cache_time(cache_json)
#         data = cache_json.get('data', {})

#         if refresh_cache or not data:
#             response = md_model.api.request_data(f'{md_model.api_url}/{md_model.download_type}/{md_model.id}', **{"includes[]": ["user", "leader", "member"]})
#             data = md_model.api.convert_to_json(md_model.id, download_type, response)

#             md_model.cache.save_cache(datetime.now(), download_id=md_model.id, data=data)
#             md_model.wait()

#         # Order the chapters descending by the order they're released to read
#         md_model.params.update({"order[createdAt]": "desc"})
#         md_model.data = data
#         download_id = md_model.id
#         url = f'{md_model.api_url}/{download_type}/{md_model.id}'
#     else:
#         download_id = f'{md_model.id}-follows'
#         url = f'{md_model.user_api_url}/follows/manga'
#         cache_json = md_model.cache_json

#     name_path = md_model.data["attributes"]
#     md_model.params.update({"includes[]": ["manga"]})

#     if download_type == 'group':
#         md_model.name = name_path["name"]
#         md_model.params.update({"groups[]": md_model.id})
#         md_model.chapter_limit = 100
#     elif download_type == 'user':
#         md_model.name = name_path["username"]
#         md_model.params.update({"uploader": md_model.id})
#         md_model.chapter_limit = 100
#     elif download_type == 'list':
#         owner = [u for u in md_model.data["relationships"] if u["type"] == 'user'][0]
#         owner = owner["attributes"]["username"]
#         md_model.name = f"{owner}'s Custom List"
#     else:
#         owner = name_path["username"]
#         md_model.name = f"{owner}'s Follows List"

#     md_model.misc.download_message(0, download_type, md_model.name)
#     chapters = cache_json.get('chapters', [])

#     if not chapters:
#         chapters = get_chapters(md_model, url)
#         md_model.cache.save_cache(datetime.now(), download_id, md_model.data, chapters)
#         md_model.wait()

#     # Initalise json classes and make series folders
#     bulk_json = BulkJson(md_model)
#     md_model.bulk_json = bulk_json

#     if not md_model.args.download_in_order:
#         print(f"Getting each manga's data from the {download_type} chosen.")

#         titles = {}
#         for chapter in chapters:
#             manga_id = [c["id"] for c in chapter["relationships"] if c["type"] == 'manga'][0]
#             if manga_id in titles:
#                 titles[manga_id]["chapters"].append(chapter)
#             else:
#                 titles[manga_id] = {"mangaId": manga_id, "chapters": [chapter]}

#         md_model.chapters_data = titles

#         print("Finished getting each manga's data, downloading the chapters.")

#         for title in titles:
#             md_model.manga_download = True
#             md_model.manga_id = titles[title]["mangaId"]

#             manga_download(md_model)

#             md_model.manga_download = False
#             md_model.manga_data = {}
#             md_model.wait(0)
#     else:
#         chapters_data = bulk_json.downloaded_ids
#         chapters = md_model.filter.filter_chapters(chapters)
#         download_chapters(md_model, chapters, chapters_data)

#     md_model.misc.download_message(1, download_type, md_model.name)

#     # Save the json
#     bulk_json.core(1)


# def follows_download(md_model) -> None:
#     """Download logged in user follows."""
#     if not md_model.auth.successful_login:
#         raise NotLoggedInError('You need to be logged in to download your follows.')

#     download_type = md_model.download_type
#     response = md_model.api.request_data(f'{md_model.user_api_url}/me', **{"order[createdAt]": "desc"})
#     md_model.data = md_model.api.convert_to_json('follows-user', download_type, response)
#     md_model.wait()

#     md_model.id = md_model.data["id"]
#     md_model.cache_json = {"cache_date": datetime.now(), "data": md_model.data, "chapters": [], "covers": []}

#     bulk_download(md_model)



async def chapter_download(args: ProcessArgs, chapter_args_obj: MDArgs) -> None:
    """Get the chapter data for download."""
    # Connect to API and get chapter info
    chapter_id = chapter_args_obj.id
    download_type = chapter_args_obj.type
    chapter_cache_obj = CacheRead(args, cache_id=chapter_id, cache_type='chapter')

    refresh_cache = chapter_cache_obj.check_cache_time()
    chapter_data = chapter_cache_obj.cache.data

    if refresh_cache or not bool(chapter_data):
        chapter_response = await args._hondana_client.get_chapter(chapter_id, includes=hondana.query.ChapterIncludes(user=False))
        chapter_cache_obj.save_cache(cache_time=datetime.now(), data=chapter_response)
    else:
        chapter_response = hondana.Chapter(args._hondana_client._http, chapter_data.copy())

    manga_cache_obj = CacheRead(args, cache_type='manga')
    if chapter_response.manga is None:
        manga_id = [m["id"] for m in chapter_response._relationships if m["type"] == "manga"][0]
        manga_cache_obj._cache_id = manga_id
        manga_cache_obj.update_cache_obj()
        await chapter_response.get_parent_manga()
    else:
        manga_cache_obj._cache_id = chapter_response.manga.id
        manga_cache_obj.update_cache_obj()

    manga_cache_obj.save_cache(cache_time=datetime.now(), data=chapter_response.manga)

    name = f'{chapter_response.manga.title}: Chapter {chapter_response.chapter}'

    # md_model.misc.download_message(0, download_type, name)

    chapter_args_obj = dataclasses.replace(chapter_args_obj, **{"data": chapter_response, "cache": chapter_cache_obj})
    image_downloader_obj = ImageDownloader(args, chapter_response.manga)
    await image_downloader_obj.chapter_downloader(chapter_args_obj)

    # md_model.misc.download_message(1, download_type, name)
