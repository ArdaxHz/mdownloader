#!/usr/bin/python3
import html
import os
import re
from typing import Type, Union

import requests

from . import constants
from .__version__ import __version__
from .chapter_downloader import chapterDownloader
from .jsonmaker import AccountJson, TitleJson
from .languages import getLangMD

headers = constants.HEADERS
domain = constants.MANGADEX_API_URL
re_regrex = re.compile(constants.REGEX)


# Connect to API and get the data
def getData(form: str, id: str) -> dict:
    params = {'include': 'chapters'}
    url = domain.format(form, id)
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Something went wrong. Error: {response.status_code}. Skipping...")
        return

    data = response.json()
    data = data["data"]
    return data


# Get the amount of chapters
def getChapterCount(form: str, data: dict):
    if form in ('title', 'manga'):
        chapter_count = len(data["chapters"])
    else:
        chapter_count = data["group"]["chapters"] if form == 'group' else data["user"]["uploads"]

    # API displays a maximum of 6000 chapters
    if chapter_count > 6000:
        print(f'Due to API limits, a maximum of 6000 chapters can be downloaded for this {form}.')
    return


# Check if there are any chapters
def checkForChapters(chapters: list, form: str, id: str, name: str):
    if not chapters:
        print(f'{form.title()}: {id} - {name} has no chapters.')
        return


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


def natsort(x):
	try:
		x = float(x)
	except ValueError:
		x = 0
	return x


# Get the chapter id and language from the rss feed
def __rssItemFetcher(t, tag, regex):
    link = re.findall(f'<{tag}>.+<\/{tag}>', t)[0]
    link = link.replace(f'<{tag}>', '').replace(f'</{tag}>', '')
    match = re.match(regex, link).group(1)
    return match


# Filter out the unwanted chapters
def filterChapters(chapters, language):
    chapters = [c for c in chapters if c["language"] == language]

    if not chapters:
        print(f'No chapters found in the selected language, {language}.')
        return
    return chapters


def getPrefixes(chapters: list) -> dict:
    volume_dict = {}
    chapter_prefix_dict = {}
    
    for c in chapters:
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


def rangeChapters(chapters: list) -> list:
    chapters_list = list(set([c["chapter"] for c in chapters]))
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
    chapters = [c for c in chapters if c["chapter"] in chapters_to_download]

    return chapters


def titleDownloader(
        id: Union[int, str],
        language: str,
        route: str,
        form: str,
        save_format: str,
        make_folder: bool,
        add_data: bool,
        covers: bool,
        range_download: bool,
        data: dict={},
        account_json: Type[AccountJson]=None):

    if form in ('title', 'manga'):
        download_type = 1
        data = getData(form, id)
        if data is None:
            return

        check = checkForChapters(data["chapters"], form, id, data["manga"]["title"])
        if check is not None:
            return

        getChapterCount(form, data)
    else:
        download_type = 2

    chapters = filterChapters(data["chapters"], language)
    if chapters is None:
        return

    chapter_prefix_dict = getPrefixes(chapters)

    title = re_regrex.sub('_', html.unescape(data["manga"]["title"]))
    title = title.rstrip()
    title = title.rstrip('.')
    title = title.rstrip()
    series_route = os.path.join(route, title)

    downloadMessage(0, form, title)

    if range_download:
        chapters = rangeChapters(chapters)

    # Initalise json classes and make series folders
    title_json = TitleJson(data, series_route, covers, download_type)

    chapters_data = getJsonData(title_json)

    # Loop chapters
    for chapter in chapters:
        chapter_id = chapter["id"]
        chapter_prefixes = chapter_prefix_dict.get(chapter["mangaId"], {})

        if chapter_id not in chapters_data:
            chapterDownloader(chapter_id, route, save_format, make_folder, add_data, chapter_prefixes, download_type, title, title_json, account_json)

    downloadMessage(1, form, title)

    # Save the json and covers if selected
    title_json.core(1)
    if download_type == 2:
        account_json.core(1)
    del title_json
    return


def groupUserDownloader(
        id: str,
        language: str,
        route: str,
        form: str,
        save_format: str,
        make_folder: bool,
        add_data: bool):

    data = getData(form, id)
    if data is None:
        return

    name = data["group"]["name"] if form == 'group' else data["user"]["username"]
    check = checkForChapters(data["chapters"], form, id, name)
    if check is not None:
        return

    downloadMessage(0, form, name)
    
    # Initalise json classes and make series folders
    account_json = AccountJson(data, route, form)

    # Group the downloads by title
    titles = {}
    for chapter in data["chapters"]:
        if chapter["mangaId"]in titles:
            titles[chapter["mangaId"]]["chapters"].append(chapter)
        else:
            titles[chapter["mangaId"]] = {"manga": {"id": chapter["mangaId"], "title": chapter["mangaTitle"]}, "chapters": []}
            titles[chapter["mangaId"]]["chapters"].append(chapter)

    for title in titles:
        titleDownloader(title, language, route, form, save_format, make_folder, add_data, False, False, titles[title], account_json)

    downloadMessage(1, form, name)

    # Save the json
    account_json.core(1)
    del account_json
    return


# Download rss feeds
def rssDownloader(
        url: str,
        language: str,
        route: str,
        save_format: str,
        make_folder: bool,
        add_data: bool):

    response = requests.get(url)
    if response.status_code != 200:
        print(f'Something went wrong. Error: {response.status_code}.')
        return

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
                temp_dict["id"] = __rssItemFetcher(t, 'link', r'.+\/(\d+)')

                lang_name = __rssItemFetcher(t, 'description', r'.+Language:\s(.+)')
                lang_id = getLangMD(lang_name)
                temp_dict["language"] = lang_id

                chapters.append(temp_dict)

    chapters = filterChapters(chapters, language)
    if chapters is None:
        return

    # links = re.findall(r'<link>.+</link>', data)
    # links = [l.replace('<link>', '').replace('</link>', '') for l in links]
    # chapters = [re.sub(r'.+\/', '', l) for l in links]
    # chapters = [c for c in chapters if len(c) > 0]

    downloadMessage(0, 'rss', "\nRSS feeds are not filtered by language.")

    for chapter in chapters:
        chapter = chapter["id"]
        chapterDownloader(chapter, route, save_format, make_folder, add_data)
    
    downloadMessage(1, 'rss', 'MangaDex')
    return
