#!/usr/bin/python3
from pathlib import Path
from typing import Dict, Union

import hondana

from .args import ProcessArgs, MDArgs
from .downloader import chapter_download, manga_download
from .constants import ImpVar
from .errors import MDownloaderError

api_message = ImpVar.API_MESSAGE


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
            await manga_download(self.args, to_download)
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
