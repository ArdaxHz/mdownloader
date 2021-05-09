#!/usr/bin/python3
import asyncio
import html
import re
from datetime import datetime
from typing import Type, Union

import requests
from aiohttp import ClientSession, ClientError
from tqdm import tqdm

from .constants import ImpVar
from .exporter import ArchiveExporter, FolderExporter
from .mangaplus import MangaPlus

domain = ImpVar.MANGADEX_API_URL
re_regrex = re.compile(ImpVar.REGEX)


# Display progress bar of downloaded images
async def displayProgress(tasks: list):
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=(str(datetime.now(tz=None))[:-7])):
        try:
            await f
        except ConnectionResetError:
            pass
        except Exception as e:
            print(e)
    return


# Download the MD chapter images
async def imageDownloader(
        url: str,
        fallback_url: str,
        image: str,
        pages: list,
        exporter: Type[Union[ArchiveExporter, FolderExporter]]):
    # pylint: disable=unsubscriptable-object
    retry = 0
    fallback_retry = 0
    retry_max_times = 3

    # Try to download it retry_max_times times
    while retry < retry_max_times:
        async with ClientSession() as session:
            try:
                async with session.get(url + image) as response:

                    assert response.status == 200
                    response = await response.read()

                    page_no = pages.index(image) + 1
                    extension = image.split('.', 1)[1]

                    # Add image to archive
                    exporter.addImage(response, page_no, extension)

                    retry = retry_max_times
                    return

            except (ClientError, AssertionError, ConnectionResetError, asyncio.TimeoutError):
                await asyncio.sleep(3)

                retry += 1

                if retry == retry_max_times:
                    if fallback_url != '' and fallback_retry == 0:
                        retry = 0
                        fallback_retry = 1
                        url = fallback_url
                        print(f'Retrying with the fallback url.')
                    else:
                        print(f'Could not download image {image} after {retry} times.')
                        return


# download_type 0 -> chapter
# download_type 1 -> title
# download_type 2 -> group/user/list
def chapterDownloader(md_model):
    manga_plus_id = '4f1de6a2-f0c5-4ac5-bce5-02c7dbb67deb'
    chapter_id = md_model.chapter_id
    external = False

    if md_model.type_id == 0:
        chapter_id = md_model.id

    # Connect to API and get chapter info
    response = md_model.requestData(chapter_id, 'chapter')
    data = md_model.getData(response)
    md_model.chapter_data = data

    # Make sure only downloadable chapters are downloaded
    if data["result"] not in ('ok'):
        return

    if r'https://mangaplus.shueisha.co.jp/viewer/' in data["data"]["attributes"]["data"][0]:
        external = True

    # group_ids = [g["id"] for g in data["relationships"] if g["type"] == 'scanlation_group']

    # if manga_plus_id in group_ids:
    #     external = True

    chapter_data = data["data"]["attributes"]

    # chapter, group, user downloads
    if md_model.type_id in (0, 2):
        manga_id = [c["id"] for c in data["relationships"] if c["type"] == 'manga'][0]
        manga_response = requests.get(f'{domain}/manga/{manga_id}')
        if manga_response.status_code == 200:
            manga_data = manga_response.json()
            title = manga_data["data"]["attributes"]["title"]["en"]
            title = re_regrex.sub('_', html.unescape(title)).rstrip(' .')
            md_model.title = title
            md_model.formatRoute()
    else:
        title = md_model.title

    md_model.prefix = md_model.chapter_prefix_dict.get(chapter_data["volume"], 'c')

    # Make the files
    if md_model.make_folder:
        exporter = FolderExporter(md_model)
    else:
        exporter = ArchiveExporter(md_model)

    md_model.exporter = exporter
    
    # Add chapter data to the json for title, group or user downloads
    if md_model.type_id == 1:
        md_model.title_json.chapters(data["data"])
    elif md_model.type_id == 2:
            md_model.account_json.chapters(data["data"])

    print(f'Downloading {title} | Volume: {chapter_data["volume"]} | Chapter: {chapter_data["chapter"]} | Title: {chapter_data["title"]}')

    # External chapters
    if external:
        # Call MangaPlus downloader
        print('External chapter. Connecting to MangaPlus to download.')
        MangaPlus(md_model).plusImages()
        return

    server_base = f'{domain}/at-home/server/{chapter_id}'
    server_response = requests.get(server_base)
    if server_response.status_code == 200:
        server = server_response.json()["baseUrl"]

    url = f'{server}/data/{chapter_data["hash"]}/'
    fallback_url = ''
    pages = chapter_data["data"]

    # Check if the chapter has been downloaded already
    exists = md_model.checkExist(pages)
    md_model.existsBeforeDownload(exists)

    # ASYNC FUNCTION
    loop  = asyncio.get_event_loop()
    tasks = []

    # Download images
    for image in pages:
        task = asyncio.ensure_future(imageDownloader(url, fallback_url, image, pages, exporter))
        tasks.append(task)

    runner = displayProgress(tasks)
    loop.run_until_complete(runner)

    downloaded_all = md_model.checkExist(pages)
    md_model.existsAfterDownload(downloaded_all)
    return
