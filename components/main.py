#!/usr/bin/python3
import os
import re
import shutil

from .bulk_downloader import titleDownloader, groupUserDownloader, rssDownloader
from .chapter_downloader import chapterDownloader
from .languages import getLangMD

api_message = 'The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.'
md_url = re.compile(r'(?:https:\/\/)?(?:www.|api.)?(?:mangadex\.(?:org|cc)\/)(?:api\/)?(?:v\d\/)?(title|chapter|manga|group|user)(?:\/)(\d+)')
md_image_url = re.compile(r'(?:https:\/\/)?(?:(?:(?:s\d|www)\.)?(?:mangadex\.(?:org|cc)\/)|.+\.mangadex\.network(?::\d+)?\/)(?:.+)?(?:data\/)([a-f0-9]+)(?:\/)((?:\w+|\d+-\w+)\.(?:jpg|jpeg|png|gif))')
md_rss_url = re.compile(r'(?:https:\/\/)?(?:www.)?(?:mangadex\.(?:org|cc)\/)(rss)(?:\/)([A-Za-z0-9]+)(?:(?:\/)(.+)(?:\/)(\d+))?')
url_re = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')


# Check if the url given is a MangaDex one
def urlMatch(url):
    if md_url.match(url) or md_image_url.match(url) or md_rss_url.match(url):
        return True
    else:
        return False


# Call the different functions depending on the type of download
def typeChecker(
        download_id: str,
        language: str,
        route: str,
        download_type: str,
        save_format: str,
        make_folder: bool,
        covers: bool,
        add_data: bool,
        range_download: bool):
    download_type = download_type.lower()

    if download_type in ('title', 'manga'):
        titleDownloader(download_id, language, route, download_type, save_format, make_folder, add_data, covers, range_download)
    elif download_type in ('group', 'user'):
        groupUserDownloader(download_id, language, route, download_type, save_format, make_folder, add_data)
    elif download_type == 'chapter':
        chapterDownloader(download_id, route, save_format, make_folder, add_data)
    elif download_type == 'rss':
        rssDownloader(download_id, language, route, save_format, make_folder, add_data)
    else:
        print('Please enter a title/chapter/group/user download_id. For non-title downloads, you must add the argument "--type [chapter|user|group]".')
    return


# Get the id and download type from the url
def urlChecker(
        url: str,
        language: str,
        route: str,
        download_type: str,
        save_format: str,
        make_folder: bool,
        covers: bool,
        add_data: bool,
        range_download: bool):

    if md_url.match(url):
        input_url = md_url.match(url)
        download_type = input_url.group(1)
        download_id = input_url.group(2)
    elif md_rss_url.match(url):
        download_id = url
        download_type = 'rss'
    else:
        input_url = md_image_url.match(url)
        download_id = input_url.group(1)
        download_type = 'chapter'

    typeChecker(download_id, language, route, download_type, save_format, make_folder, covers, add_data, range_download)
    return


def fileDownloader(
        filename: str,
        language: str,
        route: str,
        download_type: str,
        save_format: str,
        make_folder: bool,
        covers: bool,
        add_data: bool,
        range_download: bool):

    #Open file and read lines
    with open(filename, 'r') as bulk_file:
        links = [line.rstrip('\n') for line in bulk_file]

    if not links:
        print('Empty file!')
        return

    links = [line for line in links if len(line) > 0 and (urlMatch(line) or line.isdigit())]
    
    if not links:
        print('No MangaDex link or id found')
        return

    # with open(filename, 'w') as bulk_file:
    #     for line in links:
    #         bulk_file.write(line + '\n')
    
    # backup = f'{filename}.bac'
    # shutil.copy(filename, backup)

    print(api_message)
    for download_id in links:
        if not download_id.isdigit():
            urlChecker(download_id, language, route, download_type, save_format, make_folder, covers, add_data, range_download)
        else:
            typeChecker(download_id, language, route, download_type, save_format, make_folder, covers, add_data, range_download)
        
    print(f'All the ids in {filename} have been downloaded')
    return


def main(download_id, language, route, download_type, save_format, make_folder, covers, add_data, range_download):
    #Check the id is valid number
    if not download_id.isdigit():
        # If id is a valid file, use that to download
        if os.path.exists(download_id):
            fileDownloader(download_id, language, route, download_type, save_format, make_folder, covers, add_data, range_download)
        # If the id is a url, check if it's a MangaDex url to download
        elif url_re.search(download_id):
            if urlMatch(download_id):
                print(api_message)
                urlChecker(download_id, language, route, download_type, save_format, make_folder, covers, add_data, range_download)
            else:
                print('Please use a MangaDex title/chapter/group/user link.')
                return
        else:
            print('File not found!')
            return
    # Use the id and download_type argument to download
    else:
        print(api_message)
        typeChecker(download_id, language, route, download_type, save_format, make_folder, covers, add_data, range_download)
    return


def formatArgs(args):

    download_id: str = args.id
    language: str = args.language
    route: str = args.directory
    download_type: str = args.type
    save_format: str = args.save_format
    make_folder: str = args.folder
    covers: str = args.covers
    add_data: str = args.json 
    range_download: str = args.range

    if make_folder == 'yes':
        make_folder = True
    else:
        make_folder = False

    if covers == 'save':
        covers = True
    else:
        covers = False

    if add_data == 'add':
        add_data = True
    else:
        add_data = False

    if range_download == 'range':
        range_download = True
    else:
        range_download = False

    language = getLangMD(language)
    if language is None:
        return

    main(download_id, language, route, download_type, save_format, make_folder, covers, add_data, range_download)    
    return
