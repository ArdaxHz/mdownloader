#!/usr/bin/python3
import sys
import os
import time
import requests
import asyncio
import argparse
import re
import html
import json
import zipfile
import shutil

from aiohttp import ClientSession, ClientError
from tqdm import tqdm

headers = {'User-Agent': 'mDownloader/2.2'}
domain  = 'https://mangadex.org'
re_regrex = re.compile('[\\\\/:*?"<>|]')


def createFolder(folder_name):
    try:
        if not os.path.isdir(folder_name):
            os.makedirs(folder_name)
            return 0
        else:
            return 1
    except OSError:
        sys.exit('Error creating folder')


def createZip(zip_route):
    try:
        if not os.path.isfile(zip_route):
            chapter_zip = zipfile.ZipFile(zip_route, 'w')
            return 0, chapter_zip
        else:
            chapter_zip = zipfile.ZipFile(zip_route, 'a')
            return 1, chapter_zip
    except zipfile.BadZipFile:
        os.remove(zip_route)
        sys.exit('Bad zip file detected, deleting.')


#add images to zip with no folders
def appendZip(chapter_zip, folder, image_name):
    try:
        current_dir = os.getcwd()
        os.chdir(folder)
        chapter_zip.write(image_name, compress_type=zipfile.ZIP_DEFLATED)
        os.chdir(current_dir)        
    except UserWarning:
        print('Error adding images to zip')


#download images
def createImages(response, folder, image_name, chapter_zip):
    with open(f'{folder}/{image_name}', 'wb') as file:
        file.write(response)
    appendZip(chapter_zip, folder, image_name)
    return chapter_zip


def checkImages(response, folder, image_name, chapter_zip, image_data, check_images= 'names'):
    pages = []
    
    for _, _, files in os.walk(folder):
        for filename in files:
            if filename == image_name:
                if check_images == 'data':
                    with open(f'{folder}/{filename}', 'rb') as file:
                        f = file.read() 
                        b = bytearray(f)
                        if b == response:
                            appendZip(chapter_zip, folder, filename)
                            pages.append(filename)
                            continue
                else:
                    appendZip(chapter_zip, folder, filename)
                    pages.append(filename)
                    continue
        break

    #check for missing images
    if image_name not in pages:
        createImages(response, folder, image_name, chapter_zip)
        return image_name, chapter_zip


#extract zip and compare the byte information of the images
def checkZip(response, folder, zip_files, chapter_zip, image_name, check_images= 'names'):
    pages = []

    #checks if image data is the same
    if check_images == 'data':
        for _, _, files in os.walk(zip_files):
            for filename in files:
                if filename == image_name:
                    with open(f'{zip_files}/{filename}', 'rb') as file:
                        f = file.read()
                        b = bytearray(f)
                        if b == response:
                            shutil.copy(f'{zip_files}/{filename}', f'{folder}/{filename}')
                            appendZip(chapter_zip, folder, filename)
                            pages.append(filename)
                    continue
            break
    
    #checks if the images are the same name
    else:
        for i in chapter_zip.namelist():
            if i == image_name:
                pages.append(i)
    
    #folder_exists > 1 - yes
    #folder_exists > 0 - no
    
    if image_name not in pages:
        return 1, image_name
    else:
        return 0, image_name


async def wait_with_progress(coros):
    for f in tqdm(asyncio.as_completed(coros), total=len(coros)):
        try:
            await f
        except Exception as e:
            print(e)


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


async def downloadImages(image, url, language, folder, retry, folder_exists, zip_exists, image_data, groups, title, chapter_zip, zip_files, check_images):

    #try to download it 5 times
    while retry < 5:
        async with ClientSession() as session:
            try:
                async with session.get(url + image) as response:
    
                    assert response.status == 200

                    #compile regex for the image names
                    old_name = re.compile(r'^[a-zA-Z]{1}([0-9]+)(\..*)')
                    new_name = re.compile(r'(^[0-9]+)-.*(\..*)')
                    chapter_no = re.compile(r'([0-9]+)\.([0-9]+)')

                    response = await response.read()

                    if old_name.match(image):
                        pattern = old_name.match(image)
                        page_no = pattern.group(1)
                        extension = pattern.group(2)
                    elif new_name.match(image):
                        pattern = new_name.match(image)
                        page_no = pattern.group(1)
                        extension = pattern.group(2)
                    else:
                        page_no = image_data["page_array"].index(image) + 1
                        page_no = str(page_no)
                        extension = re.match(r'.*(\..*)', image).group(1)

                    if chapter_no.match(image_data["chapter"]):
                        pattern = chapter_no.match(image_data["chapter"])
                        chap_no = pattern.group(1).zfill(3)
                        decimal_no = pattern.group(2)
                        chapter_number = (f'{chap_no}.{decimal_no}')
                    else:
                        chapter_number = image_data["chapter"].zfill(3)

                    volume_no = image_data["volume"]

                    if image_data["lang_code"] == 'gb':                            
                        if image_data["volume"] == '':
                            image_name = f'{title} - c{chapter_number} - p{page_no.zfill(3)} [{groups}]{extension}'
                        else:
                            image_name = f'{title} - c{chapter_number} (v{volume_no.zfill(2)}) - p{page_no.zfill(3)} [{groups}]{extension}'
                    else:
                        if image_data["volume"] == '':
                            image_name = f'{title} [{language}] - c{chapter_number} - p{page_no.zfill(3)} [{groups}]{extension}'
                        else:
                            image_name = f'{title} [{language}] - c{chapter_number} (v{volume_no.zfill(2)}) - p{page_no.zfill(3)} [{groups}]{extension}'
                    
                    #The zip doesn't exist
                    if not zip_exists:
                        #returns true if the folder doesn't exist
                        if not folder_exists:
                            createImages(response, folder, image_name, chapter_zip)
                        elif folder_exists:
                            checkImages(response, folder, image_name, chapter_zip, image_data, check_images)

                    #The zip exists
                    else:
                        check, image_name = checkZip(response, folder, zip_files, chapter_zip, image_name, check_images)

                        #add missing images to zip
                        if check == 1:
                            if not folder_exists:
                                createImages(response, folder, image_name, chapter_zip)
                            if folder_exists:
                                checkImages(response, folder, image_name, chapter_zip, image_data, check_images)
                        else:
                            return {"image": image, "status": "Success"}
                    
                    retry = 5
                    
                    return {"image": image, "status": "Success"}

            except (ClientError, AssertionError, asyncio.TimeoutError):
                await asyncio.sleep(3)

                retry += 1

                if retry == 5:
                    print(f'Could not download image {image} after 5 times.')
                    await asyncio.sleep(1)
                    return {"image": image, "status": "Fail"}


# type 0 -> chapter
# type 1 -> title
def downloadChapter(chapter_id, series_route, route, languages, type, remove_folder, title, check_images, save_format):

    if languages == '':
        #Read languages file
        with open('languages.json', 'r') as json_file:
            languages = json.load(json_file)

        print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

    #Connect to API and get chapter info
    url = f'{domain}/api?id={chapter_id}&type=chapter&saver=0'

    response = requests.get(url, headers = headers)

    if response.status_code != 200:

        #Unavailable chapters
        if response.status_code == 300:
            print("Unavailable Chapter. This could be because the chapter was deleted by the group or you're not allowed to read it.")
        else:
            #Restricted Chapters. Like korean webtoons
            if response.status_code == 451:
                print("Restricted Chapter. You're not allowed to read this chapter.")
            else:
                print(f'Request status error: {response.status_code}')

        return {"error": "There was an error while downloading the chapter", "response_code": response.status_code}
    else:
        image_data = response.json()
        server_url = ''

        #Extenal chapters
        if 'external' == image_data["status"]:

            print('Chapter external to Mangadex. Unable to download.')
            return {"error": "There was an error while downloading the chapter", "response_code": 'Chapter external to Mangadex. Unable to download.'}
        else:

            server_url = image_data["server"]

            url = f'{server_url}{image_data["hash"]}/'

            response = {"url": url}
            response["pages"] = {}
            
            #chapter download
            if type == 0:              
                manga_id = image_data["manga_id"]
                manga_url = f'{domain}/api?id={manga_id}&type=manga'

                manga_data = requests.get(manga_url, headers= headers).json()
                title = re_regrex.sub('_', html.unescape(manga_data['manga']['title']))

                if '.' in title[-3:]:
                    folder_title = re.sub(r'\.', '', title) 
                else:
                    folder_title = title

                series_route = f'{route}/{folder_title}'

            group_keys = filter(lambda s: s.startswith('group_name'), image_data.keys())
            groups     = ', '.join(filter(None, [image_data[x] for x in group_keys]))
            groups     = re_regrex.sub('_', html.unescape(groups))
            
            language = languages[image_data["lang_code"]]
            chapter_no = re.compile(r'([0-9]+)\.([0-9]+)')

            if chapter_no.match(image_data["chapter"]):
                pattern = chapter_no.match(image_data["chapter"])
                chap_no = pattern.group(1).zfill(3)
                decimal_no = pattern.group(2)
                chapter_number = (f'{chap_no}.{decimal_no}')
            else:
                chapter_number = image_data["chapter"].zfill(3)
            
            if image_data["lang_code"] == 'gb':
                if image_data["volume"] == '':
                    folder = f'{title} - c{chapter_number} [{groups}]'
                else:
                    folder = f'{title} - c{chapter_number} (v{image_data["volume"].zfill(2)}) [{groups}]'
            else:
                if image_data["volume"] == '': 
                    folder = f'{title} [{language}] - c{chapter_number} [{groups}]'
                else:
                    folder = f'{title} [{language}] - c{chapter_number} (v{image_data["volume"].zfill(2)}) [{groups}]'

            folder_route  = f'{series_route}/{folder}'
            zip_route = f'{folder_route}.{save_format}'
            zip_files = f'{folder_route}_zip'

            # Check if the folder and zip exist. If it exists, check if images are the same as on mangadex
            folder_exists = createFolder(folder_route)
            zip_exists, chapter_zip = createZip(zip_route)

            if zip_exists:
                if check_images == 'names' or check_images == 'data':
                    zip_exists = 1
                    print('The zip file exists, checking if all the images are downloaded.')
                    if check_images == 'data':
                        chapter_zip.extractall(zip_files)
                        chapter_zip.close()
                        os.remove(zip_route)
                        _, chapter_zip = createZip(zip_route)
                elif check_images == 'skip':
                    print('The zip exists, skipping...')
                    shutil.rmtree(folder_route)
                    return

            if folder_exists:
                if check_images == 'names' or check_images == 'data':
                    folder_exists = 1
                    print('The folder exists, checking if all the images are downloaded.')
                elif check_images == 'skip':
                    print('The folder exists, skipping...')
                    shutil.rmtree(folder_route)
                    return
            elif not folder_exists:
                folder_exists = 0

            print(f'Downloading {title} - Volume {image_data["volume"]} - Chapter {image_data["chapter"]} - Title: {image_data["title"]}')

            # ASYNC FUNCTION
            loop  = asyncio.get_event_loop()
            tasks = []
            
            for image in image_data['page_array']:
                task = asyncio.ensure_future(downloadImages(image, url, language, folder_route, 0, folder_exists, zip_exists, image_data, groups, title, chapter_zip, zip_files, check_images))
                tasks.append(task)

            runner = wait_with_progress(tasks)
            loop.run_until_complete(runner)
            chapter_zip.close()
            
            #removes extracted zip folder
            if os.path.isdir(zip_files):
                shutil.rmtree(zip_files)

            #removes chapter folder
            if remove_folder == 'yes':
                shutil.rmtree(folder_route)

            if type == 1:
                for t in tasks:
                    result = t.result()
                    response['pages'][result['image']] = result['status']

                return response


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
        print(f"{id} doesn't exist. Request status error: {response.status_code}. Skipping...")
        return
        
    data = response.json()

    title = re_regrex.sub('_', html.unescape(data['manga']['title']))

    folder_title = title.rstrip()
    folder_title = folder_title.rstrip('.')
    folder_title = folder_title.rstrip()

    series_route = f'{route}/{folder_title}'

    if data["manga"]["hentai"] == 1:
        series_route = f'{series_route} (H)'

    if 'chapter' not in data:
        print(f'Title {id} - {title} has no chapters. Making json and Skipping...')
        json_data = {"id": id, "title": data['manga']['title'], "language": data["manga"]["lang_name"], "author": data["manga"]["author"], "artist": data["manga"]["artist"], "last_chapter": data["manga"]["last_chapter"], "link": domain + '/manga/' + id, "cover_url": domain + data["manga"]["cover_url"]}
        json_data["links"] = seriesLinks(data)
        json_data["chapters"] = "This title has no chapters."
        
        if not os.path.isdir(series_route):
            os.makedirs(series_route)

        with open(f'{series_route}/{id}_data.json', 'w') as file:
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

            if check_images == 'names' or check_images == 'data':
                
                if 'error' in chapter_response:
                    json_chapter["error"] = chapter_response
                else:
                    json_chapter["images"] = chapter_response

                json_data['chapters'].append(json_chapter)

    if check_images == 'names' or check_images == 'data':

        if not json_data["chapters"]:
            json_data["chapters"] = f'This title has no chapters in {language}.'

        if not os.path.isdir(series_route):
            os.makedirs(series_route)

        with open(f'{series_route}/{id}_data.json', 'w') as file:
            json.dump(json_data, file, indent=4, ensure_ascii=False)


def bulkDownloader(filename, language, route, type, remove_folder, check_images, save_format):

    # Open file and read lines
    with open(filename, 'r') as item:
        titles = [line.rstrip('\n') for line in item]

    if len(titles) == 0 :
        print('Empty file!')
        return
    else:
        #Read languages file
        with open('languages.json', 'r') as json_file:
            languages = json.load(json_file)

        print('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

        for id in titles:              
            
            if type == 'title' or type == 'manga':
                title(id, language, languages, route, 1, remove_folder, check_images, save_format)
                print('Download Complete. Waiting 30 seconds...')
                time.sleep(30) # wait 30 seconds
            else:
                downloadChapter(id, '', route, languages, 0, remove_folder, title, check_images, save_format)
                print('Download Complete. Waiting 5 seconds...')                    
                time.sleep(5) # wait 5 seconds
        
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

    md_url = re.compile(r'https\:\/\/mangadex\.org\/(title|chapter|manga)\/([0-9]+)')

    #Check the id is valid number
    if not id.isdigit():

        if os.path.exists(args.id):
            bulkDownloader(id, language, route, type, remove_folder, check_images, save_format)
        elif md_url.match(id):
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
        elif type == 'chapter' or type == 'chapters':
            downloadChapter(id, '', route, '', 0, remove_folder, title, check_images, save_format)
        else:
            print('Please enter a title/chapter id. For titles, you must add the argument "--type chapter".')
            return


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l', default='gb')
    parser.add_argument('--directory', '-d', default='./downloads')
    parser.add_argument('--type', '-t', default='title') #title or chapter
    parser.add_argument('--remove_folder', '-r', default='yes') #yes or no
    parser.add_argument('--check_images', '-c', default='names') #data or names or skip
    parser.add_argument('--save_format', '-s', default='cbz') #zip or cbz
    parser.add_argument('id')

    args = parser.parse_args()

    main(args.id, args.language, args.directory, args.type, args.remove_folder, args.check_images, args.save_format, '')