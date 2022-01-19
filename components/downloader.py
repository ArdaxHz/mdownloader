#!/usr/bin/python3
from dataclasses import dataclass
import dataclasses
from datetime import datetime
# import math
# from datetime import datetime
from typing import TYPE_CHECKING

import hondana

from components.cache import CacheRead

from .image_downloader import ImageDownloader
# from .errors import MDownloaderError, NotLoggedInError
# from .jsonmaker import BulkJson, TitleJson
# from .model import MDownloader


if TYPE_CHECKING:
    from .main import MDArgs, ProcessArgs

# def download_chapters(md_model: MDownloader, chapters: list, chapters_data: list) -> None:
#     """Loop chapters and call the baseDownloader function.

#     Args:
#         chapters (list): The chapters to download.
#         chapters_data (list): The ids of the downloaded chapters from the data json.
#     """
#     for chapter in chapters:
#         chapter_id = chapter["id"]
#         md_model.chapter_id = chapter_id
#         md_model.chapter_data = chapter

#         if md_model.args.download_in_order and md_model.type_id in (2, 3):
#             manga_data = md_model.misc.check_manga_data(chapter)
#             md_model.formatter.format_title(manga_data)

#         try:
#             if chapter_id not in chapters_data:
#                 chapter_downloader(md_model)
#                 md_model.wait(1)
#         except MDownloaderError as e:
#             if e: print(e)


# def get_chapters(md_model: MDownloader, url: str) -> list:
#     """Go through each page in the api to get all the chapters.

#     Args:
#         url (str): Request url.

#     Returns:
#         list: A list of all the chapters by the chosen method of download.
#     """
#     chapters = []
#     limit = md_model.chapter_limit
#     offset = 0
#     pages = 1
#     iteration = 1
#     created_at_since_time = '2000-01-01T00:00:00'

#     parameters = {"translatedLanguage[]": md_model.args.language, "contentRating[]": ["safe","suggestive","erotica", "pornographic"]}
#     parameters.update(md_model.params)

#     while True:
#         # Update the parameters with the new offset
#         parameters.update({
#             "limit": limit,
#             "offset": offset,
#             'createdAtSince': created_at_since_time
#         })

#         # Call the api and get the json data
#         chapters_response = md_model.api.request_data(url, True, **parameters)
#         chapters_response_data = md_model.api.convert_to_json(md_model.id, f'{md_model.download_type}-chapters', chapters_response)

#         chapters.extend(chapters_response_data["data"])
#         offset += limit

#         if md_model.type_id == 3:
#             print('Downloading only the first page of the follows.')
#             break

#         # Finds how many pages needed to be called
#         if pages == 1:
#             chapters_count = md_model.misc.check_for_chapters(chapters_response_data)
#             if chapters_count > limit:
#                 pages = math.ceil(chapters_count / limit)

#             print(f"{pages} page(s) to go through.")

#         # Wait every 5 pages
#         if iteration % 5 == 0 and pages != 5:
#             md_model.wait(3)

#         # End the loop when all the pages have been gone through
#         # Offset 10000 is the highest you can go,
#         # reset offset and get next 10k batch using
#         # the last available chapter's created at date
#         if iteration == pages or offset == 10000 or not chapters_response_data["data"]:
#             if chapters_count >= 10000 and offset == 10000:
#                 print('Reached 10k chapters, looping over next 10k.')
#                 created_at_since_time = chapters[-1]["attributes"]["createdAt"].split('+')[0]
#                 offset = 0
#                 pages = 1
#                 iteration = 1
#                 md_model.wait(5)
#                 continue
#             break

#         iteration += 1
#         md_model.wait(0)

#     print('Finished going through the pages.')
#     return chapters


# def manga_download(md_model: MDownloader) -> None:
#     """Download manga."""
#     manga_id = md_model.manga_id
#     download_type = md_model.download_type

#     cache_json = md_model.cache.load_cache(manga_id)
#     refresh_cache = md_model.cache.check_cache_time(cache_json)
#     manga_data = cache_json.get('data', {})

#     if md_model.manga_data and md_model.args.search_manga:
#         manga_data = md_model.manga_data
#         md_model.cache.save_cache(datetime.now(), manga_id, data=manga_data)

#     if refresh_cache or not manga_data:
#         manga_data = md_model.api.get_manga_data(download_type)
#         md_model.cache.save_cache(datetime.now(), manga_id, data=manga_data)
#         md_model.wait()

#     md_model.manga_data = manga_data
#     title = md_model.formatter.format_title(manga_data)
#     # Initalise json classes and make series folders
#     title_json = TitleJson(md_model)
#     md_model.title_json = title_json

#     if md_model.type_id == 1:
#         chapters_data = title_json.downloaded_ids
#         chapters = cache_json.get("chapters", [])

#         if not chapters:
#             # Call the api and filter out languages other than the selected
#             md_model.params = {"order[chapter]": "desc", "order[volume]": "desc"}
#             url = f'{md_model.manga_api_url}/{md_model.id}'
#             chapters = get_chapters(md_model, url)
#             md_model.cache.save_cache(datetime.now(), manga_id, data=manga_data, chapters=chapters)
#             md_model.wait()

#         md_model.chapters_data = chapters
#         md_model.chapter_prefix_dict = md_model.title_misc.get_prefixes(chapters)
#     else:
#         chapters = md_model.chapters_data[manga_id]["chapters"]
#         chapters_data = md_model.bulk_json.downloaded_ids
#         download_type = f'{download_type}-manga'

#     chapters = md_model.filter.filter_chapters(chapters)
#     md_model.misc.download_message(0, download_type, title)

#     if md_model.args.range_download and md_model.type_id == 1:
#         chapters = md_model.title_misc.download_range_chapters(chapters)

#     download_chapters(md_model, chapters, chapters_data)
#     md_model.misc.download_message(1, download_type, title)

#     # Save the json and covers if selected
#     title_json.core(1)


# def bulk_download(md_model: MDownloader) -> None:
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


# def follows_download(md_model: MDownloader) -> None:
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



async def chapter_download(args: 'ProcessArgs', chapter_args_obj: 'MDArgs') -> None:
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
    await ImageDownloader(args, chapter_response.manga).chapter_downloader(chapter_args_obj)

    # md_model.misc.download_message(1, download_type, name)
