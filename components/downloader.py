#!/usr/bin/python3
import dataclasses
from ast import arg
from copy import copy
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import hondana

from .args import MDArgs, ProcessArgs
from .cache import CacheRead
from .constants import ImpVar
from .errors import MDownloaderError
from .image_downloader import ImageDownloader
from .jsonmaker import BulkJson, TitleJson


class Filtering:
    def __init__(self) -> None:
        self.root = Path(".")
        self._group_blacklist_file = self.root.joinpath(ImpVar.GROUP_BLACKLIST_FILE)
        self._group_whitelist_file = self.root.joinpath(ImpVar.GROUP_WHITELIST_FILE)
        self._user_blacklist_file = self.root.joinpath(ImpVar.USER_BLACKLIST_FILE)
        self._user_userlist_file = self.root.joinpath(ImpVar.USER_WHITELIST_FILE)

        self.group_blacklist = self._read_file(self._group_blacklist_file)
        self.group_whitelist = self._read_file(self._group_whitelist_file)
        self.user_blacklist = self._read_file(self._user_blacklist_file)
        self.user_whitelist = self._read_file(self._user_userlist_file)

    def _read_file(self, file_path: Path) -> Optional[List[str]]:
        """Opens the text file and loads the ids to filter."""
        try:
            with open(file_path, "r") as fp:
                filter_list = [line.rstrip("\n") for line in fp.readlines()]
                if not filter_list:
                    return
                return filter_list
        except FileNotFoundError:
            return


async def download_chapters(
    *,
    args: ProcessArgs,
    args_obj: MDArgs,
    chapters_to_download: List[MDArgs],
    image_downloader_obj: Optional[ImageDownloader] = None,
    sorted_chapters_to_download: Optional[Dict[str, Dict[str, Union[MDArgs, List[hondana.Chapter]]]]] = None,
) -> None:
    """Loop chapters and call the baseDownloader function.

    Args:
        chapters (list): The chapters to download.
        chapters_data (list): The ids of the downloaded chapters from the data json.
    """
    for chapter in chapters_to_download:

        if args_obj.type != "manga":
            manga_args_obj = sorted_chapters_to_download[chapter.data.manga_id]["manga_args_obj"]
            image_downloader_obj = ImageDownloader(args, manga_args_obj)
            image_downloader_obj.json_exporter = args_obj.json_obj

        try:
            await image_downloader_obj.chapter_downloader(chapter)
            # md_model.wait(1)
        except MDownloaderError as e:
            if e:
                print(e)


class MangaDownloader:
    def __init__(
        self,
        args: ProcessArgs,
        manga_args_obj: MDArgs,
        *,
        chapters: Optional[List[hondana.Chapter]] = None,
        bulk_json_obj: Optional[BulkJson] = None,
    ) -> None:
        self._args = args
        self.manga_args_obj = manga_args_obj
        self.chapters = chapters
        self.bulk_json_obj = bulk_json_obj

    def _get_prefixes(self, chapters: list) -> dict:
        """Assign each volume a prefix, default: c.

        Returns:
            dict: A map of the volume number to prefix.
        """
        volume_dict = {}
        chapter_prefix_dict = {}

        # Loop over the chapters and add the chapter numbers to the volume number dict
        for c in chapters:
            c = c["attributes"]
            volume_no = c["volume"]
            try:
                volume_dict[volume_no].append(c["chapter"])
            except KeyError:
                volume_dict[volume_no] = [c["chapter"]]

        list_volume_dict = list(reversed(list(volume_dict)))
        prefix = "b"

        # Loop over the volume dict list and
        # check if the current iteration has the same chapter numbers as the volume before and after
        for volume in list_volume_dict:
            if volume is None or volume == "":
                continue

            next_volume_index = list_volume_dict.index(volume) + 1
            previous_volume_index = list_volume_dict.index(volume) - 1
            result = False

            try:
                next_item = list_volume_dict[next_volume_index]
                result = any(elem in volume_dict[next_item] for elem in volume_dict[volume])
            except (KeyError, IndexError):
                previous_volume = list_volume_dict[previous_volume_index]
                result = any(elem in volume_dict[previous_volume] for elem in volume_dict[volume])

            if volume is not None or volume != "":
                if result:
                    vol_prefix = chr(ord(prefix) + next_volume_index)
                else:
                    vol_prefix = "c"
                chapter_prefix_dict.update({volume: vol_prefix})
        return chapter_prefix_dict

    def _natsort(self, x) -> Union[float, str]:
        """Sort the chapter numbers naturally."""
        try:
            return float(x)
        except TypeError:
            return "0"
        except ValueError:
            return x

    def _get_chapters_range(self, chapters_list: List[str], chap_list: List[str]) -> List[Union[str, None]]:
        """Loop through the lists and get the chapters between the upper and lower bounds.

        Args:
            chapters_list (list): All the chapters in the manga.
            chap_list (list): A list of chapter numbers to download.

        Returns:
            list: The chapters to download the data of.
        """
        chapters_range = []

        for chapter in chap_list:
            if "-" in chapter:
                chapter_range = chapter.split("-")
                chapter_range = [None if v == "oneshot" else v for v in chapter]
                lower_bound = chapter_range[0].strip()
                upper_bound = chapter_range[1].strip()
                try:
                    lower_bound_i = chapters_list.index(lower_bound)
                except ValueError:
                    print(f"Chapter lower bound {lower_bound} does not exist. Skipping {chapter}.")
                    continue
                try:
                    upper_bound_i = chapters_list.index(upper_bound)
                except ValueError:
                    print(f"Chapter upper bound {upper_bound} does not exist. Skipping {chapter}.")
                    continue
                range = chapters_list[lower_bound_i : upper_bound_i + 1]
            else:
                if chapter == "oneshot":
                    range = None
                try:
                    range = [chapters_list[chapters_list.index(chapter)]]
                except ValueError:
                    print(f"Chapter {chapter} does not exist. Skipping.")
                    continue
            chapters_range.extend(range)
        return chapters_range

    def _download_range_chapters(self, chapters: List[MDArgs]) -> List[MDArgs]:
        """Get the chapter numbers you want to download.

        Returns:
            list: The chapters to download.
        """
        chapters_numbers_list = [c.data.chapter for c in chapters]
        chapters_list_str = ["oneshot" if c is None else c for c in chapters_numbers_list]
        chapters_numbers_list = list(set(chapters_numbers_list))
        chapters_numbers_list.sort(key=self._natsort)
        remove_chapters = []

        if not chapters_numbers_list:
            return chapters

        print(f'Available chapters:\n{", ".join(chapters_list_str)}')
        input_raw_chap_list = input("\nEnter the chapter(s) to download: ").strip()

        if not input_raw_chap_list:
            raise MDownloaderError("No chapter(s) chosen.")

        input_split_chap_list = [c.strip() for c in input_raw_chap_list.split(",")]
        chapters_to_remove = [c.strip("!") for c in input_split_chap_list if "!" in c]
        input_chap_list = [c for c in input_split_chap_list if "!" not in c]

        # Find which chapters to download
        if "all" not in input_chap_list:
            chapters_to_download = self._get_chapters_range(chapters_numbers_list, input_chap_list)
        else:
            chapters_to_download = chapters_numbers_list

        # Get the chapters to remove from the download list
        remove_chapters = self._get_chapters_range(chapters_numbers_list, chapters_to_remove)

        for i in remove_chapters:
            chapters_to_download.remove(i)
        return [c for c in chapters if c.data.chapter in chapters_to_download]

    async def manga_download(self) -> None:
        """Download manga."""
        manga_id = self.manga_args_obj.id
        download_type = self.manga_args_obj.type

        manga_cache_obj = CacheRead(self._args, cache_id=manga_id, cache_type="manga")
        refresh_cache = manga_cache_obj.check_cache_time()

        if self.manga_args_obj.data or refresh_cache or not bool(manga_cache_obj.cache.data):
            if self.manga_args_obj.data:
                manga_data: hondana.Manga = self.manga_args_obj.data
            else:
                manga_data = await self._args._hondana_client.view_manga(manga_id)
            manga_cache_obj.save_cache(cache_time=datetime.now(), data=manga_data)
        else:
            manga_data = hondana.Manga(self._args._hondana_client._http, manga_cache_obj.cache.data.copy())

        self.manga_args_obj.cache = manga_cache_obj
        self.manga_args_obj.data = manga_data
        image_downloader_obj = ImageDownloader(self._args, manga_args_obj=self.manga_args_obj)
        # Initalise json classes and make series folders
        title_json_obj = TitleJson(self._args, self.manga_args_obj, image_downloader_obj)
        self.manga_args_obj.json_obj = title_json_obj
        image_downloader_obj.json_exporter = title_json_obj
        image_downloader_obj._manga_args_obj = self.manga_args_obj

        if self.bulk_json_obj is None:
            filtering_obj = Filtering()
            json_chapters_ids = title_json_obj.downloaded_ids

            if refresh_cache or not bool(manga_cache_obj.cache.chapters):
                feed_response = await manga_data.feed(
                    limit=None,
                    translated_language=[self._args.language],
                    excluded_groups=filtering_obj.group_blacklist,
                    excluded_uploaders=filtering_obj.user_blacklist,
                    includes=hondana.query.ChapterIncludes(manga=False),
                    content_rating=[
                        hondana.ContentRating.safe,
                        hondana.ContentRating.suggestive,
                        hondana.ContentRating.erotica,
                        hondana.ContentRating.pornographic,
                    ],
                    order=hondana.query.FeedOrderQuery(
                        volume=hondana.query.Order.descending, chapter=hondana.query.Order.descending
                    ),
                )

                manga_cache_obj.save_cache(cache_time=datetime.now(), chapters=copy(feed_response))
                chapters = feed_response.chapters
            else:
                chapters: List[hondana.Chapter] = [
                    hondana.Chapter(self._args._hondana_client._http, x) for x in manga_cache_obj.cache.chapters
                ]

            self.manga_args_obj.chapters = chapters
            # chapter_prefix_dict = await args._hondana_client.get_manga_volumes_and_chapters(manga_id)
            # chapter_prefix_dict.volumes
        else:
            chapters = self.manga_args_obj.chapters
            json_chapters_ids = self.bulk_json_obj.downloaded_ids
            download_type = f"{download_type}-manga"

        chapters_to_download = [
            MDArgs(
                id=x.id, type="chapter", data=x, json_obj=title_json_obj if download_type == "manga" else self.bulk_json_obj
            )
            for x in chapters
            if x.id not in json_chapters_ids
        ]
        # md_model.misc.download_message(0, download_type, title)

        if self._args.range_download and download_type == "manga":
            chapters_to_download = self._download_range_chapters(chapters_to_download)

        await download_chapters(
            args=self._args,
            args_obj=self.manga_args_obj,
            chapters_to_download=chapters_to_download,
            image_downloader_obj=image_downloader_obj,
        )
        # md_model.misc.download_message(1, download_type, title)

        # Save the json and covers if selected
        await title_json_obj.core(1)


class BulkDownloader:
    def __init__(
        self,
        args: ProcessArgs,
        bulk_args_obj: MDArgs,
    ) -> None:
        self._args = args
        self.bulk_args_obj = bulk_args_obj
        self._filter_obj = Filtering()

    async def get_manga_data(self, manga_args_obj: MDArgs) -> MDArgs:
        manga_id = manga_args_obj.id
        manga_cache_obj = CacheRead(self._args, cache_id=manga_id, cache_type="manga")
        refresh_cache = manga_cache_obj.check_cache_time()

        if refresh_cache or not bool(manga_cache_obj.cache.data):
            manga_data = await self._args._hondana_client.view_manga(manga_id)
            manga_cache_obj.save_cache(cache_time=datetime.now(), data=manga_data)
            manga_cache_obj.cache.data
        else:
            manga_data = hondana.Manga(self._args._hondana_client._http, manga_cache_obj.cache.data.copy())

        manga_args_obj.cache = manga_cache_obj
        manga_args_obj.data = manga_data
        return manga_args_obj

    async def _sort_by_manga(self, chapters: List[hondana.Chapter]):
        titles = {}
        for chapter in chapters:
            manga_id = chapter.manga_id

            if manga_id in titles:
                titles[manga_id]["chapters"].append(chapter)
            else:
                manga_args_obj = MDArgs(id=manga_id, type="manga")
                if self._args.download_in_order:
                    await self.get_manga_data(manga_args_obj)

                titles[manga_id] = {
                    "manga_args_obj": manga_args_obj,
                    "chapters": [chapter],
                }
        return titles

    async def bulk_downlading(self, chapters: List[hondana.Chapter]):
        bulk_json_obj = BulkJson(self._args, self.bulk_args_obj)
        self.bulk_args_obj.json_obj = bulk_json_obj
        sorted_chapters_to_download = await self._sort_by_manga(chapters)

        if self._args.download_in_order:
            chapters_to_download = [
                MDArgs(id=x.id, type="chapter", data=x, json_obj=bulk_json_obj)
                for x in chapters
                if x.id not in bulk_json_obj.downloaded_ids
            ]

            await download_chapters(
                args=self._args,
                args_obj=self.bulk_args_obj,
                chapters_to_download=chapters_to_download,
                sorted_chapters_to_download=sorted_chapters_to_download,
            )
        else:
            for manga_id in sorted_chapters_to_download:
                manga_args_obj = sorted_chapters_to_download[manga_id]["manga_args_obj"]
                manga_args_obj.chapters = sorted_chapters_to_download[manga_id]["chapters"]
                manga_dl_obj = MangaDownloader(
                    self._args,
                    manga_args_obj,
                    chapters=sorted_chapters_to_download[manga_id]["chapters"],
                    bulk_json_obj=bulk_json_obj,
                )
                await manga_dl_obj.manga_download()

    async def group_download(self):
        group_id = self.bulk_args_obj.id
        download_type = self.bulk_args_obj.type

        group_cache_obj = CacheRead(self._args, cache_id=group_id, cache_type="group")
        refresh_cache = group_cache_obj.check_cache_time()

        if refresh_cache or not bool(group_cache_obj.cache.data):
            group_response = await self._args._hondana_client.get_scanlation_group(group_id)
            group_cache_obj.save_cache(cache_time=datetime.now(), data=group_response)
        else:
            group_response = hondana.ScanlatorGroup(self._args._hondana_client._http, group_cache_obj.cache.data.copy())

        self.bulk_args_obj.cache = group_cache_obj
        self.bulk_args_obj.data = group_response

        if refresh_cache or not bool(group_cache_obj.cache.chapters):
            feed_response = await self._args._hondana_client.chapter_list(
                limit=None,
                groups=[group_id],
                translated_language=[self._args.language],
                excluded_groups=self._filter_obj.group_blacklist,
                excluded_uploaders=self._filter_obj.user_blacklist,
                includes=hondana.query.ChapterIncludes(scanlation_group=False),
                content_rating=[
                    hondana.ContentRating.safe,
                    hondana.ContentRating.suggestive,
                    hondana.ContentRating.erotica,
                    hondana.ContentRating.pornographic,
                ],
                order=hondana.query.FeedOrderQuery(created_at=hondana.query.Order.descending),
            )
            group_cache_obj.save_cache(cache_time=datetime.now(), chapters=copy(feed_response))
            chapters = feed_response.chapters
        else:
            chapters: List[hondana.Chapter] = [
                hondana.Chapter(self._args._hondana_client._http, x) for x in group_cache_obj.cache.chapters
            ]

        await self.bulk_downlading(chapters)

    async def user_download(self):
        pass

    async def list_download(self):
        pass


async def bulk_download(md_model) -> None:
    """Download group, user and list chapters."""
    download_type = md_model.download_type

    if md_model.type_id == 2:
        cache_json = md_model.cache.load_cache(md_model.id)
        refresh_cache = md_model.cache.check_cache_time(cache_json)
        data = cache_json.get("data", {})

        if refresh_cache or not data:
            response = md_model.api.request_data(
                f"{md_model.api_url}/{md_model.download_type}/{md_model.id}", **{"includes[]": ["user", "leader", "member"]}
            )
            data = md_model.api.convert_to_json(md_model.id, download_type, response)

            md_model.cache.save_cache(datetime.now(), download_id=md_model.id, data=data)
            md_model.wait()

        # Order the chapters descending by the order they're released to read
        md_model.params.update({"order[createdAt]": "desc"})
        md_model.data = data
        download_id = md_model.id
        url = f"{md_model.api_url}/{download_type}/{md_model.id}"
    else:
        download_id = f"{md_model.id}-follows"
        url = f"{md_model.user_api_url}/follows/manga"
        cache_json = md_model.cache_json

    name_path = md_model.data["attributes"]
    md_model.params.update({"includes[]": ["manga"]})

    if download_type == "group":
        md_model.name = name_path["name"]
        md_model.params.update({"groups[]": md_model.id})
        md_model.chapter_limit = 100
    elif download_type == "user":
        md_model.name = name_path["username"]
        md_model.params.update({"uploader": md_model.id})
        md_model.chapter_limit = 100
    elif download_type == "list":
        owner = [u for u in md_model.data["relationships"] if u["type"] == "user"][0]
        owner = owner["attributes"]["username"]
        md_model.name = f"{owner}'s Custom List"
    else:
        owner = name_path["username"]
        md_model.name = f"{owner}'s Follows List"

    md_model.misc.download_message(0, download_type, md_model.name)
    chapters = cache_json.get("chapters", [])

    if not chapters:
        chapters = get_chapters(md_model, url)
        md_model.cache.save_cache(datetime.now(), download_id, md_model.data, chapters)
        md_model.wait()

    # Initalise json classes and make series folders
    bulk_json = BulkJson(md_model)
    md_model.bulk_json = bulk_json

    if not md_model.args.download_in_order:
        print(f"Getting each manga's data from the {download_type} chosen.")

        titles = {}
        for chapter in chapters:
            manga_id = [c["id"] for c in chapter["relationships"] if c["type"] == "manga"][0]
            if manga_id in titles:
                titles[manga_id]["chapters"].append(chapter)
            else:
                titles[manga_id] = {"mangaId": manga_id, "chapters": [chapter]}

        md_model.chapters_data = titles

        print("Finished getting each manga's data, downloading the chapters.")

        for title in titles:
            md_model.manga_download = True
            md_model.manga_id = titles[title]["mangaId"]

            manga_download(md_model)

            md_model.manga_download = False
            md_model.manga_data = {}
            md_model.wait(0)
    else:
        chapters_data = bulk_json.downloaded_ids
        chapters = md_model.filter.filter_chapters(chapters)
        download_chapters(md_model, chapters, chapters_data)

    md_model.misc.download_message(1, download_type, md_model.name)

    # Save the json
    await bulk_json.core(1)


# async def follows_download(md_model) -> None:
#     """Download logged in user follows."""
#     if not md_model.auth.successful_login:
#         raise NotLoggedInError('You need to be logged in to download your follows.')

#     download_type = md_model.download_type
#     response = md_model.api.request_data(f'{md_model.user_api_url}/me', **{"order[createdAt]": "desc"})
#     md_model.data = md_model.api.convert_to_json('follows-user', download_type, response)
#     md_model.wait()

#     md_model.id = md_model.data["id"]
#     md_model.cache_json = {"cache_date": datetime.now(), "data": md_model.data, "chapters": [], "covers": []}

#     bulk_download(md_model)


async def chapter_download(args: ProcessArgs, chapter_args_obj: MDArgs) -> None:
    """Get the chapter data for download."""
    # Connect to API and get chapter info
    chapter_id = chapter_args_obj.id
    download_type = chapter_args_obj.type
    chapter_cache_obj = CacheRead(args, cache_id=chapter_id, cache_type="chapter")

    refresh_cache = chapter_cache_obj.check_cache_time()
    chapter_data = chapter_cache_obj.cache.data

    if refresh_cache or not bool(chapter_data):
        chapter_response = await args._hondana_client.get_chapter(
            chapter_id, includes=hondana.query.ChapterIncludes(user=False)
        )
        chapter_cache_obj.save_cache(cache_time=datetime.now(), data=chapter_response)
    else:
        chapter_response = hondana.Chapter(args._hondana_client._http, chapter_data.copy())

    manga_cache_obj = CacheRead(args, cache_type="manga")
    if chapter_response.manga is None:
        manga_cache_obj._cache_id = chapter_response.manga_id
        manga_cache_obj.update_cache_obj()
        await chapter_response.get_parent_manga()
    else:
        manga_cache_obj._cache_id = chapter_response.manga_id
        manga_cache_obj.update_cache_obj()

    manga_cache_obj.save_cache(cache_time=datetime.now(), data=chapter_response.manga)
    manga_args_obj = MDArgs(id=chapter_response.manga_id, type="manga", data=chapter_response.manga, cache=manga_cache_obj)

    name = f"{chapter_response.manga.title}: Chapter {chapter_response.chapter}"

    # md_model.misc.download_message(0, download_type, name)

    chapter_args_obj.data = chapter_response
    chapter_args_obj.cache = chapter_cache_obj
    image_downloader_obj = ImageDownloader(args, manga_args_obj)
    await image_downloader_obj.chapter_downloader(chapter_args_obj)

    # md_model.misc.download_message(1, download_type, name)
