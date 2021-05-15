#!/usr/bin/python3
import re
import math
from typing import Match, Pattern, Type, Union

from .model import ImpVar
from .chapter_downloader import chapterDownloader
from .errors import MDownloaderError, NoChaptersError
from .jsonmaker import AccountJson, TitleJson
from .languages import getLangMD

domain = ImpVar.MANGADEX_API_URL


def checkForChapters(data: dict, md_model) -> int:
    """Check if there are any chapters.

    Args:
        data (dict): Manga or group or user or list data.
        md_model (MDownloader): The base class this program runs on.

    Raises:
        NoChaptersError: No chapters were found.

    Returns:
        int: The amount of chapters found.
    """
    count = data["total"]
    download_id = md_model.id

    if md_model.type_id == 1:
        download_type = 'manga'
        name = md_model.manga_data["data"]["attributes"]["title"]["en"]
    else:
        download_type = md_model.download_type
        name = md_model.name        

    if count == 0:
        raise NoChaptersError(f'{download_type.title()}: {download_id} - {name} has no chapters. Possibly because of the language chosen.')
    return count


def getChapters(md_model, limit: int=500, **params: dict) -> list:
    """Go through each page in the api to get all the chapters.

    Args:
        md_model (MDownloader): The base class this program runs on.
        limit (int, optional): How many chapters to view on one page. Defaults to 500.

    Returns:
        list: A list of all the chapters by the chosen method of download.
    """
    chapters = []
    limit = limit
    offset = 0
    pages = 1
    iteration = 1

    if params:
        parameters = params
    else:
        parameters = {}

    while True:
        # Update the parameters with the new offset
        parameters.update({
            "limit": limit,
            "offset": offset,
        })

        # Call the api and get the json data
        chapters_response = md_model.requestData(md_model.id, md_model.download_type, 1, **parameters)
        data = md_model.convertJson(md_model.id, f'{md_model.download_type}-chapters', chapters_response)

        # Finds how many pages needed to be called
        if pages == 1:
            chapters_count = checkForChapters(data, md_model)
            if chapters_count > limit:
                pages = math.ceil(chapters_count / limit)

            print(f"{pages} pages to go through.")

        chapters.extend(data["results"])
        offset += limit

        # Wait every 5 pages
        if iteration % 5 == 0:
            md_model.waitingTime(3, print_message=False)

        # End the loop when all the pages have been gone through
        if iteration == pages:
            break

        iteration += 1
    
    return chapters


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


def getJsonData(json_data: Type[Union[TitleJson, AccountJson]]) -> list:
    """Check if a data json exists and return the ids saved.

    Args:
        json_data (Type[Union[TitleJson, AccountJson]]): If the json to look through is a title one or account one.

    Returns:
        list: A list containing all the ids stored if possible, otherwise return empty.
    """
    if json_data.data_json:
        chapters_data = json_data.data_json["chapters"]
        return [c["id"] for c in chapters_data]
    else:
        return []


def natsort(x) -> Union[int, float]:
    """Sort the chapter numbers naturally."""
    try:
        return float(x)
    except ValueError:
        return 0


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
    chapters_list.sort(key=natsort)

    print(f'Available chapters:\n{", ".join(chapters_list)}')

    remove_chapters = []

    chap_list = input("\nEnter the chapter(s) to download: ").strip()
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


def loopChapters(md_model, chapters: list, chapters_data: list) -> None:
    """Loop chapters and call the chapterDownloader function.

    Args:
        md_model (MDownloader): The base class this program runs on.
        chapters (list): The chapters to download.
        chapters_data (list): The ids of the downloaded chapters from the data json.
    """
    for chapter in chapters:
        chapter_id = chapter["data"]["id"]
        md_model.chapter_id = chapter_id
        if md_model.type_id in (2, 3):
            md_model.chapter_data = chapter

        try:
            if chapter_id not in chapters_data:
                chapterDownloader(md_model)
        except MDownloaderError as e:
            if e: print(e)
        finally:
            md_model.waitingTime(1)


def titleDownloader(md_model) -> None:
    """Download titles.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    download_type = md_model.download_type

    if md_model.download_type == 'manga':
        md_model.type_id = 1
        manga_response = md_model.requestData(md_model.id, download_type)
        manga_data = md_model.convertJson(md_model.id, download_type, manga_response)
        md_model.manga_data = manga_data
        md_model.manga_id = md_model.id

        # Call the api and filter out languages other than the selected
        chapters = getChapters(md_model, **{"locales[]": md_model.language, "order[chapter]": "desc"})

        md_model.chapters_data = chapters
        # chapters = filterChapters(data["results"], md_model.language)
        md_model.chapter_prefix_dict = getPrefixes(chapters)

    else:
        chapters = md_model.chapters_data[md_model.manga_id]["chapters"]
        manga_data = md_model.manga_data
        download_type = 'manga'

    # Remove illegal symbols from the series name
    title = md_model.formatTitle(manga_data)

    downloadMessage(0, download_type, title)

    if md_model.range_download:
        chapters = rangeChapters(chapters)

    # Initalise json classes and make series folders
    title_json = TitleJson(md_model)
    md_model.title_json = title_json
    chapters_data = getJsonData(title_json)
    md_model.title_json_data = chapters_data

    loopChapters(md_model, chapters, chapters_data)

    downloadMessage(1, download_type, title)

    # Save the json and covers if selected
    title_json.core(1)


def groupUserListDownloader(md_model) -> None:
    """Download group, user and list chapters.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    download_type = md_model.download_type
    md_model.type_id = 2
    limit = 100

    response = md_model.requestData(md_model.id, download_type)
    data = md_model.convertJson(md_model.id, download_type, response)
    md_model.group_user_list_data = data

    # Get the name of the group, user or the custom list's owner
    if download_type == 'group':
        name = data["data"]["attributes"]["name"]
        params = {"groups[]": md_model.id}
    elif download_type == 'list':
        owner = data["data"]["attributes"]["owner"]["attributes"]["username"]
        name = f"{owner}'s Custom List"
        params = {}
        limit = 500
    else:
        name = data["data"]["attributes"]["username"]
        params = {"uploader": md_model.id}

    # Order the chapters descending by the order they're released to read
    params.update({"order[createdAt]": "desc"})

    md_model.name = name
    chapters = getChapters(md_model, limit, **params)
    md_model.chapters_data = chapters

    downloadMessage(0, download_type, name)

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
            manga_response = md_model.requestData(manga_id, 'manga')
            manga_data = md_model.convertJson(manga_id, 'account-manga', manga_response)

            titles[manga_id] = {"mangaId": manga_id, "mangaData": manga_data, "chapters": [chapter]}

            md_model.waitingTime(1)

    md_model.chapters_data = titles

    for title in titles:
        md_model.type_id = 3
        md_model.manga_id = titles[title]["mangaId"]
        md_model.manga_data = titles[title]["mangaData"]
        titleDownloader(md_model)
        md_model.type_id = 2
        # loopChapters(md_model, titles[title]["chapters"], chapters_data)

    downloadMessage(1, download_type, name)

    # Save the json
    account_json.core(1)


def rssDownloader(md_model) -> None:
    """Download rss feeds.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """

    print("RSS isn't supported by MangaDex at this time.")
    return

    response = md_model.requestData(md_model, **{})
    md_model.checkForError(md_model.id, response)
    data = response.content.decode()
    chapters = []

    # Find the chapter links and remove everything other than the ids and language
    items = re.findall(r'<item>.+</item>', data, re.DOTALL)
    for i in items:
        links = i.split("<item>")
        for l in links:
            tags = re.findall(r'<.+>.+<\/.+>', l, re.DOTALL)
            for t in tags:
                temp_dict = {}
                temp_dict["id"] = rssItemFetcher(t, 'link', r'.+\/(\d+)')

                lang_name = rssItemFetcher(t, 'description', r'.+Language:\s(.+)')
                lang_id = getLangMD(lang_name)
                temp_dict["language"] = lang_id

                chapters.append(temp_dict)

    md_model.data = {"chapters": chapters}
    chapters = filterChapters(chapters, md_model.language)
    downloadMessage(0, 'rss', 'This will only download chapters of the language selected, default: English.')

    for chapter in chapters:
        md_model.id = chapter["id"]
        try:
            chapterDownloader(md_model)
        except MDownloaderError as e:
            if e: print(e)
    
    downloadMessage(1, 'rss', 'MangaDex')
