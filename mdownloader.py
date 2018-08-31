import sys
import os
import time
import requests
import asyncio
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

    image_data = response.json()
    url        = 'https://mangadex.org' + image_data['server'] + image_data['hash'] + '/'

    # ASYNC FUNCTION

    loop = asyncio.get_event_loop()
    tasks = []

    for image in image_data['page_array']:
        task = asyncio.ensure_future( downloadImages(image, url, folder) )
        tasks.append(task)

    runner = wait_with_progress(tasks)
    loop.run_until_complete(runner)
    loop.close()

def main(manga_id):

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

    # Loop chapters
    for chapter_id in data['chapter']:

        if ( current_request == 600 ):
            sys.exit( 'Max requests allowed. Trying again will result on your IP banned.' )

        # Only English chapters
        if ( data['chapter'][chapter_id]['lang_code'] == 'gb' ):
            volume        = data['chapter'][chapter_id]['volume']
            chapter       = data['chapter'][chapter_id]['chapter']
            chapter_title = data['chapter'][chapter_id]['title']

            groups = data['chapter'][chapter_id]['group_name']

            if ( data['chapter'][chapter_id]['group_id_2'] > 0 ):
                groups += ', ' + data['chapter'][chapter_id]['group_name_2']

            if ( data['chapter'][chapter_id]['group_id_3'] > 0 ):
                groups += ', ' + data['chapter'][chapter_id]['group_name_3']

            chapter_folder = '[Vol. ' + volume + ' Ch. ' + chapter + '][' + groups + '] - ' + chapter_title
            chapter_route = title + '/' + chapter_folder

            # Check if the current folder exist. If it exists, skip it
            exists = createFolder(chapter_route)

            if (exists):
                continue

            print ('Downloading Volume ' + volume + ' Chapter ' + chapter + ', Title: ' + chapter_title)

            downloadChapter(chapter_id, chapter_route)

    print ('Total request: %d' % ( current_request ) )


if __name__ == "__main__":
    main(sys.argv[1])
