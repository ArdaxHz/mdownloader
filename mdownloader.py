import http.client
import sys
import json
import os
import urllib.request
import shutil
import time

current_request = 0

def createFolder(folder_name):
    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            return 0
        else:
            return 1
    except OSError:
        sys.exit('Error creating folder')

def downloadChapter(chapter_id, folder):

    global current_request

    conn = http.client.HTTPSConnection('mangadex.org')
    conn.request("GET", "/api/chapter/" + chapter_id )
    response = conn.getresponse()

    if ( response.status != 200 ):
        sys.exit('Request status error: ' + response.status)

    image_data = json.loads( response.read().decode() )
    conn.close()

    image_location = 'https://mangadex.org' + image_data['server'] + image_data['hash'] + '/'

    for image in image_data['page_array']:
        print ('Downloading image ' + image )

        req = urllib.request.Request( image_location + image, data=None, headers = { 'User-Agent': 'mDownloader/1.0' } )

        response = urllib.request.urlopen( req )

        with open( folder + '/' + image , 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

        current_request += 1


def main(manga_id):

    global current_request

    print ('The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.')

    if ( not manga_id.isdigit() ):
        sys.exit('Invalid Manga ID')

    conn = http.client.HTTPSConnection('mangadex.org')
    conn.request("GET", "/api/manga/" + manga_id )
    response = conn.getresponse()

    if ( response.status != 200 ):
       sys.exit('Request status error: ' + response.status)

    current_request += 1

    data = json.loads( response.read().decode() )
    conn.close()

    title = data['manga']['title']

    createFolder(title)

    for chapter_id in data['chapter']:

        if ( current_request == 600 ):
            sys.exit( 'Max requests allowed. Trying again will result on your IP banned.' )

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

            exists = createFolder(chapter_route)

            if (exists):
                continue

            print ('Downloading Volume ' + volume + ' Chapter ' + chapter + ', Title: ' + chapter_title)

            downloadChapter(chapter_id, chapter_route)

    print ('Total request: %d' % ( current_request ) )


if __name__ == "__main__":
    main(sys.argv[1])
