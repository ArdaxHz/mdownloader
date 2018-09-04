import sys
import os
import time
import requests
import asyncio
import argparse
from aiohttp import ClientSession
from tqdm import tqdm

current_request = 0
headers = { 'User-Agent': 'mDownloader/1.0' }

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

async def downloadImages(image, url, folder):

    global current_request

    if ( current_request == 600 ):
        sys.exit( 'Max requests allowed. Trying again will result on your IP banned.' )

    async with ClientSession() as session:
        async with session.get( url + image ) as response:

            response = await response.read()

            with open( folder + '/' + image , 'wb') as file:
                file.write(response)

            current_request += 1

def downloadChapter(chapter_id, folder):

    # Connect to API and get chapter info
    url = f'https://mangadex.org/api/chapter/{chapter_id}'

    response = requests.get( url, headers = headers)

    if ( response.status_code != 200 ):
        sys.exit('Request status error: ' + response.status_code)

    global current_request

    current_request += 1

    image_data = response.json()
    url        = f'https://mangadex.org{image_data["server"]}{image_data["hash"]}/'

    # ASYNC FUNCTION
    loop = asyncio.get_event_loop()
    tasks = []

    for image in image_data['page_array']:
        task = asyncio.ensure_future( downloadImages(image, url, folder) )
        tasks.append(task)

    runner = wait_with_progress(tasks)
    loop.run_until_complete(runner)

def main(manga_id, language, route):

    global current_request

    print ('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

    # Check the manga id is valid
    if ( not manga_id.isdigit() ):
        sys.exit('Invalid Manga ID')

    # Connect to API and get manga info
    url = f'https://mangadex.org/api/manga/{manga_id}'

    response = requests.get( url, headers = headers)

    if ( response.status_code != 200 ):
       sys.exit('Request status error: ' + response.status_code)

    current_request += 1

    data = response.json()

    title = data['manga']['title']

    createFolder(title)

    languages = {
        'sa' : 'Arabic',
        'bd' : 'Bengali',
        'bg' : 'Bulgarian',
        'mm' : 'Burmese',
        'ct' : 'Catalan',
        'cn' : 'Chinese (Simp)',
        'hk' : 'Chinese (Trad)',
        'cz' : 'Czech',
        'dk' : 'Danish',
        'nl' : 'Dutch',
        'gb' : 'English',
        'ph' : 'Filipino',
        'fi' : 'Finnish',
        'fr' : 'French',
        'de' : 'German',
        'gr' : 'Greek',
        'hu' : 'Hungarian',
        'id' : 'Indonesian',
        'it' : 'Italian',
        'jp' : 'Japanese',
        'kr' : 'Korean',
        'my' : 'Malay',
        'mn' : 'Mongolian',
        'ir' : 'Persian',
        'pl' : 'Polish',
        'br' : 'Portuguese (Br)',
        'pt' : 'Portuguese (Pt)',
        'ro' : 'Romanian',
        'ru' : 'Russian',
        'rs' : 'Serbo-Croatian',
        'es' : 'Spanish (Es)',
        'mx' : 'Spanish (LATAM)',
        'se' : 'Swedish',
        'th' : 'Thai',
        'tr' : 'Turkish',
        'ua' : 'Ukrainian',
        'vn' : 'Vietnamese'
    }

    # Loop chapters
    for chapter_id in data['chapter']:

        if ( current_request == 600 ):
            sys.exit( 'Max requests allowed. Trying again will result on your IP banned.' )

        # Only English chapters
        if ( data['chapter'][chapter_id]['lang_code'] == language ):

            chapter        = data['chapter'][chapter_id]
            volume_number  = chapter['volume']
            chapter_number = chapter['chapter']
            chapter_title  = chapter['title']

            # Thanks, Teasday
            group_keys = filter(lambda s: s.startswith('group_name'), chapter.keys())
            groups = ', '.join( filter( None, [chapter[x] for x in group_keys ] ) )

            chapter_folder = f'[{languages[language]}][Vol. {volume_number} Ch. {chapter_number}][{groups}] - {chapter_title}'
            chapter_route  = f'{route}{title}/{chapter_folder}'

            # Check if the current folder exist. If it exists, skip it
            exists = createFolder(chapter_route)

            if (exists):
                continue

            print ( f'Downloading Volume {volume_number} Chapter {chapter_number} Title: {chapter_title}' )

            downloadChapter(chapter_id, chapter_route)

    print('Total request: %d' % ( current_request ) )

    if (current_request == 1):
        print('No chapters downloaded')


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--language',  '-l', default='gb')
    parser.add_argument('--directory', '-d', default='')
    parser.add_argument('manga_id')

    args = parser.parse_args()

    main(args.manga_id, args.language, args.directory)
