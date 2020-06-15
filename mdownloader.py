import sys
import os
import time
import requests
import asyncio
import argparse
import re
import html
import json

from aiohttp import ClientSession, ClientError
from tqdm import tqdm

headers = { 'User-Agent': 'mDownloader/1.0' }
domain  = 'https://mangadex.org'

def createFolder(folder_name):
    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            return 0
        else:
            return 1
    except OSError:
        sys.exit('Error creating folder')

@asyncio.coroutine
def wait_with_progress(coros):
    for f in tqdm(asyncio.as_completed(coros), total=len(coros)):
        yield from f

async def downloadImages(image, url, folder, retry):

    #try to download it 3 times
    while( retry < 3 ):
        async with ClientSession() as session:
            try:
                async with session.get( url + image ) as response:
    
                    assert response.status == 200
    
                    response = await response.read()
    
                    with open( folder + '/' + image , 'wb') as file:
                        file.write(response)

                    retry = 3
            except (ClientError, AssertionError):
                print( f'An error happened when downloading image {image}. Trying again...' )
                await asyncio.sleep(1)

                retry += 1

                if( retry == 3 ):
                    print( f'Could not download image {image} after 3 times.' )
                    await asyncio.sleep(1)

# type 0 -> chapter
# type 1 -> title
def downloadChapter(chapter_id, folder, type):

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
    else:
        image_data = response.json()
        server_url = ''

        #Extenal chapters
        if( 'external' == image_data["status"] ):
            print ( f'Chapter external to Mangadex. Unable to download.' )
        else:
            server_url = image_data["server"]

            url = f'{server_url}{image_data["hash"]}/'

            # Only for chapter downloads
            # It is not possible at the moment to get the groups names from the chapter API endpoint
            # Only the group IDs are added to the chapter folder
            if( type ):
                group_keys = filter(lambda s: s.startswith('group_id'), image_data.keys())
                groups = ', '.join( filter( lambda zero: zero != '0', [ str( image_data[x] ) for x in group_keys ] ) )

                folder = f'[{image_data["lang_name"]}][Vol. {image_data["volume"]} Ch. {image_data["chapter"]}][{groups}] - {image_data["title"]}'

                # Check if the current folder exist. If it exists, skip it
                exists = createFolder(folder)

                if (exists):
                    sys.exit('Chapter already downloaded')

                print ( f'Downloading Volume {image_data["volume"]} Chapter {image_data["chapter"]} Title: {image_data["title"]}' )

            # ASYNC FUNCTION
            loop  = asyncio.get_event_loop()
            tasks = []

            for image in image_data['page_array']:
                task = asyncio.ensure_future( downloadImages(image, url, folder, 0) )
                tasks.append(task)

            runner = wait_with_progress(tasks)
            loop.run_until_complete(runner)

def main(id, language, route, type):

    # Check the id is valid number
    if ( not id.isdigit() ):
        sys.exit('Invalid Title/Chapter ID')

    print ('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

    if ( 'title' == type ):
        # Connect to API and get manga info
        url = f'{domain}/api?id={id}&type=manga'

        response = requests.get( url, headers = headers)

        if ( response.status_code != 200 ):
            sys.exit( f'Request status error: {response.status_code}' )

        re_regrex = re.compile('[\\\\/:*?"<>|]')

        data = response.json()

        title  = re_regrex.sub( '_', html.unescape( data['manga']['title'] ) )

        createFolder( title )

        # Read languages file
        with open('languages.json', 'r') as json_file:
            languages = json.load(json_file)

        # Loop chapters
        for chapter_id in data['chapter']:

            # Only chapters of language selected. Default language: English.
            if ( data['chapter'][chapter_id]['lang_code'] == language ):

                chapter        = data['chapter'][chapter_id]
                volume_number  = chapter['volume']
                chapter_number = chapter['chapter']
                chapter_title  = re_regrex.sub( '_', html.unescape( chapter['title'] ) )

                # Thanks, Teasday
                group_keys = filter(lambda s: s.startswith('group_name'), chapter.keys())
                groups     = ', '.join( filter( None, [chapter[x] for x in group_keys ] ) )
                groups     = re_regrex.sub( '_', html.unescape( groups ) )

                chapter_folder = f'[{languages[language]}][Vol. {volume_number} Ch. {chapter_number}][{groups}] - {chapter_title}'
                chapter_route  = f'{route}{title}/{chapter_folder}'

                # Check if the current folder exist. If it exists, skip it
                exists = createFolder(chapter_route)

                if (exists):
                    continue

                print ( f'Downloading Volume {volume_number} Chapter {chapter_number} Title: {chapter_title}' )
    
                downloadChapter(chapter_id, chapter_route, 0)

    elif ( 'chapter' == type ):
        downloadChapter(id, '', 1)
    else:
        sys.exit('Invalid type! Must be "title" or "chapter"')

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--language',  '-l', default='gb')
    parser.add_argument('--directory', '-d', default='')
    parser.add_argument('--type',      '-t', default='title') #Title or Chapter
    parser.add_argument('id')

    args = parser.parse_args()

    main(args.id, args.language, args.directory, args.type)
