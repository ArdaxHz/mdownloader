#!/usr/bin/python3
import json
import os
import re
import shutil
import time
from typing import Optional, Union, Type

from .downloader import chapterDownloader, bulkDownloader

api_message = 'The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.'
md_url = re.compile(r'(?:https:\/\/)?(?:www.)?(?:mangadex\.org\/)(?:api\/)?(?:v\d\/)?(title|chapter|manga|group|user)(?:\/)(\d+)')
md_image_url = re.compile(r'(?:https:\/\/)?(?:(?:(?:s\d|www)\.)?(?:mangadex\.org\/)|.+\.mangadex\.network:\d+\/)(?:.+)?(?:data\/)([a-f0-9]+)(?:\/)((?:\w+|\d+-\w+)\.(?:jpg|jpeg|png|gif))')
url_re = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')


# Call the different functions depending on the type of download
def typeChecker(
        id: Union[int, str],
        language: str,
        route: str,
        type: str,
        save_format: str,
        make_folder: bool,
        covers: bool):
    # pylint: disable=unsubscriptable-object
    type = type.lower()

    if type in ('title', 'manga', 'group', 'user'):
        bulkDownloader(id, language, route, type, save_format, make_folder, covers)
    elif type == 'chapter':
        chapterDownloader(id, route, save_format, make_folder)
    else:
        print('Please enter a title/chapter/group/user id. For non-title downloads, you must add the argument "--type [chapter|user|group]".')
        return
    return


# Get the id and type from the url
def urlChecker(
        url: str,
        language: str,
        route: str,
        type: str,
        save_format: str,
        make_folder: bool,
        covers: bool):

    if md_url.match(url):
        input_url = md_url.match(url)
        type = input_url.group(1)
        id = input_url.group(2)
    else:
        input_url = md_image_url.match(url)
        id = input_url.group(1)
        type = 'chapter'

    typeChecker(id, language, route, type, save_format, make_folder, covers)
    return


def fileDownloader(
        filename: str,
        language: str,
        route: str,
        type: str,
        save_format: str,
        make_folder: bool,
        covers: bool):

    #Open file and read lines
    with open(filename, 'r') as item:
        links = [line.rstrip('\n') for line in item]

    if not links:
        print('Empty file!')
        return

    links = [line for line in links if len(line) > 0 and (md_url.match(line) or md_image_url.match(line) or line.isdigit())]
    
    if not links:
        print('No MangaDex link or id found')
        return

    # with open(filename, 'w') as file:
    #     for line in links:
    #         file.write(line + '\n')
    
    # backup = f'{filename}.bac'
    # shutil.copy(filename, backup)

    print(api_message)
    for id in links:
        if not id.isdigit():
            urlChecker(id, language, route, type, save_format, make_folder, covers)
        else:
            typeChecker(id, language, route, type, save_format, make_folder, covers)
        
    print(f'All the ids in {filename} have been downloaded')
    return


def main(
        id: Union[int, str],
        language: str,
        route: str,
        type: str,
        save_format: str,
        make_folder: str,
        covers: str):
    # pylint: disable=unsubscriptable-object

    #check if valid zip formats
    save_format = save_format.lower()
    if save_format not in ('zip', 'cbz'):
        print('Please either use zip or cbz as the save formats.')
        return

    if make_folder == 'yes':
        make_folder = True
    else:
        make_folder = False

    if covers == 'save':
        covers = True
    else:
        covers = False

    #Check the id is valid number
    if not id.isdigit():
        # If id is a valid file, use that to download
        if os.path.exists(id):
            fileDownloader(id, language, route, type, save_format, make_folder, covers)
        # If the id is a url, check if it's a MangaDex url to download
        elif url_re.search(id):
            if md_url.match(id) or md_image_url.match(id):
                print(api_message)
                urlChecker(id, language, route, type, save_format, make_folder, covers)
            else:
                print('Please use a MangaDex title/chapter/group/user link.')
                return
        else:
            print('File not found!')
            return
    # Use the id and type argument to download
    else:
        print(api_message)
        typeChecker(id, language, route, type, save_format, make_folder, covers)
    return
