#!/usr/bin/python3
import math
from datetime import datetime
from typing import Type, Union

from .image_downloader import chapter_downloader
from .errors import MDownloaderError, NotLoggedInError
from .jsonmaker import BulkJson, TitleJson
from .model import MDownloader


def download_chapters(md_model: MDownloader, chapters: list, chapters_data: list) -> None:
    """Loop chapters and call the baseDownloader function.

    Args:
        md_model (MDownloader): The base class this program runs on.
        chapters (list): The chapters to download.
        chapters_data (list): The ids of the downloaded chapters from the data json.
    """
    for chapter in chapters:
        chapter_id = chapter["data"]["id"]
        md_model.chapter_id = chapter_id
        md_model.chapter_data = chapter        

        try:
            if chapter_id not in chapters_data:
                chapter_downloader(md_model)
                md_model.wait()
        except MDownloaderError as e:
            if e: print(e)


def json_ids(md_model: MDownloader, json_data: Type[Union[TitleJson, BulkJson]]) -> list:
    """Check if a data json exists and return the ids saved.

    Args:
        md_model (MDownloader): The base class this program runs on.
        json_data (Type[Union[TitleJson, BulkJson]]): If the json to look through is a title one or account one.

    Returns:
        list: A list containing all the ids stored if possible, otherwise return empty.
    """
    ids = []

    if json_data.data_json and not md_model.force_refresh:
        chapters_data = json_data.data_json.get("chapters", [])
        if chapters_data:
            ids = [c["data"]["id"] for c in chapters_data]

    return ids


def get_chapters(md_model: MDownloader, url: str) -> list:
    """Go through each page in the api to get all the chapters.

    Args:
        md_model (MDownloader): The base class this program runs on.
        url (str): Request url.

    Returns:
        list: A list of all the chapters by the chosen method of download.
    """
    chapters = []
    limit = md_model.chapter_limit
    offset = 0
    pages = 1
    iteration = 1

    parameters = {"includes[]": "scanlation_group"}
    parameters.update(md_model.params)

    while True:
        # Update the parameters with the new offset
        parameters.update({
            "limit": limit,
            "offset": offset
        })

        # Call the api and get the json data
        chapters_response = md_model.api.request_data(url, 1, **parameters)
        data = md_model.api.convert_to_json(md_model.id, f'{md_model.download_type}-chapters', chapters_response)

        chapters.extend(data["results"])
        offset += limit

        if md_model.type_id == 3:
            print('Downloading only the first page of the follows.')
            break

        # Finds how many pages needed to be called
        if pages == 1:
            chapters_count = md_model.misc.check_for_chapters(data)
            if chapters_count > limit:
                pages = math.ceil(chapters_count / limit)

            if chapters_count >= 10000:
                print('Due to api limits, a maximum of 10000 chapters can be downloaded.')

            print(f"{pages} page(s) to go through.")

        # Wait every 5 pages
        if iteration % 5 == 0:
            md_model.wait(3)

        # End the loop when all the pages have been gone through
        # Offset 10000 is the highest you can go, any higher returns an error
        if iteration == pages or offset == 10000:
            break

        iteration += 1
        md_model.wait(0)

    print('Finished going through the pages.')
    return chapters


def manga_download(md_model: MDownloader) -> None:
    """Download manga.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    manga_id = md_model.manga_id
    download_type = md_model.download_type

    cache_json = md_model.cache.load_cache(manga_id)
    refresh_cache = md_model.cache.check_cache_time(cache_json)
    manga_data = cache_json.get('data', {})
    relationships = manga_data.get('relationships', [])

    if md_model.manga_data and md_model.args.search_manga:
        manga_data = md_model.manga_data
        md_model.cache.save_cache(datetime.now(), manga_id, data=manga_data)

    if refresh_cache or not manga_data or not relationships:
        manga_data = md_model.api.get_manga_data(download_type)
        md_model.cache.save_cache(datetime.now(), manga_id, data=manga_data)
        md_model.wait()        

    md_model.manga_data = manga_data
    title = md_model.formatter.format_title(manga_data)
    # Initalise json classes and make series folders
    title_json = TitleJson(md_model)
    md_model.title_json = title_json

    if md_model.type_id == 1:
        chapters_data = json_ids(md_model, title_json)
        md_model.title_json_data = chapters_data
        chapters = cache_json.get("chapters", [])

        if not chapters:
            # Call the api and filter out languages other than the selected
            md_model.params = {"translatedLanguage[]": md_model.args.language, "order[chapter]": "desc", "order[volume]": "desc"}
            url = f'{md_model.manga_api_url}/{md_model.id}'
            chapters = get_chapters(md_model, url)
            md_model.cache.save_cache(datetime.now(), manga_id, data=manga_data, chapters=chapters)
            md_model.wait()

        md_model.chapters_data = chapters
        md_model.chapter_prefix_dict = md_model.title_misc.get_prefixes(chapters)
    else:
        chapters = md_model.chapters_data[manga_id]["chapters"]
        chapters_data = md_model.bulk_json_data
        download_type = f'{download_type}-manga'

    if md_model.filter.group_whitelist or md_model.filter.user_whitelist:
        if md_model.filter.group_whitelist:
            chapters = [c for c in chapters if [g["id"] for g in c["relationships"] if g["type"] == 'scanlation_group'] in md_model.filter.group_whitelist]
        else:
            if md_model.filter.user_whitelist:
                chapters = [c for c in chapters if [u["id"] for u in c["relationships"] if u["type"] == 'user'] in md_model.filter.user_whitelist]
    else:
        chapters = [c for c in chapters if 
            (([g["id"] for g in c["relationships"] if g["type"] == 'scanlation_group'] not in md_model.filter.group_blacklist) 
                or [u["id"] for u in c["relationships"] if u["type"] == 'user'] not in md_model.filter.user_blacklist)]

    md_model.misc.download_message(0, download_type, title)

    if md_model.args.range_download and md_model.type_id == 1:
        chapters = md_model.title_misc.download_range_chapters(chapters)

    download_chapters(md_model, chapters, chapters_data)
    md_model.misc.download_message(1, download_type, title)

    # Save the json and covers if selected
    title_json.core(1)


def bulk_download(md_model: MDownloader) -> None:
    """Download group, user and list chapters.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    download_type = md_model.download_type

    if md_model.type_id == 2:
        cache_json = md_model.cache.load_cache(md_model.id)
        refresh_cache = md_model.cache.check_cache_time(cache_json)
        data = cache_json.get('data', {})
        relationships = data.get('relationships', [])

        if refresh_cache or not data or not relationships:
            response = md_model.api.request_data(f'{md_model.api_url}/{md_model.download_type}/{md_model.id}')
            data = md_model.api.convert_to_json(md_model.id, download_type, response)

            md_model.cache.save_cache(datetime.now(), download_id=md_model.id, data=data)
            md_model.wait()

        # Order the chapters descending by the order they're released to read
        md_model.params.update({"order[createdAt]": "desc"})
        md_model.data = data
        download_id = md_model.id
        url = f'{md_model.api_url}/{download_type}/{md_model.id}'
    else:
        download_id = f'{md_model.id}-follows'
        url = f'{md_model.user_api_url}/follows/manga'
        cache_json = md_model.cache_json

    name_path = md_model.data["data"]["attributes"]

    if download_type == 'group':
        md_model.name = name_path["name"]
        md_model.params.update({"groups[]": md_model.id})
        md_model.chapter_limit = 100
    elif download_type == 'user':
        md_model.name = name_path["username"]
        md_model.params.update({"uploader": md_model.id})
        md_model.chapter_limit = 100
    elif download_type == 'list':
        owner = name_path["owner"]["attributes"]["username"]
        md_model.name = f"{owner}'s Custom List"
    else:
        owner = name_path["username"]
        md_model.name = f"{owner}'s Follows List"

    md_model.misc.download_message(0, download_type, md_model.name)
    chapters = cache_json.get('chapters', [])

    if not chapters:
        chapters = get_chapters(md_model, url)
        md_model.cache.save_cache(datetime.now(), download_id, md_model.data, chapters)
        md_model.wait()

    # Initalise json classes and make series folders
    bulk_json = BulkJson(md_model)
    md_model.bulk_json = bulk_json
    md_model.bulk_json_data = json_ids(md_model, bulk_json)

    print(f"Getting each manga's data from the {download_type} chosen.")

    titles = {}
    for chapter in chapters:
        manga_id = [c["id"] for c in chapter["relationships"] if c["type"] == 'manga'][0]
        if manga_id in titles:
            titles[manga_id]["chapters"].append(chapter)
        else:
            titles[manga_id] = {"mangaId": manga_id, "chapters": [chapter]}

    md_model.chapters_data = titles

    print("Finished getting each manga's data, downloading the chapters.")

    for title in titles:
        md_model.manga_download = True
        md_model.manga_id = titles[title]["mangaId"]

        manga_download(md_model)

        md_model.manga_download = False
        md_model.manga_data = {}
        md_model.wait(0)

    md_model.misc.download_message(1, download_type, md_model.name)

    # Save the json
    bulk_json.core(1)


def follows_download(md_model: MDownloader) -> None:
    """Download logged in user follows.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    if not md_model.auth.successful_login:
        raise NotLoggedInError('You need to be logged in to download your follows.')

    download_type = md_model.download_type
    response = md_model.api.request_data(f'{md_model.user_api_url}/me', **{"order[createdAt]": "desc"})
    data = md_model.api.convert_to_json('User', download_type, response)
    md_model.wait()

    user_id = data["data"]["id"]
    md_model.id = user_id
    md_model.data = data
    md_model.cache_json = {"cache_date": datetime.now(), "data": data, "chapters": [], "covers": []}

    bulk_download(md_model)


def chapter_download(md_model: MDownloader) -> None:
    """Get the chapter data for download.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    # Connect to API and get chapter info
    chapter_id = md_model.chapter_id
    download_type = md_model.download_type

    cache_json = md_model.cache.load_cache(md_model.id)
    refresh_cache = md_model.cache.check_cache_time(cache_json)
    chapter_data = cache_json.get('data', {})

    if refresh_cache or not chapter_data:
        response = md_model.api.request_data(f'{md_model.chapter_api_url}/{chapter_id}', **{"includes[]": ["manga", "scanlation_group"]})
        chapter_data = md_model.api.convert_to_json(chapter_id, download_type, response)

        # Make sure only downloadable chapters are downloaded
        if chapter_data["result"] not in ('ok'):
            return

        md_model.cache.save_cache(datetime.now(), chapter_id, data=chapter_data)
        manga_data = md_model.misc.check_manga_data(chapter_data)
    else:
        manga_data = md_model.misc.check_manga_data(chapter_data)

    md_model.formatter.format_title(manga_data)
    md_model.chapter_data = chapter_data
    name = f'{md_model.title}: Chapter {chapter_data["data"]["attributes"]["chapter"]}'

    md_model.misc.download_message(0, download_type, name)

    chapter_downloader(md_model)

    md_model.misc.download_message(1, download_type, name)
