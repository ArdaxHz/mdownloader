#!/usr/bin/python3
import argparse
import asyncio
import dataclasses
import getpass
import inspect
import os
from pathlib import Path
import re
from typing import TYPE_CHECKING, Dict, List, Literal, Optional, Tuple, Type, Union

import hondana

from .downloader import chapter_download
from .constants import ImpVar
from .errors import MDownloaderError

api_message = ImpVar.API_MESSAGE

if TYPE_CHECKING:
    from .cache import CacheRead


@dataclasses.dataclass()
class MDArgs:
    id: str
    type: str
    data: Optional[Union[hondana.Manga, hondana.Chapter, hondana.ScanlatorGroup, hondana.User, hondana.CustomList]] = dataclasses.field(default=None)
    cache: Optional['CacheRead'] = dataclasses.field(default=None)


class ProcessArgs:

    # __slots__ = (
    #     "debug",
    #     "force_refresh",
    #     "directory",
    #     "language",
    #     "archive_extension",
    #     "folder_download",
    #     "cover_download",
    #     "save_chapter_data",
    #     "range_download",
    #     "rename_files",
    #     "download_in_order",
    #     "search_manga",
    #     "manga_data"
    # )

    def __init__(self, unparsed_arguments, hondana_client: hondana.Client) -> None:
        self._hondana_client = hondana_client
        self._unparsed_arguments = unparsed_arguments
        self._arg_id = unparsed_arguments["id"]
        self._arg_type = unparsed_arguments["type"]
        self.debug = bool(unparsed_arguments["debug"])
        self.force_refresh = bool(unparsed_arguments["refresh"])
        self.directory: Path = Path(unparsed_arguments["directory"]) if unparsed_arguments["directory"] is not None else Path(ImpVar.DOWNLOAD_PATH)
        self.language = 'get_lang_md(unparsed_arguments["language"])'
        self.archive_extension = ImpVar.ARCHIVE_EXTENSION
        self._check_archive_extension(self.archive_extension)
        self.folder_download = bool(unparsed_arguments["folder"])
        self.cover_download = bool(unparsed_arguments["covers"])
        self.save_chapter_data = bool(unparsed_arguments["json"])
        self.range_download = bool(unparsed_arguments["range"])
        self.rename_files = bool(unparsed_arguments["rename"])
        self.download_in_order = bool(unparsed_arguments["order"])
        self.search_manga = bool(unparsed_arguments["search"])
        if unparsed_arguments["login"]:
            self.login()

        self.naming_scheme_options = Literal['default', 'original', 'number']
        self.naming_scheme = Literal['default']

    async def _check_legacy(self, download_id: str, download_type: str):
        if download_id.isdigit():
            return await self._map_single_legacy_uuid(download_type, item_ids=download_id)
        return download_id

    async def _map_single_legacy_uuid(self, download_id: int, download_type: str) -> str:
        download_id = int(download_id)
        response: hondana.LegacyMappingCollection = await self._hondana_client.legacy_id_mapping(download_type, item_ids=[download_id])
        return response.legacy_mappings[0].obj_new_id

    def check_url(self, url: str) -> Optional[re.Match[str]]:
        """Check if the url given is a MangaDex one."""
        return ImpVar.MD_URL.match(url)

    def parse_url(self, url: str) -> Tuple[str]:
        """Get the id and download type from url."""
        md_url_match = self.check_url(url)
        if md_url_match is None:
            raise MDownloaderError("That url is not recognised.")

        download_type_from_url = md_url_match.group(1)
        id_from_url = md_url_match.group(2)

        if download_type_from_url == 'title':
            download_type_from_url = 'manga'

        return id_from_url, download_type_from_url

    def check_uuid(self, series_id: str) -> bool:
        """Check if the id is a UUID."""
        return bool(re.match(ImpVar.UUID_REGEX, series_id))

    async def _parse_id(self, download_id: str, download_type: str) -> Tuple[Union[str, Path], Optional[str]]:
        to_return_id = None
        to_return_type = None
        if self.check_uuid(download_id):
            to_return_id = download_id
        elif download_id.isdigit():
            to_return_id = await self._map_single_legacy_uuid(download_id, download_type)
        elif ImpVar.URL_RE.search(download_id):
            parsed_id, parsed_type = self.parse_url(download_id)
            to_return_type = parsed_type
            to_return_id = await self._check_legacy(parsed_id, download_type)
        else:
            download_id_path = Path(download_id)
            if download_id_path.exists():
                to_return_id = download_id_path
            raise MDownloaderError("The id argument entered is not recognised.")
        return to_return_id, to_return_type

    def login(self):
        username = input('Your username: ')
        password = getpass.getpass(prompt='Your password: ', stream=None)
        self._hondana_client.login(username=username, password=password)

    def _check_archive_extension(self, archive_extension: str) -> str:
        """Check if the file extension is an accepted format. Default: cbz.

        Raises:
            MDownloaderError: The extension chosen isn't allowed.
        """
        if archive_extension not in ('zip', 'cbz'):
            raise MDownloaderError("This archive save format is not allowed.")

    async def find_manga(self, search_term: str) -> hondana.Manga:
        """Search for a manga by title."""
        manga_response = await self._hondana_client.manga_list(title=search_term)

        for count, manga in enumerate(manga_response.manga, start=1):
            print(f'{count}: {manga.title} | {manga.url}')

        try:
            manga_to_use_num = int(input(f'Choose a number matching the position of the manga you want to download: '))
        except ValueError:
            raise MDownloaderError("That's not a number.")

        if manga_to_use_num not in range(1, len(manga_response.manga) + 1):
            raise MDownloaderError("Not a valid option.")

        manga_to_use = manga_response.manga[manga_to_use_num - 1]
        return manga_to_use

    async def process_args(self, download_id: str=None, _download_type: str=None) -> MDArgs:
        if _download_type is None:
            _download_type = self._arg_type
        
        if self.search_manga:
            found_manga = await self.find_manga(download_id)
            return MDArgs(id=found_manga.id, type='manga', data=found_manga)

        download_id, download_type = await self._parse_id(str(download_id), _download_type)
        if download_type is None:
            download_type = _download_type
        return MDArgs(id=download_id, type=download_type)



class MDParser:

    def __init__(self, vargs: Dict[str, Union[str, bool]]) -> None:
        self.hondana_client = hondana.Client()
        self.args = ProcessArgs(vargs, self.hondana_client)

    async def _download_type(self, to_download: MDArgs) -> None:
        """Call the different functions depending on the type of download.

        Raises:
            MDownloaderError: The selected download type is not recognised.
        """
        if to_download.type == 'chapter':
            await chapter_download(self.args, to_download)
        elif to_download.type in ('title', 'manga'):
            manga_download(to_download)
        elif to_download.type in ('group', 'user', 'list'):
            bulk_download(to_download)
        # elif to_download.type in ('follows', 'feed'):
        #     md_model.type_id = 3
            follows_download(to_download)
        else:
            raise MDownloaderError('Please enter a manga/chapter/group/user/list id. For non-chapter downloads, you must add the argument "--type [manga|user|group|list]".')

    async def _file_downloader(self, filepath: MDArgs) -> None:
        """Download from file."""
        self.args.range_download = False
        filename = filepath.id
        unparsed_lines = []

        # Open file and read lines
        with open(filename, 'r') as bulk_file:
            unparsed_lines = [line.rstrip('\n') for line in bulk_file.readlines()]

        # md_model.misc.check_for_links(unparsed_lines, 'Empty file!')
        links = [line for line in unparsed_lines if len(line) > 0 and (self.check_url(line) or self.check_uuid(line) or line.isdigit())]
        # md_model.misc.check_for_links(links, 'No MangaDex link or id found')

        legacy_ids = [int(legacy) for legacy in links if legacy.isdigit()]
        new_download_ids = [x for x in links if int(x) not in legacy_ids]
        parsed = []

        for p in new_download_ids:
            parsed.append(self.args.process_args(p))

        legacy_response: hondana.LegacyMappingCollection = await self.hondana_client.legacy_id_mapping(self.args._arg_type, legacy_ids)

        for ids in legacy_response.legacy_mappings:
            parsed.append(self.args.process_args(ids.obj_new_id))

        # md_model.wait()

        print(api_message)
        for download in parsed:
            try:
                await self._download_type(download)
            except MDownloaderError as e:
                if e: print(e)

        print(f'All the ids in {filename} have been downloaded')

    async def main(self):
        args_obj = await self.args.process_args(self.args._arg_id, self.args._arg_type)

        if isinstance(args_obj.id, Path):
            await self._file_downloader(args_obj)
        else:
            await self._download_type(args_obj)    
