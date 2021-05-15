#!/usr/bin/python3
import asyncio
import time
from datetime import datetime
from typing import Type, Union

from aiohttp import ClientSession, ClientError
from tqdm import tqdm

from .constants import ImpVar
from .exporter import ArchiveExporter, FolderExporter
from .mangaplus import MangaPlus
from .model import MDownloader

domain = ImpVar.MANGADEX_API_URL


def reportImage(
        md_model: MDownloader,
        success: bool,
        image_link: str,
        img_size: int,
        start_time: int) -> None:
    """Report the success of the image.

    Args:
        md_model (MDownloader): The base class this program runs on.
        success (bool): If the image was downloaded or not.
        image_link (str): The url of the image.
        img_size (int): The size in bytes of the image.
        start_time (int): When the request was started.
    """

    end_time = time.time()
    elapsed_time = int((end_time - start_time) * 1000)

    data = {
        "url": image_link,
        "success": success,
        "bytes": img_size,
        "duration": elapsed_time
    }

    response = md_model.postData('https://api.mangadex.network/report', data)
    # if not success:
    #     print(f'Reporting image {str(success)}.')
    # data = md_model.convertJson(md_mode.chapter_id, 'image-report', response)


def getServer(md_model: MDownloader) -> str:
    """Get the MD@H node to download images from.

    Args:
        md_model (MDownloader): The base class this program runs on.

    Returns:
        str: The MD@H node to download images from.
    """
    server_response = md_model.requestData(md_model.chapter_id, 'at-home/server')
    server_data = md_model.convertJson(md_model.chapter_id, 'chapter-server', server_response)
    return server_data["baseUrl"]


async def displayProgress(tasks: list) -> None:
    """Display a progress bar of the downloaded images.

    Args:
        tasks (list): Asyncio tasks for downloading images.
    """
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=(str(datetime.now(tz=None))[:-7])):
        try: await f
        except ConnectionResetError: pass
        except Exception as e: print(e)


async def imageDownloader(
        md_model: MDownloader,
        url: str,
        fallback_url: str,
        image: str,
        pages: list,
        exporter: Type[Union[ArchiveExporter, FolderExporter]]) -> None:
    """Download the MangaDex chapter images.

    Args:
        md_model (MDownloader): The base class this program runs on.
        url (str): The server to download images from.
        fallback_url (str): A backup server to download images from.
        image (str): The image name.
        pages (list): List of all the images.
        exporter (Type[Union[ArchiveExporter, FolderExporter]]): Add images to the exporter.
    """
    retry = 0
    fallback_retry = 0
    retry_max_times = 3
    image_link = url + image

    # Try to download it retry_max_times times
    while retry < retry_max_times:
        start_time = time.time()
        async with ClientSession() as session:
            try:
                async with session.get(image_link) as response:

                    assert response.status == 200
                    img_data = await response.read()

                    reportImage(md_model, True, image_link, len(img_data), start_time)

                    page_no = pages.index(image) + 1
                    extension = image.split('.', 1)[1]

                    # Add image to archive
                    exporter.addImage(img_data, page_no, extension)

                    retry = retry_max_times

            except (ClientError, AssertionError, ConnectionResetError, asyncio.TimeoutError):
                retry += 1

                reportImage(md_model, False, image_link, 0, start_time)

                if retry == retry_max_times:

                    if fallback_url != '' and fallback_retry == 0:
                        retry = 0
                        fallback_retry = 1
                        url = fallback_url
                        print(f'Retrying with the fallback url.')
                    else:
                        print(f'Could not download image {image_link} after {retry} times.')

                await asyncio.sleep(3)


def chapterDownloader(md_model: MDownloader) -> None:
    """download_type: 0 = chapter
    download_type: 1 = manga
    download_type: 2 = group|user|list
    download_type: 3 = manga title through group

    Args:
        md_model (MDownloader): [description]
    """
    manga_plus_id = '4f1de6a2-f0c5-4ac5-bce5-02c7dbb67deb'
    chapter_id = md_model.chapter_id
    external = False

    if md_model.type_id in (0, 1):
        # Connect to API and get chapter info
        response = md_model.requestData(chapter_id, 'chapter')
        data = md_model.convertJson(chapter_id, 'chapter', response)
        md_model.chapter_data = data
    else:
        data = md_model.chapter_data

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
    if md_model.type_id == 0:
        manga_id = [c["id"] for c in data["relationships"] if c["type"] == 'manga'][0]
        manga_response = md_model.requestData(manga_id, 'manga')
        manga_data = md_model.convertJson(manga_id, 'chapter-manga', manga_response)

        title = md_model.formatTitle(manga_data)
    else:
        title = md_model.title

    md_model.prefix = md_model.chapter_prefix_dict.get(chapter_data["volume"], 'c')

    # Make the files
    if md_model.make_folder:
        exporter = FolderExporter(md_model)
    else:
        exporter = ArchiveExporter(md_model)

    md_model.exporter = exporter

    print(f'Downloading {title} | Volume: {chapter_data["volume"]} | Chapter: {chapter_data["chapter"]} | Title: {chapter_data["title"]}')

    # External chapters
    if external:
        # Call MangaPlus downloader
        print('External chapter. Connecting to MangaPlus to download.')
        MangaPlus(md_model).plusImages()
        return

    server = getServer(md_model)
    fallback_server = getServer(md_model)

    url = f'{server}/data/{chapter_data["hash"]}/'
    fallback_url = f'{fallback_server}/data/{chapter_data["hash"]}/'
    pages = chapter_data["data"]

    # Check if the chapter has been downloaded already
    exists = md_model.checkExist(pages)
    md_model.existsBeforeDownload(exists)

    # ASYNC FUNCTION
    loop  = asyncio.get_event_loop()
    tasks = []

    # Download images
    for image in pages:
        task = asyncio.ensure_future(imageDownloader(md_model, url, fallback_url, image, pages, exporter))
        tasks.append(task)

    runner = displayProgress(tasks)
    loop.run_until_complete(runner)

    downloaded_all = md_model.checkExist(pages)
    md_model.existsAfterDownload(downloaded_all)
