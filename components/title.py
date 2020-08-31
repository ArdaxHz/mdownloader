#!/usr/bin/python3
import sys
import os
import time
import requests
import re
import html
import json

from aiohttp import ClientSession, ClientError
from components.chapters import downloadChapter
from components.jsonmaker import titleJson
from components.__version__ import __version__

headers = {'User-Agent': f'mDownloader/{__version__}'}
domain  = 'https://mangadex.org'
re_regrex = re.compile('[\\\\/:*?"<>|]')


def downloadTitle(id, language, languages, route, type, check_images, save_format):

    if languages == '':
        #Read languages file
        with open('languages.json', 'r') as lang_file:
            languages = json.load(lang_file)

        print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')
    
    #Connect to API and get manga info
    url = f'{domain}/api?id={id}&type=manga'

    response = requests.get(url, headers = headers)

    if response.status_code != 200:
        print(f"Title {id} doesn't exist. Request status error: {response.status_code}. Skipping...")
        return
        
    data = response.json()

    title = re_regrex.sub('_', html.unescape(data['manga']['title']))

    folder_title = title.rstrip()
    folder_title = folder_title.rstrip('.')
    folder_title = folder_title.rstrip()

    series_route = os.path.join(route, folder_title)

    if data["manga"]["hentai"] == 1:
        series_route = f'{series_route} (H)'

    json_file = titleJson(data, id, series_route)

    if 'chapter' not in data:
        print(f'Title {id} - {title} has no chapters. Making json and Skipping...')
        json_file.chapters(None)
        json_file.core()
        return

    print(f'---------------------------------------------------------------------\nDownloading Title: {title}\n---------------------------------------------------------------------')

    # Loop chapters
    for chapter_id in data['chapter']:

        # Only chapters of language selected. Default language: English.
        if data['chapter'][chapter_id]['lang_code'] == language:
                
            downloadChapter(chapter_id, series_route, route, languages, 1, title, check_images, save_format, json_file)
    
    json_file.core()