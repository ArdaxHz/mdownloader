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

headers = { 'User-Agent': 'mDownloader/2.1.2' }
domain  = 'https://mangadex.org'

def createFolder(folder_name):
    try:
        if not os.path.isdir(folder_name):
            os.makedirs(folder_name)
            return 0
        else:
            return 1
    except OSError:
        sys.exit('Error creating folder')

#add images to zip with no folders
def appendZip(chapter_zip, folder, image_name):
    try:
        current_dir = os.getcwd()
        os.chdir(folder)
        chapter_zip.write(image_name, compress_type=zipfile.ZIP_DEFLATED)
        os.chdir(current_dir)        
    except UserWarning:
        print('Error adding images to zip')

def createZip(zip_route):
    try:
        if os.path.isfile(zip_route) == False:
            chapter_zip = zipfile.ZipFile(zip_route, 'w')
            return 0, chapter_zip
        else:
            chapter_zip = zipfile.ZipFile(zip_route, 'a')
            return 1, chapter_zip
    except zipfile.BadZipFile:
        os.remove(zip_route)
        sys.exit('Bad zip file detected, deleting.')

#download images
def createImages(response, folder, image_name, chapter_zip):
    with open( folder + '/' + image_name , 'wb') as file:
        file.write(response)
    appendZip(chapter_zip, folder, image_name)
    return chapter_zip

def checkImages(response, folder, image_name, chapter_zip, image_data, check_images):
    pages = []
    for root, dirs, files in os.walk(folder):
        for filename in files:
            if filename == image_name:
                if check_images == 'yes':
                    with open( folder + '/' + image_name, 'rb') as file:
                        f = file.read()
                        b = bytearray(f)
                        if b == response:
                            appendZip(chapter_zip, folder, image_name)
                            pages.append(image_name)
                            continue
                else:
                    appendZip(chapter_zip, folder, image_name)
                    pages.append(filename)
                    continue
        break

    #check for missing images
    if image_name not in pages:
        createImages(response, folder, image_name, chapter_zip)
        return image_name, chapter_zip

#extract zip and compare the byte information of the images
def checkZip(response, folder, zip_files, chapter_zip, image_name, check_images):
    pages = []

    #checks if image data is the same
    if check_images == 'yes':
        for root, dirs, files in os.walk(zip_files):
            for filename in files:
                if filename == image_name:
                    with open( zip_files + '/' + image_name, 'rb') as file:
                        f = file.read()
                        b = bytearray(f)
                        if b == response:
                            shutil.copy(f'{zip_files}/{filename}', f'{folder}/{filename}')
                            appendZip(chapter_zip, folder, image_name)
                            pages.append(image_name)
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

async def downloadImages(image, url, language, folder, retry, folder_exists, zip_exists, image_data, groups, title, chapter_zip, zip_route, zip_files, check_images):

    #try to download it 3 times
    while( retry < 3 ):
        async with ClientSession() as session:
            try:
                async with session.get( url + image ) as response:
    
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
                            return { "image": image, "status": "Success" }
                    
                    retry = 3
                    
                    return { "image": image, "status": "Success" }

            except (ClientError, AssertionError, asyncio.TimeoutError):
                await asyncio.sleep(1)

                retry += 1

                if( retry == 3 ):
                    print( f'Could not download image {image} after 3 times.' )
                    await asyncio.sleep(1)
                    return { "image": image, "status": "Fail" }

# type 0 -> chapter
# type 1 -> title
def downloadChapter(chapter_id, series_route, route, languages, type, remove, title, check_images):

    # Connect to API and get chapter info
    url = f'{domain}/api?id={chapter_id}&type=chapter&saver=0'

    response = requests.get( url, headers = headers )

    if ( response.status_code != 200 ):

        #Unavailable chapters
        if ( response.status_code == 300 ):
            print ( "Unavailable Chapter. This could be because the chapter was deleted by the group or you're not allowed to read it." )
        else:
            #Restricted Chapters. Like korean webtoons
            if ( response.status_code == 451 ):
                print ( "Restricted Chapter. You're not allowed to read this chapter." )
            else:
                print ( f'Request status error: {response.status_code}' )

        return { "error": "There was an error while downloading the chapter", "response_code": response.status_code }
    else:
        image_data = response.json()
        server_url = ''

        #Extenal chapters
        if( 'external' == image_data["status"] ):

            print ( 'Chapter external to Mangadex. Unable to download.' )
            return { "error": "There was an error while downloading the chapter", "response_code": 'Chapter external to Mangadex. Unable to download.' }
        else:

            server_url = image_data["server"]

            url = f'{server_url}{image_data["hash"]}/'

            response = { "url": url }
            response["images"] = {}
            
            #chapter download
            if type == 0:              
                manga_id = image_data["manga_id"]
                manga_url = f'{domain}/api?id={manga_id}&type=manga'

                manga_data = requests.get( manga_url, headers= headers ).json()
                title = re.sub( r'[\\\\/:*?"<>|]', '_', html.unescape( manga_data['manga']['title'] ) )
                if series_route == '':
                    series_route = f'{route}{title}'
                with open('languages.json', 'r') as json_file:
                    languages = json.load(json_file)

            group_keys = filter(lambda s: s.startswith('group_name'), image_data.keys())
            groups     = ', '.join( filter( None, [image_data[x] for x in group_keys ] ) )
            groups     = re.sub( r'[\\\\/:*?"<>|]', '_', html.unescape( groups ) )
            
            language = languages[image_data["lang_code"]]
            chapter_title = image_data["title"]
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

            chapter_route  = f'{series_route}/{folder}'
            zip_route = f'{series_route}/{folder}.zip'

            # Check if the folder and zip exist. If it exists, check if images are the same as on mangadex
            chapter_exists = createFolder(chapter_route)
            zip_exists, chapter_zip = createZip(zip_route)            

            if (zip_exists):
                zip_exists = 1
                if check_images == 'yes':
                    zip_files = f'{chapter_route}_zip'
                    chapter_zip.extractall(zip_files)
                    chapter_zip.close()
                    os.remove(zip_route)
                    _, chapter_zip = createZip(zip_route)
                else:
                    zip_files = ''
            else:
                zip_files = ''
                if (chapter_exists):
                    chapter_exists = 1
                    print( 'The folder exists, checking if all the files downloaded.' )
                else:
                    chapter_exists = 0

            print ( f'Downloading Volume {image_data["volume"]} Chapter {image_data["chapter"]} Title: {chapter_title}' )

            # ASYNC FUNCTION
            loop  = asyncio.get_event_loop()
            tasks = []
            
            for image in image_data['page_array']:
                task = asyncio.ensure_future( downloadImages(image, url, language, chapter_route, 0, chapter_exists, zip_exists, image_data, groups, title, chapter_zip, zip_route, zip_files, check_images) )
                tasks.append(task)

            runner = wait_with_progress(tasks)
            loop.run_until_complete(runner)
            chapter_zip.close()
            
            #removes extracted zip folder
            if os.path.isdir(zip_files):
                shutil.rmtree(zip_files)

            #removes chapter folder
            if remove == 'yes':
                shutil.rmtree(chapter_route)

            if type == 1:
                for t in tasks:
                    result = t.result()
                    response['images'][ result['image'] ] = result['status']

                return response

def main(id, language, route, type, remove, check_images, languages, re_regrex):

    # Check the id is valid number
    if ( not id.isdigit() ):
        sys.exit('Invalid Title/Chapter ID')

    if( languages == '' ):
        print ('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')
    
    title = ''
    
    if ( 'title' == type ):
        # Connect to API and get manga info
        url = f'{domain}/api?id={id}&type=manga'

        response = requests.get( url, headers = headers)

        if ( response.status_code != 200 ):
            if (languages == ''):
                sys.exit( f'Request status error: {response.status_code}' )
            else:
                print( f'Title {id}. Request status error: {response.status_code}. Skipping...' )
                return

        if( re_regrex == '' ):
            #Compile regrex
            re_regrex = re.compile('[\\\\/:*?"<>|]')
            
        data = response.json()

        title = re_regrex.sub( '_', html.unescape( data['manga']['title'] ) )

        if 'chapter' not in data:
            if (languages == ''):
                sys.exit( f'Title {id} - {title} has no chapters.' )
            else:
                print( f'Title {id} - {title} has no chapters. Skipping...' )
                return

        if( languages == '' ):
            # Read languages file
            with open('languages.json', 'r') as json_file:
                languages = json.load(json_file)

        print( f'---------------------------------------------------------------------\nDownloading Title: {title}\n---------------------------------------------------------------------' )

        json_data = { "id": id, "title": title, "language": data["manga"]["lang_name"], "author": data["manga"]["author"], "artist": data["manga"]["artist"], "last_chapter": data["manga"]["last_chapter"], "link": domain + '/manga/' + id, "cover_url": domain + data["manga"]["cover_url"]}
        json_data["links"] = data["manga"]["links"]
        json_data["chapters"] = {}

        series_route = f'{route}{title}'

        # Loop chapters
        for chapter_id in data['chapter']:

            # Only chapters of language selected. Default language: English.
            if ( data['chapter'][chapter_id]['lang_code'] == language ):

                lang_code = data['chapter'][chapter_id]['lang_code']
                chapter        = data['chapter'][chapter_id]
                volume_number  = chapter['volume']
                chapter_number = chapter['chapter']
                chapter_title  = re_regrex.sub( '_', html.unescape( chapter['title'] ) )

                # Thanks, Teasday
                group_keys = filter(lambda s: s.startswith('group_name'), chapter.keys())
                groups     = ', '.join( filter( None, [chapter[x] for x in group_keys ] ) )
                groups     = re_regrex.sub( '_', html.unescape( groups ) )

                json_chapter = { "chapter_id": chapter_id, "lang_code": lang_code, "chapter": chapter_number, "volume": volume_number, "title": chapter_title, "groups": groups  }
                    
                chapter_response = downloadChapter(chapter_id, series_route, route, languages, 1, remove, title, check_images)

                if( 'error' in chapter_response ):
                    json_chapter["error"] = chapter_response
                else:
                    json_chapter["images"] = chapter_response

                json_data['chapters'] = json_chapter

        with open( f'{series_route}/{id}_data.json' , 'w') as file:
            file.write( json.dumps( json_data, indent=4 ) )

    elif ( 'chapter' == type ):
        downloadChapter(id, '', route, languages, 0, remove, title, check_images)
    else:
        sys.exit('Invalid type! Must be "title" or "chapter"')

def bulkDownloader(filename, language, route, type, remove, check_images):

    titles = []

    if( os.path.exists(filename) ):

        # Open file and read lines
        with open(filename, 'r') as item:
            titles = [ line.rstrip('\n') for line in item ]

        if( len(titles) == 0 ):
            sys.exit('Empty file!')
        else:
            print ('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

            # Read languages file
            with open('languages.json', 'r') as json_file:
                languages = json.load(json_file)

            #Compile regex
            compiled = re.compile('[\\\\/:*?"<>|]')

            for id in titles:
                main(id, language, route, type, remove, check_images, languages, compiled)

                if type == 'title':
                    print( 'Download Complete. Waiting 30 seconds...' )
                    time.sleep(30) # wait 30 seconds
                else:
                    print( 'Download Complete. Waiting 5 seconds...' )
                    time.sleep(5) # wait 5 seconds
    else:
        sys.exit('File not found!')
        
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l', default='gb')
    parser.add_argument('--directory', '-d', default='downloads/')
    parser.add_argument('--type', '-t', default='title') #title or chapter
    parser.add_argument('--remove', '-r', default='yes') #yes or no
    parser.add_argument('--check_images', '-c', default='no') #yes or no
    parser.add_argument('id')

    args = parser.parse_args()

    # If the ID is not a number, try to bulk download from file
    if ( not args.id.isdigit() ):
        bulkDownloader(args.id, args.language, args.directory, args.type, args.remove, args.check_images)
    else:
        main(args.id, args.language, args.directory, args.type, args.remove, args.check_images, '', '')