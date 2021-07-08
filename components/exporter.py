#!/usr/bin/python3
import json
import os
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from .errors import MDownloaderError
from .languages import get_lang_iso
from .model import MDownloader



class ExporterBase:

    def __init__(self, md_model: MDownloader) -> None:
        self.md_model = md_model
        self.series_title = md_model.title
        self.orig_chapter_data = md_model.chapter_data
        self.chapter_id = md_model.chapter_data["data"]["id"]
        self.chapter_data = md_model.chapter_data["data"]["attributes"]
        self.relationships = md_model.chapter_data["relationships"]
        self.chapter_prefix = md_model.prefix
        self.oneshot = self.check_oneshot()
        self.groups = self.group_names()
        self.chapter_number = self.format_chapter_number()
        self.volume = self.format_volume_number()
        self.language = self.lang_code()
        self.prefix = self.prefix_name()
        self.suffix = self.suffix_name()
        self.folder_name = self.folder_name()

        self.add_data = md_model.args.save_chapter_data
        self.destination = md_model.route
        self.path = Path(md_model.route)
        self.path.mkdir(parents=True, exist_ok=True)

    def check_oneshot(self) -> int:
        """If the chapter is a oneshot.

        Returns:
            int: If the chapter is a oneshot or not.
        """
        if self.chapter_data["title"] is None:
            return 0
        elif self.chapter_data["title"].lower() == 'oneshot':
            return 1
        elif self.chapter_data["chapter"] == '' and (self.chapter_data["volume"] == '' or self.chapter_data["volume"] == '0') and self.chapter_data["title"] == '':
            return 1
        elif self.chapter_data["chapter"] == '' and (self.chapter_data["volume"] == '' or self.chapter_data["volume"] == '0'):
            return 2
        elif self.chapter_data["chapter"] == '' and self.chapter_data["volume"] != '' and (self.chapter_data["title"] != '' or self.chapter_data["title"] == ''):
            return 3
        return 0

    def format_chapter_number(self) -> str:
        """Format the chapter number into 3 digits long.

        Returns:
            str: The formatted chapter number.
        """
        if self.oneshot in (1, 2, 3):
            return '000'

        chapter_number = str(self.chapter_data["chapter"])

        if re.search(r'[\\\\/-:*?"<>|]', chapter_number):
            decimal = chapter_number.split('.', 1)
            parts = re.split(r'\D', decimal[0], 1)
            c = int(parts[0])
            parts = [i.zfill(3) for i in parts]
            chap_prefix = self.chapter_prefix if c < 1000 else (chr(ord(self.chapter_prefix) + 1))
            chap_no = '-'.join(parts) + '.' + decimal[1] if (len(decimal) > 1 and decimal[1] != '0') else '-'.join(parts)
        else:
            parts = chapter_number.split('.', 1)
            c = int(parts[0])
            chap_no = str(c).zfill(3)
            chap_prefix = self.chapter_prefix if c < 1000 else (chr(ord(self.chapter_prefix) + 1))
            chap_no = chap_no + '.' + parts[1] if (len(parts) > 1 and parts[1] != '0') else chap_no
        chapter_number = chap_prefix + chap_no

        return chapter_number

    def lang_code(self) -> str:
        """Ignore language code if in english.

        Returns:
            str: The formatted language.
        """
        if self.chapter_data["translatedLanguage"] == 'en':
            return ''
        return f' [{get_lang_iso(self.chapter_data["translatedLanguage"])}]'

    def format_volume_number(self) -> str:
        """Get the volume number if applicable.

        Returns:
            str: The formatted volume number.
        """
        volume_number = self.chapter_data["volume"]
        if volume_number is None or volume_number.lower() in ('0', 'none', 'null') or self.oneshot in (1, 2):
            return ''

        volume_number = str(volume_number)
        parts = volume_number.split('.', 1)
        v = int(parts[0])
        vol_no = str(v).zfill(2)
        volume_number = vol_no + '.' + parts[1] if (len(parts) > 1 and parts[1] != '0') else vol_no
        return f' (v{volume_number})'

    def prefix_name(self) -> str:
        """The formatted prefix name.

        Returns:
            str: The name prefix.
        """
        return f'{self.series_title}{self.language} - {self.chapter_number}{self.volume}'

    def group_names(self) -> str:
        """The chapter's groups.

        Returns:
            str: The names of the scanlation groups.
        """
        groups_relationship = [g for g in self.relationships if g["type"] == 'scanlation_group']
        group_names = []

        for group in groups_relationship:
            group_id = group["id"]
            group_data = group.get('attributes', {})
            cache_json = self.md_model.cache.load_cache(group_id)
            refresh_cache = self.md_model.cache.check_cache_time(cache_json)

            if not group_data:
                if self.md_model.debug: print('Calling api for group data from chapter download.')
                group_data = cache_json.get('data', {})

                if refresh_cache or not group_data:
                    group_response = self.md_model.api.request_data(f'{self.md_model.group_api_url}/{group_id}')
                    group_data = self.md_model.api.convert_to_json(group_id, 'chapter-group', group_response)
                    self.md_model.cache.save_cache(datetime.now(), group_id, group_data)

                group_data = group_data["data"]["attributes"]
            else:
                if refresh_cache:
                    cache_group_data = cache_json.get('data', {})
                    if cache_group_data:
                        cache_group_data = {"data": group, "relationships": cache_group_data.get('relationships', [])}
                    self.md_model.cache.save_cache(cache_json.get('cache_date', ''), download_id=group_id, data=cache_group_data, chapters=cache_json.get('chapters', []), covers=cache_json.get('covers', []))
            
            name = group_data["name"]
            group_names.append(name)

        if len(group_names) == 0:
            group_names.append('no group')

        return self.md_model.formatter.strip_illegal(', '.join(group_names))

    def suffix_name(self) -> str:
        """Formatting the groups as the suffix.

        Returns:
            str: The suffix of the file name.
        """
        chapter_title = self.chapter_data["title"]
        if chapter_title is None:
            chapter_title = ''
        chapter_title = f'{chapter_title[:31]}...' if len(chapter_title) > 30 else chapter_title
        title = f'[{self.md_model.formatter.strip_illegal(chapter_title)}] ' if len(chapter_title) > 0 else ''
        oneshot_prefix = '[Oneshot] '
        group_suffix = f'[{self.groups}]'

        if self.oneshot == 1:
            return f'{oneshot_prefix}{group_suffix}'
        elif self.oneshot == 2:
            return f'{oneshot_prefix}{title}{group_suffix}'
        elif self.oneshot == 3:
            return f'{title}{group_suffix}'
        return group_suffix

    def folder_name(self) -> str:
        """The final folder name combining the prefix and suffix for the archive/folder name

        Returns:
            str: The file name images to be saved to. 
        """
        return f'{self.prefix} {self.suffix}'

    def format_page_name(self, page_no: int, ext: str) -> str:
        """Each page name.

        Args:
            page_no (int): The image number.
            ext (str): The image extension.

        Returns:
            str: The formatted page name.
        """
        return f'{self.prefix} - p{page_no:0>3} {self.suffix}.{ext}'



class ArchiveExporter(ExporterBase):
    def __init__(self, md_model: MDownloader) -> None:
        super().__init__(md_model)

        self.archive_extension = md_model.args.archive_extension
        self.archive_path = os.path.join(self.destination, f'{self.folder_name}.{self.archive_extension}')
        self.archive = self.check_zip()
 
    def make_zip(self) -> zipfile.ZipFile:
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

    def check_zip(self) -> zipfile.ZipFile:
        """Check the zipfile to see if it is a duplicate or not.

        Returns:
            zipfile.ZipFile: A ZipFile object of the open archive. 
        """
        version_no = 1
        self.archive = self.make_zip()
        chapter_hash = self.archive.comment.decode().split('\n')[-1]
        to_add = f'{self.chapter_id}\n{self.chapter_data["title"]}\n{self.chapter_data["hash"]}'

        if chapter_hash == '' or chapter_hash == self.chapter_data["hash"]:
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
                    self.archive_path = os.path.join(self.destination, f'{self.folder_name}{{v{version_no}}}.{self.archive_extension}')
                    self.archive = self.make_zip()
                    chapter_hash = self.archive.comment.decode().split('\n')[-1]
                    if chapter_hash == '' or chapter_hash == self.chapter_data["hash"]:
                        break
                    else:
                        self.close()
                        version_no += 1
                else:
                    break

            self.archive.comment = to_add.encode()
            return self.archive

    def compress_image(self) -> None:
        """Add image to archive through the memory."""
        self.archive.writestr(self.page_name, self.response)

    def check_image(self) -> None:
        """Check if the image is in the archive, skip if it is."""
        if self.page_name not in self.archive.namelist():
            self.compress_image()

    def add_image(self, response: bytes, page_no: int, ext: str) -> None:
        """Format the image name then add to archive.

        Args:
            response (bytes): The image data.
            page_no (int): The image number.
            ext (str): The image extension.
        """
        self.page_name = self.format_page_name(page_no, ext)
        self.response = response

        self.check_image()

    def close(self, status: bool=0) -> None:
        """Close the archive and save the chapter data.

        Args:
            status (bool, optional): The type of archive closing. Defaults to 0.
        """
        if not status:
            # Add the chapter data json to the archive
            if self.add_data and f'{self.chapter_id}.json' not in self.archive.namelist():
                self.archive.writestr(f'{self.chapter_id}.json', json.dumps(self.orig_chapter_data, indent=4, ensure_ascii=False))

        self.archive.close()

        if status:
            os.remove(self.archive_path)



class FolderExporter(ExporterBase):
    def __init__(self, md_model: MDownloader) -> None:
        super().__init__(md_model)

        self.check_folder()

    def make_folder(self) -> bool:
        """Make the folder.

        Raises:
            MDownloaderError: Folder was unable to be made.

        Returns:
            bool: If the folder existed before or not.
        """
        try:
            if os.path.exists(self.folder_path):
                return 1
            else:
                self.folder_path.mkdir(parents=True, exist_ok=True)
                return 0
        except OSError:
            raise MDownloaderError('Error creating folder')

    def check_folder(self) -> None:
        """Check if the image is in the folder, skip if it is"""
        self.folder_path = self.path.joinpath(self.folder_name)
        self.make_folder()
        # version_no = 1
        # if self.makeFolder():
        #     if f'{self.chapter_id}.json' not in os.listdir(self.folder_path):
        #             print('The archive with the same chapter number and groups exists, but not the same chapter hash, making a different archive...')
        #         version_no += 1
        #         while True:
        #             self.folder_path = self.path.joinpath(f'{self.folder_name}{{v{version_no}}}')
        #             if self.makeFolder():
        #                 if f'{self.chapter_id}.json' not in os.listdir(self.folder_path):
        #                     break
        #                 else:
        #                     continue
        #             else:
        #                 break

    def add_to_folder(self) -> None:
        """Add images to the folder."""
        with open(self.folder_path.joinpath(self.page_name), 'wb') as file:
            file.write(self.response)

    def check_image(self) -> None:
        """Check if images are in the folder."""
        if self.page_name not in os.listdir(self.folder_path):
            self.add_to_folder()

    def add_image(self, response: bytes, page_no: int, ext: str) -> None:
        """Format the image name then add to archive.

        Args:
            response (bytes): The image data.
            page_no (int): The image number.
            ext (str): The image extension.
        """
        self.page_name = self.format_page_name(page_no, ext)
        self.response = response

        self.check_image()

    def close(self, status: bool=0) -> None:
        """Close the archive and save the chapter data.

        Args:
            status (bool, optional): The type of archive closing. Defaults to 0.
        """
        if not status:
            # Add the chapter data json to the folder
            if self.add_data and f'{self.chapter_id}.json' not in os.listdir(self.folder_path):
                with open(self.folder_path.joinpath(f'{self.chapter_id}.json'), 'w') as json_file:
                    json.dump(self.orig_chapter_data, json_file, indent=4, ensure_ascii=False)
        else:
            shutil.rmtree(self.folder_path)
