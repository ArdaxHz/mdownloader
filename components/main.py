#!/usr/bin/python3
import os
import shutil
import time
import re
import json

from components.downloader import downloadChapter, downloadBatch

api_message = 'The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.'
md_url = re.compile(r'(?:https\:\/\/mangadex\.org\/)(title|chapter|manga|group|user)(?:\/)([0-9]+)')
url_re = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')


def typeChecker(id, language, route, type, make_folder, save_format, covers, hentai):

    if type in ('title', 'manga', 'group', 'user'):
        downloadBatch(id, language, route, type, make_folder, save_format, covers)
    elif type == 'chapter':
        downloadChapter(id, route, 0, '', make_folder, save_format, '')
    else:
        print('Please enter a title/chapter/group/user id. For non-title downloads, you must add the argument "--type [chapter|user|group]".')
        return

    return


def urlChecker(id, language, route, type, make_folder, save_format, covers, hentai):

    input_url = md_url.match(id)
    type = input_url.group(1)

    if type in ('title', 'manga', 'group', 'user'):
        id = input_url.group(2)
        downloadBatch(id, language, route, type, make_folder, save_format, covers)
    elif type == 'chapter':
        id = input_url.group(2)
        downloadChapter(id, route, 0, '', make_folder, save_format, '')

    return


def bulkDownloader(filename, language, route, type, make_folder, save_format, covers, hentai):

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
            # print(id)

            if not id.isdigit():
                
                if md_url.match(id):
                    urlChecker(id, language, route, type, make_folder, save_format, covers, hentai)                   
                    
                    # titles.pop(0)
                    # with open(filename, 'w') as file:
                    #     for line in titles:
                    #         file.write(line + '\n')
                    
                    # print(titles)
                else:
                    titles.pop(0)
                    with open(filename, 'w') as file:
                        for line in titles:
                            file.write(line + '\n')

            else:
                typeChecker(id, language, route, type, make_folder, save_format, covers, hentai)
            
        print(f'All the ids in {filename} have been downloaded')

    return

def main(id, language, route, type, make_folder, save_format, covers, hentai):

    #check if valid zip formats
    if save_format == 'zip':
        save_format = 'zip'
    elif save_format == 'cbz':
        save_format == 'cbz'
    else:
        print('Please either use zip or cbz as the save formats.')
        return

    #Check the id is valid number
    if not id.isdigit():

        if os.path.exists(id):
            bulkDownloader(id, language, route, type, make_folder, save_format, covers, hentai)        
        elif url_re.search(id):
            if md_url.match(id):
                print(api_message)
                urlChecker(id, language, route, type, make_folder, save_format, covers, hentai)
            else:
                print('Please use a MangaDex title/chapter/group/user link.')
                return
        else:
            print('File not found!')
            return
    else:
        print(api_message)
        typeChecker(id, language, route, type, make_folder, save_format, covers, hentai)

    return
