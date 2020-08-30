#!/usr/bin/python3
import sys
import os
import time
import requests
import argparse
import re
import html
import json

from aiohttp import ClientSession, ClientError
from chapters import downloadChapter

headers = {'User-Agent': 'mDownloader/2.2.9'}
domain  = 'https://mangadex.org'
re_regrex = re.compile('[\\\\/:*?"<>|]')
md_url = re.compile(r'https\:\/\/mangadex\.org\/(title|chapter|manga)\/([0-9]+)')
url_re = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')

start_time = time.time()

def seriesLinks(data):
    json_links = {}
    try:
        if 'al' in data["manga"]["links"]:
            json_links["anilist"] = f'https://anilist.co/manga/{data["manga"]["links"]["al"]}'
        if 'ap' in data["manga"]["links"]:
            json_links["anime_planet"] = f'https://www.anime-planet.com/manga/{data["manga"]["links"]["ap"]}'
        if 'bw' in data["manga"]["links"]:
            if re.match(r'series/[0-9]+', data["manga"]["links"]["bw"]):
                json_links["bookwalker"] = f'https://bookwalker.jp/{data["manga"]["links"]["bw"]}/list'
            else:
                json_links["bookwalker"] = f'https://bookwalker.jp/{data["manga"]["links"]["bw"]}'
        if 'kt' in data["manga"]["links"]:
            json_links["kitsu"] = f'https://kitsu.io/manga/{data["manga"]["links"]["kt"]}'
        if 'mu' in data["manga"]["links"]:
            json_links["manga_updates"] = f'https://www.mangaupdates.com/series.html?id={data["manga"]["links"]["mu"]}'
        if 'nu' in data["manga"]["links"]:
            json_links["novel_updates"] = f'https://www.novelupdates.com/series/{data["manga"]["links"]["nu"]}'
        if 'amz' in data["manga"]["links"]:
            json_links["amazon_jp"] = data["manga"]["links"]["amz"]
        if 'cdj' in data["manga"]["links"]:
            json_links["cd_japan"] = data["manga"]["links"]["cdj"]
        if 'ebj' in data["manga"]["links"]:
            json_links["ebookjapan"] = data["manga"]["links"]["ebj"]
        if 'mal' in data["manga"]["links"]:
            json_links["myanimelist"] = f'https://myanimelist.net/manga/{data["manga"]["links"]["mal"]}'
        if 'raw' in data["manga"]["links"]:
            json_links["raw"] = data["manga"]["links"]["raw"]
        if 'engtl' in data["manga"]["links"]:
            json_links["official_english"] = data["manga"]["links"]["engtl"] 
    except TypeError:
        pass

    return json_links


def title(id, language, languages, route, type, remove_folder, check_images, save_format):

    if languages == '':
        #Read languages file
        with open('languages.json', 'r') as json_file:
            languages = json.load(json_file)

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

    if 'chapter' not in data:
        print(f'Title {id} - {title} has no chapters. Making json and Skipping...')
        json_data = {"id": id, "title": data['manga']['title'], "language": data["manga"]["lang_name"], "author": data["manga"]["author"], "artist": data["manga"]["artist"], "last_chapter": data["manga"]["last_chapter"], "link": domain + '/manga/' + id, "cover_url": domain + data["manga"]["cover_url"]}
        json_data["links"] = seriesLinks(data)
        json_data["chapters"] = "This title has no chapters."
        
        if not os.path.isdir(series_route):
            os.makedirs(series_route)

        with open(os.path.join(series_route, f'{id}_data.json'), 'w') as file:
            json.dump(json_data, file, indent=4, ensure_ascii=False)
        
        return

    print(f'---------------------------------------------------------------------\nDownloading Title: {title}\n---------------------------------------------------------------------')

    json_data = {"id": id, "title": data['manga']['title'], "language": data["manga"]["lang_name"], "author": data["manga"]["author"], "artist": data["manga"]["artist"], "last_chapter": data["manga"]["last_chapter"], "link": domain + '/manga/' + id, "cover_url": domain + data["manga"]["cover_url"]}
    json_data["links"] = seriesLinks(data)
    json_data["chapters"] = []

    # Loop chapters
    for chapter_id in data['chapter']:

        # Only chapters of language selected. Default language: English.
        if data['chapter'][chapter_id]['lang_code'] == language:

            lang_code = data['chapter'][chapter_id]['lang_code']
            chapter        = data['chapter'][chapter_id]
            volume_number  = chapter['volume']
            chapter_number = chapter['chapter']
            chapter_title  = chapter['title']

            # Thanks, Teasday
            group_keys = filter(lambda s: s.startswith('group_name'), chapter.keys())
            groups     = ', '.join(filter(None, [chapter[x] for x in group_keys]))
            groups     = re_regrex.sub('_', html.unescape(groups))

            json_chapter = {"chapter_id": chapter_id, "lang_code": lang_code, "chapter": chapter_number, "volume": volume_number, "title": chapter_title, "groups": groups}
                
            chapter_response = downloadChapter(chapter_id, series_route, route, languages, 1, remove_folder, title, check_images, save_format)

            if check_images != 'skip':
                if 'error' in chapter_response:
                    json_chapter["error"] = chapter_response
                else:
                    json_chapter["images"] = chapter_response

                json_data['chapters'].append(json_chapter)

    if check_images != 'skip':
        if not json_data["chapters"]:
            json_data["chapters"] = f'This title has no chapters in {language}.'

        if not os.path.isdir(series_route):
            os.makedirs(series_route)

        with open(os.path.join(series_route, f'{id}_data.json'), 'w') as file:
            json.dump(json_data, file, indent=4, ensure_ascii=False)

    if languages == '':
        print(f"----The script took {round(time.time() - start_time, 2)} seconds----")


def bulkDownloader(filename, language, route, type, remove_folder, check_images, save_format):

    #Open file and read lines
    with open(filename, 'r') as item:
        titles = [line.rstrip('\n') for line in item]

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
                        title(id, language, languages, route, 1, remove_folder, check_images, save_format)
                        print('Download Complete. Waiting 30 seconds...')
                        time.sleep(30) # wait 30 seconds
                    elif input_url.group(1) == 'chapter':
                        id = input_url.group(2)
                        downloadChapter(id, '', route, languages, 0, remove_folder, title, check_images, save_format)
                        print('Download Complete. Waiting 5 seconds...')
                        time.sleep(5) # wait 5 seconds
                else:
                    pass

            else:
                if type == 'title' or type == 'manga':
                    title(id, language, languages, route, 1, remove_folder, check_images, save_format)
                    print('Download Complete. Waiting 30 seconds...')
                    time.sleep(30) # wait 30 seconds
                else:
                    downloadChapter(id, '', route, languages, 0, remove_folder, title, check_images, save_format)
                    print('Download Complete. Waiting 5 seconds...')
                    # time.sleep(5) # wait 5 seconds
            
        print(f'All the ids in {filename} have been downloaded')


def main(id, language, route, type, remove_folder, check_images, save_format, languages):

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
            bulkDownloader(id, language, route, type, remove_folder, check_images, save_format)        
        elif url_re.search(id):
            if md_url.match(id):
                input_url = md_url.match(id)
                
                if input_url.group(1) == 'title' or input_url.group(1) == 'manga':
                    id = input_url.group(2)
                    title(id, language, '', route, 1, remove_folder, check_images, save_format)
                elif input_url.group(1) == 'chapter':
                    id = input_url.group(2)
                    downloadChapter(id, '', route, '', 0, remove_folder, title, check_images, save_format)
            else:
                print('Please use a MangaDex title/chapter link.')
                return
        else:
            print('File not found!')
            return
    else:
        if type == 'title' or type == 'manga':
            title(id, language, '', route, 1, remove_folder, check_images, save_format)
        elif type == 'chapter':
            downloadChapter(id, '', route, '', 0, remove_folder, title, check_images, save_format)
        else:
            print('Please enter a title/chapter id. For titles, you must add the argument "--type chapter".')
            return


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l', default='gb', help='Specify the language to download. NEEDED for non-English title downloads.')
    parser.add_argument('--directory', '-d', default='./downloads', help='The download location, need to specify full path.')
    parser.add_argument('--type', '-t', default='title', nargs='?', const='chapter', help='Type of id to download, title or chapter.') #title or chapter
    parser.add_argument('--remove_folder', '-r', default='yes', help='Remove the chapter folder that is made after the chapter has been downloaded.') #yes or no
    parser.add_argument('--check_images', '-c', default='names', choices=['names', 'data', 'skip'], help='Check if the chapter folder and/or zip has the same files as the chapter on MangaDex. Read the Readme for more information.') #data or names or skip
    parser.add_argument('--save_format', '-s', default='cbz', help='Choose to download as a zip archive or as a comic archive.') #zip or cbz
    parser.add_argument('id', help='ID to download. Can be chapter, tile, link or file.')

    args = parser.parse_args()

    main(args.id, args.language, args.directory, args.type, args.remove_folder, args.check_images, args.save_format, '')
