#!/usr/bin/python3
import asyncio
import time
from datetime import datetime
from typing import Type, Union

from aiohttp import ClientSession, ClientError
from tqdm import tqdm

from .constants import ImpVar
from .errors import MDownloaderError
from .exporter import ArchiveExporter, FolderExporter
from .model import MDownloader


def report_image(
        md_model: MDownloader,
        success: bool,
        image_link: str,
        img_size: int,
        start_time: int) -> None:
    """Report the success of the image.

    Args:
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

    response = md_model.api.post_data(md_model.report_url, data)

    if md_model.debug: print(f'Reporting image {str(success)}.')

    # data = md_model.api.convertJson(md_mode.chapter_id, 'image-report', response)


def get_server(md_model: MDownloader) -> str:
    """Get the MD@H node to download images from."""
    server_response = md_model.api.request_data(f'{md_model.mdh_url}/{md_model.chapter_id}')
    server_data = md_model.api.convert_to_json(md_model.chapter_id, 'chapter-server', server_response)
    return server_data["baseUrl"]


async def display_progress(tasks: list) -> None:
    """Display a progress bar of the downloaded images using the asyncio tasks."""
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=(str(datetime.now(tz=None))[:-7])):
        try: await f
        except ConnectionResetError: pass
        except Exception as e: print(e)


async def image_download(
        md_model: MDownloader,
        url: str,
        fallback_url: str,
        image: str,
        pages: list,
        exporter: Type[Union[ArchiveExporter, FolderExporter]]) -> None:
    """Download the MangaDex chapter images.

    Args:
        url (str): The server to download images from.
        fallback_url (str): A backup server to download images from.
        image (str): The image name.
        pages (list): List of all the images.
        exporter (Type[Union[ArchiveExporter, FolderExporter]]): Add images to the exporter.
    """
    retry = 0
    fallback_retry = 0
    retry_max_times = ImpVar.RETRY_MAX_TIMES
    time_to_sleep = ImpVar.TIME_TO_SLEEP

    # Try to download it retry_max_times times
    while retry < retry_max_times:
        start_time = time.time()
        image_link = url + image
        async with ClientSession() as session:
            try:
                async with session.get(image_link) as response:

                    assert response.status == 200
                    img_data = await response.read()

                    report_image(md_model, True, image_link, len(img_data), start_time)

                    page_no = pages.index(image) + 1
                    extension = image.split('.', 1)[1]

                    # Add image to archive
                    exporter.add_image(img_data, page_no, extension, image)

                    retry = retry_max_times

            except (ClientError, AssertionError, ConnectionResetError, asyncio.TimeoutError):
                retry += 1

                report_image(md_model, False, image_link, 0, start_time)

                if retry == retry_max_times:

                    if fallback_url != '' and fallback_retry == 0:
                        retry = 0
                        fallback_retry = 1
                        url = fallback_url
                        if md_model.debug: print(f'Retrying with the fallback url.')
                    else:
                        print(f'Could not download image {image_link} after {retry} times.')

                await asyncio.sleep(time_to_sleep)


def chapter_downloader(md_model: MDownloader) -> None:
    """Use the chapter data for image downloads and file name export.

    download_type: 0 = chapter
    download_type: 1 = manga
    download_type: 2 = group|user|list
    download_type: 3 = follows
    """
    chapter_id = md_model.chapter_id
    data = md_model.chapter_data
    title = md_model.title
    chapter_data = data["data"]["attributes"]
    md_model.prefix = md_model.chapter_prefix_dict.get(chapter_data["volume"], 'c')

    print(f'Downloading {title} | Volume: {chapter_data["volume"]} | Chapter: {chapter_data["chapter"]} | Title: {chapter_data["title"]}')

    external = md_model.misc.check_external(chapter_data)

    # Make the files
    if md_model.args.folder_download:
        exporter = FolderExporter(md_model)
    else:
        exporter = ArchiveExporter(md_model)

    md_model.exporter = exporter

    # Add chapter data to the json for title, group or user downloads
    if md_model.type_id in (1,):
        md_model.title_json.add_chapter(data)
    if md_model.type_id in (2, 3):
        md_model.bulk_json.add_chapter(data)

    # External chapters
    if external is not None:
        from .external import MangaPlus, ComiKey
        if 'mangaplus' in external:
            # Call MangaPlus downloader
            print('External chapter. Connecting to MangaPlus to download.')
            MangaPlus(md_model, external).download_mplus_chap()
        elif 'comikey' in external:
            # Call ComiKey downloader
            print('External chapter. Connecting to ComiKey to download.')
            ComiKey(md_model, external).download_comikey_chap()
        return

    pages = chapter_data["data"]

    if not pages:
        raise MDownloaderError('This chapter has no pages.')

    # Check if the chapter has been downloaded already
    exists = md_model.exist.check_exist(pages)
    md_model.exist.before_download(exists)

    server = get_server(md_model)
    fallback_server = get_server(md_model)

    url = f'{server}/data/{chapter_data["hash"]}/'
    fallback_url = f'{fallback_server}/data/{chapter_data["hash"]}/'

    # ASYNC FUNCTION
    loop  = asyncio.get_event_loop()
    tasks = []

    # Download images
    for image in pages:
        task = asyncio.ensure_future(image_download(md_model, url, fallback_url, image, pages, exporter))
        tasks.append(task)

    runner = display_progress(tasks)
    loop.run_until_complete(runner)

    downloaded_all = md_model.exist.check_exist(pages)
    md_model.exist.after_download(downloaded_all)
