#!/usr/bin/python3
import json
import os
import re
import shutil
import time

from .downloader import chapterDownloader, bulkDownloader

api_message = 'The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.'
md_url = re.compile(r'(?:https\:\/\/mangadex\.org\/)(title|chapter|manga|group|user)(?:\/)([0-9]+)')
url_re = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')


# Call the different functions depending on the type of download
def typeChecker(id, language, route, type, save_format, make_folder, covers):
    type = type.lower()

    if type in ('title', 'manga', 'group', 'user'):
        chapterDownloader(id, language, route, type, save_format, make_folder, covers)
    elif type == 'chapter':
        bulkDownloader(id, '', route, 0, save_format, make_folder, '')
    else:
        print('Please enter a title/chapter/group/user id. For non-title downloads, you must add the argument "--type [chapter|user|group]".')
        return
    return


# Get the id and type from the url
def urlChecker(url, language, route, type, save_format, make_folder, covers):

    input_url = md_url.match(url)
    type = input_url.group(1)
    id = input_url.group(2)

    typeChecker(id, language, route, type, save_format, make_folder, covers)
    return


def fileDownloader(filename, language, route, type, save_format, make_folder, covers):

    #Open file and read lines
    with open(filename, 'r') as item:
        titles = [line.rstrip('\n') for line in item]
    
    backup = f'{filename}.bac'
    shutil.copy(filename, backup)

    if len(titles) == 0:
        print('Empty file!')
        return
    else:
        print(api_message)
        for id in titles:
            if not id.isdigit():
                if md_url.match(id):
                    urlChecker(id, language, route, type, save_format, make_folder, covers)
                else:
                    # Remove non-md urls
                    titles.pop(0)
                    with open(filename, 'w') as file:
                        for line in titles:
                            file.write(line + '\n')
            else:
                typeChecker(id, language, route, type, save_format, make_folder, covers)
            
        print(f'All the ids in {filename} have been downloaded')
    return


def main(id, language, route, type, save_format, make_folder, covers):

    #check if valid zip formats
    save_format = save_format.lower()
    if save_format not in ('zip', 'cbz'):
        print('Please either use zip or cbz as the save formats.')
        return

    #Check the id is valid number
    if not id.isdigit():
        # If id is a valid file, use that to download
        if os.path.exists(id):
            fileDownloader(id, language, route, type, save_format, make_folder, covers)
        # If the id is a url, check if it's a MangaDex url to download
        elif url_re.search(id):
            if md_url.match(id):
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
