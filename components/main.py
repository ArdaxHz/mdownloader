#!/usr/bin/python3
import argparse
from typing import Type
import os

from .downloader import bulk_download, manga_download, follows_download, chapter_download
from .constants import ImpVar
from .errors import MDownloaderError
from .legacy import get_id_type, id_from_legacy, convert_ids
from .model import MDownloader

api_message = ImpVar.API_MESSAGE


def check_type(md_model: MDownloader) -> None:
    """Call the different functions depending on the type of download.

    Raises:
        MDownloaderError: The selected download type is not recognised.
    """
    if md_model.download_type == 'chapter':
        md_model.type_id = 0
        md_model.chapter_id = md_model.id
        chapter_download(md_model)
    elif md_model.download_type in ('title', 'manga'):
        md_model.type_id = 1
        md_model.manga_id = md_model.id
        md_model.download_type = 'manga'
        manga_download(md_model)
    elif md_model.download_type in ('group', 'user', 'list'):
        md_model.type_id = 2
        bulk_download(md_model)
    elif md_model.download_type in ('follows', 'feed'):
        md_model.type_id = 3
        follows_download(md_model)
    else:
        raise MDownloaderError('Please enter a manga/chapter/group/user/list id. For non-manga downloads, you must add the argument "--type [chapter|user|group|list]".')


def file_downloader(md_model: MDownloader) -> None:
    """Download from file."""
    md_model.args.range_download = False
    filename = md_model.id

    # Open file and read lines
    with open(filename, 'r') as bulk_file:
        links = [line.rstrip('\n') for line in bulk_file.readlines()]

    md_model.misc.check_for_links(links, 'Empty file!')
    links = [line for line in links if len(line) > 0 and (md_model.misc.check_url(line) or md_model.misc.check_uuid(line) or line.isdigit())]
    md_model.misc.check_for_links(links, 'No MangaDex link or id found')

    legacy_ids = [int(legacy) for legacy in links if legacy.isdigit()]
    ids_to_convert = [legacy_ids[l:l + 1400] for l in range(0, len(legacy_ids), 1400)]

    for ids in ids_to_convert:
        new_ids = convert_ids(md_model, md_model.download_type, ids)
        if new_ids:
            for link in new_ids:
                old_id = link["old_id"]
                new_id = link["new_id"]
                links[links.index(str(old_id))] = new_id

    md_model.wait()

    print(api_message)
    for download_id in links:
        try:
            if download_id.isdigit() or md_model.misc.check_uuid(download_id):
                md_model.id = download_id
            else:
                get_id_type(md_model)

            check_type(md_model)
        except MDownloaderError as e:
            if e: print(e)

    print(f'All the ids in {filename} have been downloaded')


def main(args: Type[argparse.ArgumentParser.parse_args]) -> None:
    """Initialise the MDownloader class and call the respective functions.

    Args:
        args (argparse.ArgumentParser.parse_args): Command line arguments to parse.

    Raises:
        MDownloaderError: No MangaDex link or id found.
        MDownloaderError: Couldn't find the file to download from.
    """
    md_model = MDownloader()
    md_model.args.format_args(args)
    series_id = md_model.id

    # Check the id is valid number
    if not md_model.misc.check_uuid(series_id):
        # If id is a valid file, use that to download
        if os.path.exists(series_id):
            file_downloader(md_model)
        elif series_id.isdigit():
            print(api_message)
            id_from_legacy(md_model, series_id)
            check_type(md_model)
        # If the id is a url, check if it's a MangaDex url to download
        elif ImpVar.URL_RE.search(series_id):
            if md_model.misc.check_url(series_id):
                print(api_message)
                get_id_type(md_model)
                check_type(md_model)
            else:
                raise MDownloaderError('Please use a MangaDex manga/chapter/group/user/list/follows link.')
        else:
            raise MDownloaderError('File not found!')
    # Use the id and download_type argument to download
    else:
        print(api_message)
        check_type(md_model)
