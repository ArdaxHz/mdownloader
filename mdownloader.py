import http.client
import sys
import json
import os
import urllib.request
import shutil

def createFolder(folder_name):
    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
    except OSError:
        sys.exit('Error creating folder')

def downloadChapter(chapter_id, folder):
    conn = http.client.HTTPSConnection('mangadex.org')
    conn.request("GET", "/api/?id=" + chapter_id + "&type=chapter")
    response = conn.getresponse()

    if ( response.status != 200 ):
        sys.exit('Request status error: ' + response.status)

    image_data = json.loads( response.read().decode() )
    conn.close()

    image_location = 'https://mangadex.org' + image_data['server'] + image_data['hash'] + '/'

    for image in image_data['page_array']:
        print ('Downloading image ' + image )
        req = urllib.request.Request(
            image_location + image,
            data=None, 
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:62.0) Gecko/20100101 Firefox/62.0'
            }
        )

        response = urllib.request.urlopen( req )

        with open( folder + '/' + image , 'wb') as out_file:
            shutil.copyfileobj(response, out_file)


def main(manga_id):
    if ( not manga_id.isdigit() ):
        sys.exit('Invalid Manga ID')

    conn = http.client.HTTPSConnection('mangadex.org')
    conn.request("GET", "/api/?id=" + manga_id + "&type=manga")
    response = conn.getresponse()

    if ( response.status != 200 ):
       sys.exit('Request status error: ' + response.status)

    data = json.loads( response.read().decode() )
    conn.close()

    title = data['manga']['title']

    createFolder(title)

    for chapter_id in data['chapter']:

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

            createFolder(chapter_route)

            print ('Downloading Volume ' + volume + ' Chapter ' + chapter + ', Title: ' + chapter_title)

            downloadChapter(chapter_id, chapter_route)


if __name__ == "__main__":
    main(sys.argv[1])
