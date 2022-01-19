#!/usr/bin/python3
import asyncio
import html
import json
import os
import re
import shutil
from typing import TYPE_CHECKING, List, Optional
import zipfile
from datetime import datetime
from pathlib import Path

import hondana

from .cache import CacheRead
from .constants import ImpVar
from .errors import MDownloaderError
from .languages import get_lang_iso

if TYPE_CHECKING:
    from .image_downloader import ImageDownloader
    from .main import ProcessArgs, MDArgs



class ExporterBase:

    def __init__(self, **kwargs) -> None:
        self._args: 'ProcessArgs' = kwargs["args"]
        self._chapter_args_obj: 'MDArgs' = kwargs["chapter_args_obj"]
        self._at_home_data: hondana.ChapterAtHome = kwargs["at_home_data"]
        self._chapter_obj: hondana.Chapter = self._chapter_args_obj.data
        self._series_title: str = kwargs["manga_title"]
        self._download_path: Path = kwargs["download_path"]

        self.chapter_prefix = 'c'
        self.naming_scheme = self._args.naming_scheme
        self._process_data()
        self.is_oneshot = self._check_oneshot()
        self.chapter = self._format_chapter_number()
        self.volume = self._format_volume_number()
        self.language = self._format_language()
        self.groups = self.get_groups()
        self.prefix = self._prefix_name()
        self.suffix = self._suffix_name()
        self.folder_name = self._folder_name()

        self.add_data = self._args.save_chapter_data

    def _strip_illegal_characters(self, name: str) -> str:
        """Remove illegal characters from the specified name."""
        return re.sub(ImpVar.CHARA_REGEX, '_', html.unescape(name)).rstrip(' .')

    def _process_data(self):
        """Convert the chapter data into a more readable format."""
        self._chapter_number = self._chapter_obj.chapter
        self._volume_number = self._chapter_obj.volume
        self._chapter_title = self._chapter_obj.title

        if self._chapter_number is None or str(self._chapter_number).lower() in ('', 'none'):
            self._chapter_number = None
        if self._volume_number is None or str(self._volume_number).lower() in ('', '0', 'none'):
            self._volume_number = None
        if self._chapter_title is None or str(self._chapter_title).lower() in ('', 'none', 'oneshot'):
            self._chapter_title = None

    def _check_oneshot(self) -> int:
        """Checks if the chapter is a oneshot."""
        if self._chapter_number is None and self._volume_number is None and self._chapter_title is None:
            return 1
        elif self._chapter_number is None and self._volume_number is None:
            return 2
        elif self._chapter_number == '0' and self._chapter_title is None:
            return 1
        return 0

    def _format_chapter_number(self) -> str:
        """Format the chapter number into 3 digits long."""
        if self.is_oneshot in (1, 2):
            return '000'

        chapter_number = str(self._chapter_number)

        decimal = chapter_number.split('.', 1)
        if len(decimal) == 1:
            decimal = chapter_number.split(',', 1)

        parts = re.split(r'\D', decimal[0], 1)
        c = int(parts[0])
        parts = [i.zfill(3) for i in parts]
        chap_prefix = self.chapter_prefix if c < 1000 else (chr(ord(self.chapter_prefix) + 1))
        chap_no = '-'.join(parts) + '.' + decimal[1] if (len(decimal) > 1 and decimal[1] != '0') else '-'.join(parts)

        chapter_number = chap_prefix + chap_no
        return chapter_number

    def _format_language(self) -> str:
        """Gets the language code to use and ignores the language code if its english."""
        if self._chapter_obj.translated_language == 'en':
            return ''
        return f' [{get_lang_iso(self._chapter_obj.translated_language)}]'

    def _format_volume_number(self) -> str:
        """Get the volume number if applicable."""
        if self._volume_number is None:
            return ''

        volume_number = str(self._volume_number)
        parts = volume_number.split('.', 1)
        v = int(parts[0])
        vol_no = str(v).zfill(2)
        volume_number = vol_no + '.' + parts[1] if (len(parts) > 1 and parts[1] != '0') else vol_no
        return f' (v{volume_number})'

    def _prefix_name(self) -> str:
        """The formatted prefix name."""
        return f'{self._series_title}{self.language} - {self.chapter}{self.volume}'

    def get_groups(self) -> str:
        """The scanlation groups that worked on the chapter."""
        _group_ids = [g["id"] for g in self._chapter_obj._relationships if g["type"] == 'scanlation_group']
        groups = self._chapter_obj.scanlator_groups
        group_names: List[str] = []
        _groups_types: List[hondana.ScanlatorGroup] = []

        if not groups:
            for _group_id in _group_ids:
                group_cache_obj = CacheRead(self._args, cache_id=_group_id, cache_type='group')
                refresh_cache = group_cache_obj.check_cache_time()
                if refresh_cache or not bool(group_cache_obj.cache.data):
                    group_response_coro = asyncio.create_task(self._args._hondana_client.get_scanlation_group(_group_id))
                    try:
                        group_response = group_response_coro.set_result()
                    except (asyncio.InvalidStateError, asyncio.CancelledError):
                        pass
                    group_cache_obj.save_cache(cache_time=datetime.now(), data=group_response_coro.res)
                else:
                    group_response = hondana.ScanlatorGroup(self._args._hondana_client._http, group_cache_obj.cache.data.copy())

                _groups_types.append(group_response)
                group_names.append(group_response.name)
        else:
            group_names = [g.name for g in groups]

        if len(group_names) == 0:
            group_names.append('No Group')

        if _groups_types:
            self._chapter_obj.scanlator_groups = _groups_types

        return self._strip_illegal_characters(', '.join(group_names))

    def _suffix_name(self) -> str:
        """Formats the groups as the suffix of the file name."""
        chapter_title = self._chapter_title or ''

        chapter_title = f'{chapter_title[:21]}...' if len(chapter_title) > 30 else chapter_title
        title = f'[{self._strip_illegal_characters(chapter_title)}] ' if len(chapter_title) > 0 else ''
        oneshot_prefix = '[Oneshot] '
        group_suffix = f'[{self.groups}]'
        is_oneshot = self.is_oneshot

        if is_oneshot == 1:
            return f'{oneshot_prefix}{group_suffix}'
        elif is_oneshot == 2:
            return f'{oneshot_prefix}{title}{group_suffix}'
        return group_suffix

    def _folder_name(self) -> str:
        """The folder or archive name images are saved to."""
        if self.naming_scheme == 'default':
            return f'{self.prefix} {self.suffix}'
        elif self.naming_scheme == 'number':
            name = self._chapter_number
            if self._chapter_number is None:
                name = '0'
            return f'Chapter {name}'
        elif self.naming_scheme == 'original':
            return f'{self._chapter_obj.id}'

    def _format_page_name(self, page_no: int, ext: str, orig_name: Optional[str]=None) -> str:
        """Each page name.

        Args:
            page_no (int): The image number.
            ext (str): The image extension.
            orig_name (str): The original image name.

        Returns:
            str: The formatted page name.
        """
        if self.naming_scheme == 'default' or orig_name is None:
            return f'{self.prefix} - p{page_no:0>3} {self.suffix}.{ext}'
        elif self.naming_scheme == 'number':
            return f'{page_no:0>3}.{ext}'
        elif self.naming_scheme == 'original':
            return f'{orig_name}'



class ArchiveExporter(ExporterBase):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.archive_extension = self._args.archive_extension
        self.archive_path = self._get_file_path(self.folder_name)
        self.archive = self._check_zip()

    def _get_file_path(self, name: str) -> Path:
        return self._download_path.joinpath(name).with_suffix(f'.{self.archive_extension}')

    def _make_zip(self) -> zipfile.ZipFile:
        """Make a zipfile, if it exists, open it instead.

        Raises:
            MDownloaderError: Archive was unable to be made.
            MDownloaderError: The archive was opened by an external program.

        Returns:
            zipfile.ZipFile: A ZipFile object of the open archive.
        """
        try:
            return zipfile.ZipFile(self.archive_path, mode="a", compression=zipfile.ZIP_DEFLATED)
        except zipfile.BadZipFile:
            raise MDownloaderError('Error creating archive')
        except PermissionError:
            raise MDownloaderError("The file is open by another process.")

    def _check_zip(self) -> zipfile.ZipFile:
        """Check if the zipfile is a duplicate."""
        version_no = 1
        self.archive = self._make_zip()
        chapter_hash = self.archive.comment.decode().split('\n')[-1]
        to_add = f'{self._chapter_obj.id}\n{self._chapter_obj.title}\n{self._at_home_data.hash}'

        if chapter_hash == '' or chapter_hash == self._at_home_data.hash:
            if self.archive.comment.decode() != to_add:
                self.archive.comment = to_add.encode()
            return self.archive
        else:
            self.close()
            version_no += 1

            print('The archive with the same chapter number and groups exists, but not the same chapter hash, making a different archive...')

            # Loop until an available archive name that isn't taken is available
            while True:
                if os.path.exists(self.archive_path):
                    self.archive_path = self._get_file_path(f'{self.folder_name}{{v{version_no}}}')
                    self.archive = self._make_zip()
                    chapter_hash = self.archive.comment.decode().split('\n')[-1]
                    if chapter_hash == '' or chapter_hash == self._at_home_data.hash:
                        break
                    else:
                        self.close()
                        version_no += 1
                else:
                    break

            self.archive.comment = to_add.encode()
            return self.archive

    def _compress_image(self) -> None:
        """Add image to archive through the memory."""
        self.archive.writestr(self.page_name, self.response)

    def _check_image(self) -> None:
        """Check if the image is in the archive, skip if it is."""
        if self.page_name not in self.archive.namelist():
            self._compress_image()

    def add_image(self, *, response: bytes, page_no: int, ext: str, orig_name: str) -> None:
        """Format the image name then add to archive.

        Args:
            response (bytes): The image data.
            page_no (int): The image number.
            ext (str): The image extension.
            orig_name (str): The original image name.
        """
        self.page_name = self._format_page_name(page_no, ext, orig_name)
        self.response = response

        self._check_image()

    def close(self, status: int=0) -> None:
        """Close the archive and save the chapter data.

        Args:
            status (int, optional): The type of archive closing. Defaults to 0. 0 doesnt't delete, 1 deletes if empty, 2 deletes regardless.
        """
        pages = self.archive.namelist()

        if status == 0:
            # Add the chapter data json to the archive
            if self.add_data and f'{self._chapter_obj.id}.json' not in self.archive.namelist():
                self.archive.writestr(f'{self._chapter_obj.id}.json', json.dumps(self._chapter_args_obj.cache.cache.data, indent=4, ensure_ascii=False))

        self.archive.close()

        if status in (1, 2):
            if status == 2 or (status == 1 and not pages):
                os.remove(self.archive_path)



class FolderExporter(ExporterBase):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._folder_path = self._download_path.joinpath(self.folder_name)
        self.check_folder()

    def _make_folder(self) -> bool:
        """Make the folder.

        Raises:
            MDownloaderError: Folder was unable to be made.

        Returns:
            bool: If the folder existed before or not.
        """
        try:
            if self._folder_path.exists():
                return True
            else:
                self._folder_path.mkdir(parents=True, exist_ok=True)
                return False
        except OSError:
            raise MDownloaderError('Error creating folder')

    def check_folder(self) -> None:
        """Check if the image is in the folder, skip if it is"""
        
        self._make_folder()
        # version_no = 1
        # if self._make_folder():
        #     if f'{self._chapter_obj.id}.json' not in os.listdir(self._folder_path):
        #             print('The archive with the same chapter number and groups exists, but not the same chapter hash, making a different archive...')
        #         version_no += 1
        #         while True:
        #             self._folder_path = self._download_path.joinpath(f'{self.folder_name}{{v{version_no}}}')
        #             if self._make_folder():
        #                 if f'{self._chapter_obj.id}.json' not in os.listdir(self._folder_path):
        #                     break
        #                 else:
        #                     continue
        #             else:
        #                 break

    def _add_to_folder(self) -> None:
        """Add images to the folder."""
        with open(self._folder_path.joinpath(self.page_name), 'wb') as file:
            file.write(self.response)

    def _check_image(self) -> None:
        """Check if images are in the folder."""
        if self.page_name not in os.listdir(self._folder_path):
            self._add_to_folder()

    def add_image(self, *, response: bytes, page_no: int, ext: str, orig_name: Optional[str]=None) -> None:
        """Format the image name then add to archive.

        Args:
            response (bytes): The image data.
            page_no (int): The image number.
            ext (str): The image extension.
            orig_name (str): The original image name.
        """
        self.page_name = self._format_page_name(page_no, ext, orig_name)
        self.response = response

        self._check_image()

    def close(self, status: int=0) -> None:
        """Close the archive and save the chapter data.

        Args:
            status (int, optional): The type of archive closing. Defaults to 0. 0 doesnt't delete, 1 deletes if empty, 2 deletes regardless.
        """
        _folder_files = os.listdir(self._folder_path)
        pages = [i for i in _folder_files if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

        if status == 0:
            # Add the chapter data json to the folder
            if self.add_data and f'{self._chapter_obj.id}.json' not in _folder_files:
                with open(self._folder_path.joinpath(self._chapter_obj.id).with_suffix('.json'), 'w') as json_file:
                    json.dump(self._chapter_args_obj.cache.cache.data, json_file, indent=4, ensure_ascii=False)
        else:
            if status == 2 or (status == 1 and not pages):
                shutil.rmtree(self._folder_path)
