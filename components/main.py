#!/usr/bin/python3
from components.errors import MDownloaderError
import os
import re
import shutil

from .bulk_downloader import titleDownloader, groupUserDownloader, rssDownloader
from .chapter_downloader import chapterDownloader
from .constants import MDownloader, ImpVar


# Check if the url given is a MangaDex one
def urlMatch(url):
    if ImpVar.MD_URL.match(url) or ImpVar.MD_IMAGE_URL.match(url) or ImpVar.MD_RSS_URL.match(url):
        return True
    else:
        return False


# Call the different functions depending on the type of download
def typeChecker(md_model):

    if md_model.download_type in ('title', 'manga'):
        titleDownloader(md_model)
    elif md_model.download_type in ('group', 'user'):
        groupUserDownloader(md_model)
    elif md_model.download_type == 'chapter':
        chapterDownloader(md_model)
    elif md_model.download_type == 'rss':
        rssDownloader(md_model)
    else:
        print('Please enter a title/chapter/group/user download_id. For non-title downloads, you must add the argument "--type [chapter|user|group]".')
    return


def fileDownloader(md_model):

    #Open file and read lines
    with open(md_model.id, 'r') as bulk_file:
        links = [line.rstrip('\n') for line in bulk_file]

    if not links:
        print('Empty file!')
        return

    links = [line for line in links if len(line) > 0 and (urlMatch(line) or line.isdigit())]
    
    if not links:
        print('No MangaDex link or id found')
        return

    print(ImpVar.API_MESSAGE)
    for download_id in links:
        try:
            if not download_id.isdigit():
                md_model.getIdFromUrl(download_id)
            else:
                md_model.id = download_id

            typeChecker(md_model)
        except MDownloaderError as e:
            if e: print(e)

    print(f'All the ids in {md_model.id} have been downloaded')
    return


def main(args):
    md_model = MDownloader()
    md_model.formatArgs(args)
    series_id = args.id
    # md_model.login()  

    # Check the id is valid number
    if not series_id.isdigit():
        # If id is a valid file, use that to download
        if os.path.exists(series_id):
            fileDownloader(md_model)
        # If the id is a url, check if it's a MangaDex url to download
        elif ImpVar.URL_RE.search(series_id):
            if urlMatch(series_id):
                print(ImpVar.API_MESSAGE)
                typeChecker(md_model)
            else:
                print('Please use a MangaDex title/chapter/group/user link.')
                return
        else:
            print('File not found!')
            return
    # Use the id and download_type argument to download
    else:
        print(ImpVar.API_MESSAGE)
        typeChecker(md_model)
    return
