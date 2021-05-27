#!/usr/bin/python3
import argparse
from typing import Type
import os
import re

from .downloader import bulkDownloader, titleDownloader, followsDownloader, chapterDownloader
from .constants import ImpVar
from .errors import MDownloaderError, NoChaptersError
from .legacy import getIdType, idFromLegacy, legacyMap
from .model import MDownloader


def urlMatch(url: str) -> bool:
    """Check if the url given is a MangaDex one.

    Args:
        url (str): The url to check.

    Returns:
        bool: True if the url is a MangaDex one, False if not.
    """
    return bool(ImpVar.MD_URL.match(url) or ImpVar.MD_IMAGE_URL.match(url) or ImpVar.MD_FOLLOWS_URL.match(url))


def checkForLinks(links: list, message: str) -> None:
    """See if the file has any MangaDex urls or ids. 

    Args:
        links (list): Array of urls and ids.
        message (str): The error message.

    Raises:
        NoChaptersError: End the program with the error message.
    """
    if not links:
        raise NoChaptersError(message)


def checkUuid(series_id: str) -> bool:
    """Check if the id is a UUID.

    Args:
        series_id (str): Id to check.

    Returns:
        bool: True if the id is a UUID, False if not.
    """
    return bool(re.match(ImpVar.UUID_REGEX, series_id))


def typeChecker(md_model: MDownloader) -> None:
    """Call the different functions depending on the type of download.

    Args:
        md_model (MDownloader): The base class this program runs on.

    Raises:
        MDownloaderError: The selected download type is not recognised.
    """
    if md_model.download_type == 'chapter':
        md_model.type_id = 0
        md_model.chapter_id = md_model.id
        chapterDownloader(md_model)
    elif md_model.download_type in ('title', 'manga'):
        md_model.type_id = 1
        md_model.manga_id = md_model.id
        md_model.download_type == 'manga'
        titleDownloader(md_model)
    elif md_model.download_type in ('group', 'user', 'list'):
        md_model.type_id = 2
        bulkDownloader(md_model)
    elif md_model.download_type == 'follows':
        md_model.type_id = 3
        followsDownloader(md_model)
    else:
        raise MDownloaderError('Please enter a manga/chapter/group/user/list id. For non-manga downloads, you must add the argument "--type [chapter|user|group|list]".')


def fileDownloader(md_model: MDownloader) -> None:
    """Download from file.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    # Open file and read lines
    with open(md_model.id, 'r') as bulk_file:
        links = [line.rstrip('\n') for line in bulk_file.readlines()]

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

    md_model.wait(2)

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


def main(args: Type[argparse.ArgumentParser.parse_args]) -> None:
    """Initialise the MDownloader class and call the respective functions.

    Args:
        args (argparse.ArgumentParser.parse_args): Command line arguments to parse.

    Raises:
        MDownloaderError: No MangaDex link or id found.
        MDownloaderError: Couldn't find the file to download from.
    """
    md_model = MDownloader()
    md_model.args.formatArgs(args)

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
                raise MDownloaderError('Please use a MangaDex manga/chapter/group/user/list/follows link.')
        else:
            raise MDownloaderError('File not found!')
    # Use the id and download_type argument to download
    else:
        print(ImpVar.API_MESSAGE)
        typeChecker(md_model)
