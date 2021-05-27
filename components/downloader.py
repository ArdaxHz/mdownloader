#!/usr/bin/python3
import re
import math
from datetime import datetime
from typing import Match, Pattern, Type, Union

from .image_downloader import baseDownloader
from .errors import MDownloaderError, NoChaptersError
from .jsonmaker import AccountJson, TitleJson
from .languages import getLangMD
from .model import MDownloader


def loopChapters(md_model: MDownloader, chapters: list, chapters_data: list) -> None:
    """Loop chapters and call the baseDownloader function.

    Args:
        md_model (MDownloader): The base class this program runs on.
        chapters (list): The chapters to download.
        chapters_data (list): The ids of the downloaded chapters from the data json.
    """
    for chapter in chapters:
        groups = [g["id"] for g in chapter["relationships"] if g["type"] == 'scanlation_group']
        users = [u["id"] for u in chapter["relationships"] if u["type"] == 'user']

        if md_model.download_type == 'user' or md_model.download_type == 'manga':
            # if any(group for group in groups if group not in md_model.filter.group_whitelist):
            #     continue
            if any(group for group in groups if group in md_model.filter.group_blacklist):
                continue

        if md_model.download_type == 'group' or md_model.download_type == 'manga':
            # if any(user for user in users if user not in md_model.filter.user_whitelist):
            #     continue
            if any(user for user in users if user in md_model.filter.user_blacklist):
                continue

        chapter_id = chapter["data"]["id"]
        md_model.chapter_id = chapter_id
        md_model.chapter_data = chapter        

        try:
            if chapter_id not in chapters_data:
                baseDownloader(md_model)
                md_model.wait()
        except MDownloaderError as e:
            if e: print(e)


def downloadMessage(status: bool, download_type: str, name: str) -> None:
    """Print the download message.

    Args:
        status (bool): If the download has started or ended.
        download_type (str): What type of data is being downloaded, manga, group, user, or list.
        name (str): Name of the chosen download.
    """
    message = 'Downloading'
    if status:
        message = f'Finished {message}'

    print(f'{"-"*69}\n{message} {download_type.title()}: {name}\n{"-"*69}')


def checkForChapters(md_model: MDownloader, data: dict) -> int:
    """Check if there are any chapters.

    Args:
        md_model (MDownloader): The base class this program runs on.
        data (data): The data used to find the amount of chapters.

    Raises:
        NoChaptersError: No chapters were found.

    Returns:
        int: The amount of chapters found.
    """
    download_id = md_model.id

    count = data.get('total', 0)

    if md_model.type_id == 1:
        download_type = 'manga'
        name = md_model.title
    else:
        download_type = md_model.download_type
        name = md_model.name

    if count == 0:
        raise NoChaptersError(f'{download_type.title()}: {download_id} - {name} has no chapters. Possibly because of the language chosen or because there are no uploads.')
    return count


def getChapters(md_model: MDownloader, url: str) -> list:
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

    parameters = md_model.params

    while True:
        # Update the parameters with the new offset
        parameters.update({
            "limit": limit,
            "offset": offset,
        })

        # Call the api and get the json data
        chapters_response = md_model.api.requestData(url, 1, **parameters)
        data = md_model.api.convertJson(md_model.id, f'{md_model.download_type}-chapters', chapters_response)

        chapters.extend(data["results"])

        if md_model.type_id == 3:
            print('Downloading only the first page of the follows.')
            break

        # Finds how many pages needed to be called
        if pages == 1:
            chapters_count = checkForChapters(md_model, data)
            if chapters_count > limit:
                pages = math.ceil(chapters_count / limit)

            print(f"{pages} page(s) to go through.")

        offset += limit

        # Wait every 5 pages
        if iteration % 5 == 0:
            md_model.wait(3)

        # End the loop when all the pages have been gone through
        if iteration == pages:
            break

        iteration += 1
        md_model.wait(0)

    print('Finished going through the pages.')

    return chapters


def getJsonData(json_data: Type[Union[TitleJson, AccountJson]]) -> list:
    """Check if a data json exists and return the ids saved.

    Args:
        json_data (Type[Union[TitleJson, AccountJson]]): If the json to look through is a title one or account one.

    Returns:
        list: A list containing all the ids stored if possible, otherwise return empty.
    """
    if json_data.data_json:
        chapters_data = json_data.data_json["chapters"]
        return [c["data"]["id"] for c in chapters_data]
    return []


def rssItemFetcher(t: str, tag: str, regex: Pattern) -> Match:
    """Get the chapter id and language from the rss feed."""
    link = re.findall(f'<{tag}>.+<\/{tag}>', t)[0]
    link = link.replace(f'<{tag}>', '').replace(f'</{tag}>', '')
    match = re.match(regex, link).group(1)
    return match


def filterChapters(chapters: list, language: str) -> list:
    """Filter out chapters not from the chosen language."""
    chapters = [c for c in chapters if c["data"]["attributes"]["translatedLanguage"] == language]

    if not chapters:
        raise NoChaptersError(f'No chapters found in the selected language, {language}.')
    return chapters


def getPrefixes(chapters: list) -> dict:
    """Assign each volume a prefix, default: c.

    Args:
        chapters (list): List of chapters to find the prefixes of.

    Returns:
        dict: A mapping of the volume number and the prefix to use.
    """
    volume_dict = {}
    chapter_prefix_dict = {}

    # Loop over the chapters and add the chapter numbers to the volume number dict
    for c in chapters:
        c = c["data"]["attributes"]
        volume_no = c["volume"]
        try:
            volume_dict[volume_no].append(c["chapter"])
        except KeyError:
            volume_dict[volume_no] = [c["chapter"]]

    list_volume_dict = list(reversed(list(volume_dict)))
    prefix = 'b'

    # Loop over the volume dict list and
    # check if the current iteration has the same chapter numbers as the volume before and after
    for volume in list_volume_dict:
        next_volume_index = list_volume_dict.index(volume) + 1
        previous_volume_index = list_volume_dict.index(volume) - 1
        result = False

        try:
            next_item = list_volume_dict[next_volume_index]
            result = any(elem in volume_dict[next_item] for elem in volume_dict[volume])
        except (KeyError, IndexError):
            previous_volume = list_volume_dict[previous_volume_index]
            result = any(elem in volume_dict[previous_volume] for elem in volume_dict[volume])

        if volume != '':
            if result:
                temp_json = {}
                temp_json[volume] = chr(ord(prefix) + next_volume_index)
                chapter_prefix_dict.update(temp_json)
            else:
                temp_json = {}
                temp_json[volume] = 'c'
                chapter_prefix_dict.update(temp_json)

    return chapter_prefix_dict


def getChapterRange(chapters_list: list, chap_list: list) -> list:
    """Loop through the lists and get the chapters between the upper and lower bounds.

    Args:
        chapters_list (list): All the chapters in the manga.
        chap_list (list): A list of chapter numberss to download.

    Returns:
        list: The chapter number's to download's data.
    """
    chapters_range = []

    for c in chap_list:
        if "-" in c:
            chapter_range = c.split('-')
            lower_bound = chapter_range[0].strip()
            upper_bound = chapter_range[1].strip()
            try:
                lower_bound_i = chapters_list.index(lower_bound)
            except ValueError:
                print(f'Chapter {lower_bound} does not exist. Skipping {c}.')
                continue
            try:
                upper_bound_i = chapters_list.index(upper_bound)
            except ValueError:
                print(f'Chapter {upper_bound} does not exist. Skipping {c}.')
                continue
            c = chapters_list[lower_bound_i:upper_bound_i+1]
        else:
            try:
                c = [chapters_list[chapters_list.index(c)]]
            except ValueError:
                print(f'Chapter {c} does not exist. Skipping.')
                continue
        chapters_range.extend(c)

    return chapters_range


def rangeChapters(chapters: list) -> list:
    """Check which chapters you want to download.

    Args:
        chapters (list): The chapters to get the chapter numbers.

    Returns:
        list: The list of chapters to download.
    """
    chapters_list = [c["data"]["attributes"]["chapter"] for c in chapters]
    chapters_list = list(set(chapters_list))
    chapters_list.sort()

    print(f'Available chapters:\n{", ".join(chapters_list)}')

    remove_chapters = []

    chap_list = input("\nEnter the chapter(s) to download: ").strip()

    if not chap_list:
        raise MDownloaderError('No chapter(s) chosen.')

    chap_list = [c.strip() for c in chap_list.split(',')]
    chapters_to_remove = [c.strip('!') for c in chap_list if '!' in c]
    [chap_list.remove(c) for c in chap_list if '!' in c]

    # Find which chapters to download
    if 'all' not in chap_list:
        chapters_to_download = getChapterRange(chapters_list, chap_list)
    else:
        chapters_to_download = chapters_list

    # Get the chapters to remove from the download list
    remove_chapters = getChapterRange(chapters_list, chapters_to_remove)

    [chapters_to_download.remove(i) for i in remove_chapters]
    chapters = [c for c in chapters if c["data"]["attributes"]["chapter"] in chapters_to_download]

    return chapters


def getTitleData(md_model: MDownloader, download_type: str) -> dict:
    """Call the manga api for the data.

    Args:
        md_model (MDownloader): The base class this program runs on.
        download_type (str): The type of download calling the manga api.

    Returns:
        dict: The manga's data.
    """
    manga_response = md_model.api.requestData(f'{md_model.manga_api_url}/{md_model.manga_id}')
    return md_model.api.convertJson(md_model.manga_id, download_type, manga_response)


def titleDownloader(md_model: MDownloader) -> None:
    """Download titles.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    download_type = md_model.download_type
    manga_id = md_model.manga_id

    cache_json = md_model.cache.loadCacheData(manga_id)
    refresh_cache = md_model.cache.checkCacheTime(cache_json)
    manga_data = cache_json.get('data', [])

    if refresh_cache or not manga_data:
        manga_data = getTitleData(md_model, download_type)
        md_model.cache.saveCacheData(datetime.now(), manga_id, manga_data)
        md_model.wait()

    md_model.manga_data = manga_data
    title = md_model.formatter.formatTitle(manga_data)
    # Initalise json classes and make series folders
    title_json = TitleJson(md_model)
    md_model.title_json = title_json

    if md_model.download_type == 'manga':
        chapters_data = getJsonData(title_json)
        md_model.title_json_data = chapters_data

        chapters = cache_json.get("chapters", [])

        if not chapters:
            # Call the api and filter out languages other than the selected
            md_model.params = {"translatedLanguage[]": md_model.args.language, "order[chapter]": "desc", "order[volume]": "desc"}
            url = f'{md_model.manga_api_url}/{md_model.id}'
            chapters = getChapters(md_model, url)
            md_model.cache.saveCacheData(datetime.now(), manga_id, manga_data, chapters)
            md_model.wait()

        md_model.chapters_data = chapters
        # chapters = filterChapters(data["results"], md_model.language)
        md_model.chapter_prefix_dict = getPrefixes(chapters)
    else:
        chapters = md_model.chapters_data[manga_id]["chapters"]
        chapters_data = md_model.account_json_data
        download_type = 'manga'

    downloadMessage(0, download_type, title)

    if md_model.args.range_download:
        chapters = rangeChapters(chapters)  

    loopChapters(md_model, chapters, chapters_data)

    downloadMessage(1, download_type, title)

    # Save the json and covers if selected
    title_json.core(1)


def bulkDownloader(md_model: MDownloader) -> None:
    """Download group, user and list chapters.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    download_type = md_model.download_type

    if md_model.type_id == 2:
        cache_json = md_model.cache.loadCacheData(md_model.id)
        refresh_cache = md_model.cache.checkCacheTime(cache_json)
        data = cache_json.get('data', [])

        if refresh_cache or not data:
            response = md_model.api.requestData(f'{md_model.api_url}/{md_model.download_type}/{md_model.id}')
            data = md_model.api.convertJson(md_model.id, download_type, response)

            md_model.cache.saveCacheData(datetime.now(), md_model.id, data)
            md_model.wait()

        # Order the chapters descending by the order they're released to read
        md_model.params.update({"order[createdAt]": "desc"})
        md_model.data = data
        download_id = md_model.id
        url = f'{md_model.api_url}/{md_model.download_type}/{md_model.id}'
    else:
        data = md_model.data
        download_id = f'{md_model.id}-follows'
        url = f'{md_model.user_api_url}/follows/manga'
        cache_json = md_model.cache_json

    if download_type == 'group':
        md_model.name = data["data"]["attributes"]["name"]
        md_model.params = {"groups[]": md_model.id}
        md_model.chapter_limit = 100
    elif download_type == 'user':
        md_model.name = data["data"]["attributes"]["username"]
        md_model.params = {"uploader": md_model.id}
        md_model.chapter_limit = 100
    elif download_type == 'list':
        owner = data["data"]["attributes"]["owner"]["attributes"]["username"]
        md_model.name = f"{owner}'s Custom List"
    else:
        owner = data["data"]["attributes"]["username"]
        md_model.name = f"{owner}'s Follows List"

    name = md_model.name
    downloadMessage(0, download_type, name)
    chapters = cache_json.get('chapters', [])

    if not chapters:
        chapters = getChapters(md_model, url)
        md_model.cache.saveCacheData(datetime.now(), download_id, md_model.data, chapters)
        md_model.wait()

    # Initalise json classes and make series folders
    account_json = AccountJson(md_model)
    md_model.account_json = account_json
    md_model.account_json_data = getJsonData(account_json)

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

        titleDownloader(md_model)

        md_model.manga_download = False

    downloadMessage(1, download_type, name)

    # Save the json
    account_json.core(1)


def followsDownloader(md_model: MDownloader) -> None:
    """Download logged in user follows.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    if not md_model.auth.successful_login:
        raise MDownloaderError('You need to be logged in to download your follows.')

    download_type = md_model.download_type
    response = md_model.api.requestData(f'{md_model.user_api_url}/me')
    data = md_model.api.convertJson('User', download_type, response)
    md_model.wait()

    user_id = data["data"]["id"]
    md_model.id = user_id
    md_model.data = data
    md_model.cache_json = {"cache_date": datetime.now(), "data": data, "chapters": [], "covers": []}

    bulkDownloader(md_model)
    return


def chapterDownloader(md_model: MDownloader) -> None:
    """Get the chapter data for download.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    # Connect to API and get chapter info
    chapter_id = md_model.chapter_id
    download_type = md_model.download_type

    cache_json = md_model.cache.loadCacheData(md_model.id)
    refresh_cache = md_model.cache.checkCacheTime(cache_json)
    data = cache_json.get('chapters', {})
    manga_data = cache_json.get('data', {})

    if refresh_cache or not data or not manga_data:
        response = md_model.api.requestData(f'{md_model.chapter_api_url}/{chapter_id}')
        data = md_model.api.convertJson(chapter_id, download_type, response)

        # Make sure only downloadable chapters are downloaded
        if data["result"] not in ('ok'):
            return

        manga_id = [c["id"] for c in data["relationships"] if c["type"] == 'manga'][0]
        md_model.manga_id = manga_id
        manga_data = getTitleData(md_model, 'chapter-manga')

        md_model.cache.saveCacheData(datetime.now(), chapter_id, manga_data, data)

    md_model.formatter.formatTitle(manga_data)
    md_model.chapter_data = data
    name = f'{md_model.title}: Chapter {data["data"]["attributes"]["chapter"]}'

    downloadMessage(0, download_type, name)

    baseDownloader(md_model)

    downloadMessage(1, download_type, name)
