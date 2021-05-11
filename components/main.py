#!/usr/bin/python3
from .errors import MDownloaderError
import os
import re

from .bulk_downloader import titleDownloader, groupUserListDownloader, rssDownloader
from .chapter_downloader import chapterDownloader
from .constants import ImpVar
from .legacy import getIdType, idFromLegacy, legacyMap
from .model import MDownloader


# Check if the url given is a MangaDex one
def urlMatch(url):
    return bool(ImpVar.MD_URL.match(url) or ImpVar.MD_IMAGE_URL.match(url) or ImpVar.MD_RSS_URL.match(url))


def checkForLinks(links, message):
    if not links:
        raise MDownloaderError(message)


def checkUuid(series_id):
    return bool(re.match(ImpVar.UUID_REGEX, series_id))


# Call the different functions depending on the type of download
def typeChecker(md_model):

    if md_model.download_type in ('title', 'manga'):
        md_model.download_type == 'manga'
        titleDownloader(md_model)
    elif md_model.download_type in ('group', 'user', 'list'):
        groupUserListDownloader(md_model)
    elif md_model.download_type == 'chapter':
        chapterDownloader(md_model)
    elif md_model.download_type == 'rss':
        rssDownloader(md_model)
    else:
        raise MDownloaderError('Please enter a manga/chapter/group/user/list id. For non-manga downloads, you must add the argument "--type [chapter|user|group|list]".')


def fileDownloader(md_model):

    # Open file and read lines
    with open(md_model.id, 'r') as bulk_file:
        links = [line.rstrip('\n') for line in bulk_file]

    checkForLinks(links, 'Empty file!')
    links = [line for line in links if len(line) > 0 and (urlMatch(line) or checkUuid(line) or line.isdigit())]
    checkForLinks(links, 'No MangaDex link or id found')

    legacy_ids = [int(legacy) for legacy in links if legacy.isdigit()]

    if len(legacy_ids) > 1400:
        print("Too many legacy ids to convert, skipping the conversion.")
    else:
        new_ids = legacyMap(md_model, md_model.download_type, legacy_ids)
        if new_ids:
            for link in new_ids:
                old_id = link["old_id"]
                new_id = link["new_id"]
                links[links.index(str(old_id))] = new_id

    print(ImpVar.API_MESSAGE)
    for download_id in links:
        try:
            if download_id.isdigit() or checkUuid(download_id):
                md_model.id = download_id
            else:
                getIdType(md_model)

            typeChecker(md_model)
        except MDownloaderError as e:
            if e: print(e)

    print(f'All the ids in {md_model.id} have been downloaded')


def main(args):
    md_model = MDownloader()
    md_model.formatArgs(args)
    series_id = md_model.id
    # md_model.login()

    # Check the id is valid number
    if not checkUuid(series_id):
        # If id is a valid file, use that to download
        if os.path.exists(series_id):
            fileDownloader(md_model)
        elif series_id.isdigit():
            print(ImpVar.API_MESSAGE)
            idFromLegacy(md_model, series_id)
            typeChecker(md_model)
        # If the id is a url, check if it's a MangaDex url to download
        elif ImpVar.URL_RE.search(series_id):
            if urlMatch(series_id):
                print(ImpVar.API_MESSAGE)
                getIdType(md_model)
                typeChecker(md_model)
            else:
                raise MDownloaderError('Please use a MangaDex manga/chapter/group/user/list link.')
        else:
            raise MDownloaderError('File not found!')
    # Use the id and download_type argument to download
    else:
        print(ImpVar.API_MESSAGE)
        typeChecker(md_model)
