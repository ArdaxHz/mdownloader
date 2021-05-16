#!/usr/bin/python3
import html
import json
import os
import re
import shutil
import zipfile
from pathlib import Path

from .constants import ImpVar
from .errors import MDownloaderError
from .languages import getLangIso

re_regrex = re.compile(ImpVar.REGEX)



class ExporterBase:

    def __init__(self, md_model) -> None:
        self.md_model = md_model
        self.series_title = md_model.title
        self.chapter_id = md_model.chapter_data["data"]["id"]
        self.chapter_data = md_model.chapter_data["data"]["attributes"]
        self.relationships = md_model.chapter_data["relationships"]
        self.chapter_prefix = md_model.prefix
        self.oneshot = self.oneshotChecker()
        self.groups = self.groupNames()
        self.chapter_number = self.chapterNo()
        self.volume = self.volumeNo()
        self.language = self.langCode()
        self.prefix = self.prefixName()
        self.suffix = self.suffixName()
        self.folder_name = self.folderName()

    def oneshotChecker(self) -> int:
        """If the chapter is a oneshot.

        Returns:
            int: If the chapter is a oneshot or not.
        """
        if self.chapter_data["title"].lower() == 'oneshot':
            return 1
        elif self.chapter_data["chapter"] == '' and (self.chapter_data["volume"] == '' or self.chapter_data["volume"] == '0') and self.chapter_data["title"] == '':
            return 1
        elif self.chapter_data["chapter"] == '' and (self.chapter_data["volume"] == '' or self.chapter_data["volume"] == '0'):
            return 2
        elif self.chapter_data["chapter"] == '' and self.chapter_data["volume"] != '' and (self.chapter_data["title"] != '' or self.chapter_data["title"] == ''):
            return 3
        else:
            return 0

    def chapterNo(self) -> str:
        """Format the chapter number into 3 digits long.

        Returns:
            str: The formatted chapter number.
        """
        chapter_number = str(self.chapter_data["chapter"])

        if self.oneshot in (1, 2, 3):
            return chapter_number.zfill(3)

        if re.search(r'[\\\\/-:*?"<>|]', chapter_number):
            decimal = chapter_number.split('.', 1)
            parts = re.split(r'\D', decimal[0], 1)
            c = int(parts[0])
            parts = [i.zfill(3) for i in parts]
            chap_prefix = self.chapter_prefix if c < 1000 else (chr(ord(self.chapter_prefix) + 1))
            chap_no = '-'.join(parts) + '.' + decimal[1] if len(decimal) > 1 else '-'.join(parts)
        else:
            parts = chapter_number.split('.', 1)
            c = int(parts[0])
            chap_no = str(c).zfill(3)
            chap_prefix = self.chapter_prefix if c < 1000 else (chr(ord(self.chapter_prefix) + 1))
            chap_no = chap_no + '.' + parts[1] if len(parts) > 1 else chap_no
        chapter_number = chap_prefix + chap_no

        return chapter_number

    def langCode(self) -> str:
        """Ignore language code if in english.

        Returns:
            str: The formatted language.
        """
        if self.chapter_data["translatedLanguage"] == 'en':
            return ''
        return f' [{getLangIso(self.chapter_data["translatedLanguage"])}]'

    def volumeNo(self) -> str:
        """Get the volume number if applicable.

        Returns:
            str: The formatted volume number.
        """
        volume_number = self.chapter_data["volume"]
        if volume_number is None or self.oneshot in (1, 2) or volume_number != '0':
            return ''

        volume_number = str(volume_number)
        parts = volume_number.split('.', 1)
        v = int(parts[0])
        vol_no = str(v).zfill(2)
        volume_number = vol_no + '.' + parts[1] if len(parts) > 1 else vol_no
        return f' (v{volume_number})'

    # The formatted prefix name
    def prefixName(self) -> str:
        return f'{self.series_title}{self.language} - {self.chapter_number}{self.volume}'

    # The chapter's groups
    def groupNames(self) -> str:
        group_ids = [g["id"] for g in self.relationships if g["type"] == 'scanlation_group']
        groups = []

        for group_id in group_ids:
            group_response = self.md_model.requestData(group_id, 'group')
            group_data = self.md_model.convertJson(group_id, 'chapter-group', group_response)
            name = group_data["data"]["attributes"]["name"]
            groups.append(name)

        return re_regrex.sub('_', html.unescape(', '.join(groups)))

    def suffixName(self) -> str:
        """Formatting the groups as the suffix.

        Returns:
            str: The suffix of the file name.
        """
        chapter_title = f'{self.chapter_data["title"][:31]}...' if len(self.chapter_data["title"]) > 30 else self.chapter_data["title"]
        title = f'[{re_regrex.sub("_", html.unescape(chapter_title))}] ' if len(chapter_title) > 0 else ''
        oneshot_prefix = '[Oneshot] '
        group_suffix = f'[{self.groups}]'

        if self.oneshot == 1:
            return f'{oneshot_prefix}{group_suffix}'
        elif self.oneshot == 2:
            return f'{oneshot_prefix}{title}{group_suffix}'
        elif self.oneshot == 3:
            return f'{title}{group_suffix}'
        return group_suffix

    def folderName(self) -> str:
        """The final folder name combining the prefix and suffix for the archive/folder name

        Returns:
            str: The file name images to be saved to.
        """
        return f'{self.prefix} {self.suffix}'

    def pageName(self, page_no: int, ext: str) -> str:
        """Each page name.

        Args:
            page_no (int): The image number.
            ext (str): The image extension.

        Returns:
            str: The page name downloaded.
        """
        return f'{self.prefix} - p{page_no:0>3} {self.suffix}.{ext}'



class ArchiveExporter(ExporterBase):
    def __init__(self, md_model) -> None:
        super().__init__(md_model)
        
        self.add_data = md_model.add_data
        self.destination = md_model.route
        self.save_format = md_model.save_format
        self.path = Path(md_model.route)
        self.path.mkdir(parents=True, exist_ok=True)
        self.archive_path = os.path.join(self.destination, f'{self.folder_name}.{self.save_format}')
        self.archive = self.checkZip()
 
    def makeZip(self) -> zipfile.ZipFile:
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

    def checkZip(self) -> zipfile.ZipFile:
        """Check the zipfile to see if it is a duplicate or not.

        Returns:
            zipfile.ZipFile: A ZipFile object of the open archive. 
        """
        version_no = 1
        self.archive = self.makeZip()
        chapter_hash = self.archive.comment.decode().split('\n')[-1]
        to_add = f'{self.chapter_id}\n{self.chapter_data["title"]}\n{self.chapter_data["hash"]}'

        if chapter_hash == '' or chapter_hash == self.chapter_data["hash"]:
            if self.archive.comment.decode() == to_add:
                pass
            else:
                self.archive.comment = to_add.encode()

            return self.archive
        else:
            self.close()
            version_no += 1

            print('The archive with the same chapter number and groups exists, but not the same chapter hash, making a different archive...')

            # Loop until an available archive name that isn't taken is available
            while True:
                if os.path.exists(self.archive_path):
                    self.archive_path = os.path.join(self.destination, f'{self.folder_name}{{v{version_no}}}.{self.save_format}')
                    self.archive = self.makeZip()
                    chapter_hash = self.archive.comment.decode().split('\n')[-1]
                    if chapter_hash == '' or chapter_hash == self.chapter_data["hash"]:
                        if self.archive.comment.decode() == to_add:
                            pass
                        else:
                            self.archive.comment = to_add.encode()
                        break
                    else:
                        self.close()
                        version_no += 1
                        continue
                else:
                    break

            self.archive.comment = to_add.encode()
            return self.archive

    def imageCompress(self) -> None:
        """Add image to archive through the memory."""
        self.archive.writestr(self.page_name, self.response)

    def checkImages(self) -> None:
        """Check if the image is in the archive, skip if it is."""
        if self.page_name not in self.archive.namelist():
            self.imageCompress()

    def addImage(self, response: bytes, page_no: int, ext: str) -> None:
        """Format the image name then add to archive.

        Args:
            response (bytes): The image data.
            page_no (int): The image number.
            ext (str): The image extension.
        """
        self.page_name = self.pageName(page_no, ext)
        self.response = response

        self.checkImages()

    def close(self, status: bool=0) -> None:
        """Close the archive and save the chapter data.

        Args:
            status (bool, optional): The type of archive closing. Defaults to 0.
        """
        if not status:
            # Add the chapter data json to the archive
            if self.add_data and f'{self.chapter_id}.json' not in self.archive.namelist():
                self.archive.writestr(f'{self.chapter_id}.json', json.dumps(self.chapter_data, indent=4, ensure_ascii=False))

        self.archive.close()

        if status:
            os.remove(self.archive_path)



class FolderExporter(ExporterBase):
    def __init__(self, md_model) -> None:
        super().__init__(md_model.title, md_model.chapter_data, md_model.chapter_prefix)

        self.add_data = md_model.add_data
        self.path = Path(md_model.route)
        self.path.mkdir(parents=True, exist_ok=True)
        self.checkFolder()

    def makeFolder(self) -> bool:
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

    def checkFolder(self) -> None:
        """Check if the image is in the folder, skip if it is"""
        self.folder_path = self.path.joinpath(self.folder_name)
        self.makeFolder()
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

    def folderAdd(self) -> None:
        """Add images to the folder."""
        with open(self.folder_path.joinpath(self.page_name), 'wb') as file:
            file.write(self.response)

    def checkImages(self) -> None:
        """Check if images are in the folder."""
        if self.page_name not in os.listdir(self.folder_path):
            self.folderAdd()

    def addImage(self, response: bytes, page_no: int, ext: str) -> None:
        """Format the image name then add to archive.

        Args:
            response (bytes): The image data.
            page_no (int): The image number.
            ext (str): The image extension.
        """
        self.page_name = self.pageName(page_no, ext)
        self.response = response

        self.checkImages()

    def close(self, status: bool=0) -> None:
        """Close the archive and save the chapter data.

        Args:
            status (bool, optional): The type of archive closing. Defaults to 0.
        """
        if not status:
            # Add the chapter data json to the folder
            if self.add_data and f'{self.chapter_id}.json' not in os.listdir(self.folder_path):
                with open(self.folder_path.joinpath(f'{self.chapter_id}.json'), 'w') as json_file:
                    json.dump(self.chapter_data, json_file, indent=4, ensure_ascii=False)
        else:
            shutil.rmtree(self.folder_path)
