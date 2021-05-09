#!/usr/bin/python3
from components.errors import MdDownloaderError, NoChaptersError
import html
import os
import re
import math
import time
from typing import Match, Optional, Pattern, Type, Union

from .model import ImpVar
from .__version__ import __version__
from .chapter_downloader import chapterDownloader
from .jsonmaker import AccountJson, TitleJson
from .languages import getLangMD

domain = ImpVar.MANGADEX_API_URL
re_regrex = re.compile(ImpVar.REGEX)


# Check if there are any chapters
def checkForChapters(data: dict, md_model):
    count = data["total"]
    download_id = md_model.id

    if md_model.download_type == 'manga':
        download_type = 'manga'
        name = md_model.data["data"]["attributes"]["title"]["en"]
    else:
        download_type = md_model.download_type
        name = md_model.name        

    if count == 0:
        raise NoChaptersError(f'{download_type.title()}: {download_id} - {name} has no chapters. Possibly because of the language chosen')
    return count


# Go through each page to get the chapters
def getChapters(md_model, limit: int=500, **params):
    chapters = []
    limit = limit
    offset = 0
    pages = 1
    iteration = 1
    time_to_wait = 3

    if params:
        parameters = params
    else:
        parameters = {}

    while True:
        parameters.update({
            "limit": limit,
            "offset": offset,
        })

        chapters_response = md_model.requestData(md_model.id, md_model.download_type, 1, **parameters)
        print(chapters_response.url)
        data = md_model.getData(chapters_response)

        if pages == 1:
            chapters_count = checkForChapters(data, md_model)
            if chapters_count > limit:
                pages = math.ceil(chapters_count / limit)

            print(f"{pages} pages to go through.")

        chapters.extend(data["results"])
        offset += limit

        if iteration % 5 == 0:
            print(f'Waiting {time_to_wait} seconds')
            time.sleep(time_to_wait)

        if iteration == pages:
            break

        iteration += 1
    
    return chapters


# Print the download messages
def downloadMessage(status: bool, form: str, name: str):
    message = 'Downloading'
    if status:
        message = f'Finished {message}'

    print(f'{"-"*69}\n{message} {form.title()}: {name}\n{"-"*69}')
    return


# Check if a json exists
def getJsonData(title_json: Type[TitleJson]) -> list:
    if title_json.data_json:
        chapters_data = title_json.data_json["chapters"]
        return [c["id"] for c in chapters_data]
    else:
        return []


# Sort the chapter numbers naturally
def natsort(x) -> Union[int, float]:
	try:
		x = float(x)
	except ValueError:
		x = 0
	return x


# Get the chapter id and language from the rss feed
def rssItemFetcher(t: str, tag: str, regex: Pattern) -> Match:
    link = re.findall(f'<{tag}>.+<\/{tag}>', t)[0]
    link = link.replace(f'<{tag}>', '').replace(f'</{tag}>', '')
    match = re.match(regex, link).group(1)
    return match


# Filter out the unwanted chapters
def filterChapters(chapters: list, language: str) -> Optional[list]:
    chapters = [c for c in chapters if c["data"]["attributes"]["translatedLanguage"] == language]

    if not chapters:
        print(f'No chapters found in the selected language, {language}.')
        return
    return chapters


# Assign each volume a prefix, default: c
def getPrefixes(chapters: list) -> dict:
    volume_dict = {}
    chapter_prefix_dict = {}
    
    for c in chapters:
        c = c["data"]["attributes"]
        volume_no = c["volume"]
        try:
            volume_dict[volume_no].append(c["chapter"])
        except KeyError:
            volume_dict[volume_no] = [c["chapter"]]

    list_volume_dict = list(reversed(list(volume_dict)))
    prefix = 'b'

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


# Loop through the lists and get the chapters between the upper and lower bounds
def getChapterRange(chapters_list: list, chap_list: list) -> list:
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


# Check which chapters you want to download
def rangeChapters(chapters: list) -> list:
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


# Loop chapters
def loopChapters(md_model, chapters, chapters_data):
    for chapter in chapters:
        chapter_id = chapter["data"]["id"]
        md_model.chapter_id = chapter_id

        try:
            if chapter_id not in chapters_data:
                chapterDownloader(md_model)
        except MdDownloaderError as e:
            if e: print(e)


# Download titles
def titleDownloader(md_model):
    download_type = md_model.download_type
    md_model.type_id = 1
    manga_response = md_model.requestData(md_model.id, download_type)
    manga_data = md_model.getData(manga_response)
    title = manga_data["data"]["attributes"]["title"]["en"]
    md_model.data = manga_data

    chapters = getChapters(md_model, **{"locales[]": md_model.language})

    md_model.chapters_data = chapters
    # chapters = filterChapters(data["results"], md_model.language)
    md_model.chapter_prefix_dict = getPrefixes(chapters)

    title = re_regrex.sub('_', html.unescape(title))
    title = title.rstrip(' .')
    md_model.title = title
    md_model.formatRoute()

    downloadMessage(0, download_type, title)

    if md_model.range_download:
        chapters = rangeChapters(chapters)

    # Initalise json classes and make series folders
    title_json = TitleJson(md_model)
    md_model.title_json = title_json
    chapters_data = getJsonData(title_json)

    loopChapters(md_model, chapters, chapters_data)

    downloadMessage(1, download_type, title)

    # Save the json and covers if selected
    title_json.core(1)
    del title_json
    return


# Download group, user and list chapters
def groupUserListDownloader(md_model):
    download_type = md_model.download_type
    md_model.type_id = 2
    limit = 100

    response = md_model.requestData(md_model.id, download_type)
    data = md_model.getData(response)
    md_model.data = data

    if download_type == 'group':
        name = data["data"]["attributes"]["name"]
        params = {"groups[]": md_model.id}
    elif download_type == 'list':
        owner = data["data"]["attributes"]["owner"]["attributes"]["username"]
        name = f"{owner}'s Custom List"
        limit = 500
    else:
        name = data["data"]["attributes"]["username"]
        params = {"uploader": md_model.id}

    params.update({"order[publishAt]": "desc"})

    md_model.name = name
    chapters = getChapters(md_model, limit, **params)
    md_model.chapters_data = chapters

    downloadMessage(0, download_type, name)

    # Initalise json classes and make series folders
    account_json = AccountJson(md_model)
    md_model.account_json = account_json
    chapters_data = getJsonData(account_json)

    loopChapters(md_model, chapters, chapters_data)

    downloadMessage(1, download_type, name)

    # Save the json
    account_json.core(1)
    del account_json
    return


# Download rss feeds
def rssDownloader(md_model):

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
        except MdDownloaderError as e:
            if e: print(e)
    
    downloadMessage(1, 'rss', 'MangaDex')
    return
