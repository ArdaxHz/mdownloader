#!/usr/bin/python3
import os
import shutil
import time
import re
import json

from components.chapters import downloadChapter
from components.title import downloadTitle
from components.scraper import Scraper

md_url = re.compile(r'(?:https\:\/\/mangadex\.org\/)(title|chapter|manga|group|user)(?:\/)([0-9]+)')
url_re = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')


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
        #Read languages file
        with open('languages.json', 'r') as json_file:
            languages = json.load(json_file)

        print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

        for id in titles:

            if not id.isdigit():
                
                if md_url.match(id):
                    input_url = md_url.match(id)
                    
                    if input_url.group(1) == 'title' or input_url.group(1) == 'manga':
                        id = input_url.group(2)
                        downloadTitle(id, language, languages, route, 1, make_folder, save_format, covers)
                        print('Download Complete. Waiting 15 seconds...')
                        time.sleep(15) # wait 30 seconds
                    elif input_url.group(1) == 'chapter':
                        id = input_url.group(2)
                        downloadChapter(id, '', route, languages, 0, '', make_folder, save_format, '')
                        print('Download Complete.')
                    elif input_url.group(1) == 'group' or input_url.group(1) == 'user':
                        id = input_url.group(2)
                        type = input_url.group(1)
                        Scraper(id, type, hentai, route, languages, make_folder, save_format).getChapters()
                        print('Download Complete. Waiting 15 seconds...')
                        time.sleep(15) # wait 30 seconds
                else:
                    titles.remove(id)
                    with open(filename, 'w') as file:
                        for line in titles:
                            file.write(line + '\n')

            else:
                if type == 'title' or type == 'manga':
                    downloadTitle(id, language, languages, route, 1, make_folder, save_format, covers)
                    print('Download Complete. Waiting 15 seconds...')
                    time.sleep(15) # wait 30 seconds
                elif type == 'chapter':
                    downloadChapter(id, '', route, languages, 0, '', make_folder, save_format, '')
                    print('Download Complete.')
                elif type == 'group' or type == 'user':
                    Scraper(id, type, hentai, route, languages, make_folder, save_format).getChapters()
                    print('Download Complete. Waiting 15 seconds...')
                    time.sleep(15) # wait 30 seconds
                else:
                    print('Please enter a title/chapter id. For chapters, you must add the argument "--type chapter".')
            
        print(f'All the ids in {filename} have been downloaded')


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
                input_url = md_url.match(id)
                
                if input_url.group(1) == 'title' or input_url.group(1) == 'manga':
                    id = input_url.group(2)
                    downloadTitle(id, language, '', route, 1, make_folder, save_format, covers)
                elif input_url.group(1) == 'chapter':
                    id = input_url.group(2)
                    downloadChapter(id, '', route, '', 0, '', make_folder, save_format, '')
                elif input_url.group(1) == 'group' or input_url.group(1) == 'user':
                    id = input_url.group(2)
                    type = input_url.group(1)
                    Scraper(id, type, hentai, route, '', make_folder, save_format).getChapters()
            else:
                print('Please use a MangaDex title/chapter/group link.')
                return
        else:
            print('File not found!')
            return
    else:
        if type == 'title' or type == 'manga':
            downloadTitle(id, language, '', route, 1, make_folder, save_format, covers)
        elif type == 'chapter':
            downloadChapter(id, '', route, '', 0, '', make_folder, save_format, '')
        elif type == 'group' or type == 'user':
            Scraper(id, type, hentai, route, '', make_folder, save_format).getChapters()
        else:
            print('Please enter a title/chapter id. For chapters, you must add the argument "--type chapter".')
            return