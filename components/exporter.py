#!/usr/bin/python3
import html
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

from .constants import REGEX
from .languages import languages_iso

re_regrex = re.compile(REGEX)



class ExporterBase:

    def __init__(self, series_title: str, chapter_data: dict, chapter_prefix: str):
        self.series_title = series_title
        self.chapter_data = chapter_data
        self.chapter_id = chapter_data["id"]
        self.chapter_prefix = chapter_prefix
        self.oneshot = self.oneshotChecker()
        self.groups = self.groupNames()
        self.chapter_number = self.chapterNo()
        self.volume = self.volumeNo()
        self.language = self.langCode()
        self.prefix = self.prefixName()
        self.suffix = self.suffixName()
        self.folder_name = self.folderName()


    # If oneshot, add to file name
    def oneshotChecker(self) -> int:
        if self.chapter_data["title"].lower() == 'oneshot':
            return 1
        elif self.chapter_data["chapter"] == '' and self.chapter_data["volume"] == '' and self.chapter_data["title"] == '':
            return 1
        elif self.chapter_data["chapter"] == '' and self.chapter_data["volume"] == '':
            return 2
        elif self.chapter_data["chapter"] == '' and self.chapter_data["volume"] != '' and (self.chapter_data["title"] != '' or self.chapter_data["title"] == ''):
            return 3
        else:
            return 0


    # Format the chapter number
    def chapterNo(self) -> str:
        chapter_number = self.chapter_data["chapter"]

        if self.oneshot in (1, 2, 3):
            chapter_number = chapter_number.zfill(3)
        else:
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


    # Ignore language code if in english
    def langCode(self) -> str:
        if self.chapter_data["language"] == 'gb':
            return ''
        else:
            return f' [{languages_iso.get(self.chapter_data["language"], "N/A")}]'


    # Get the volume number if applicable
    def volumeNo(self) -> str:
        volume_number = self.chapter_data["volume"]

        if volume_number == '' or self.oneshot in (1, 2):
            return ''
        else:
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
        return re_regrex.sub('_', html.unescape(', '.join([g["name"] for g in self.chapter_data["groups"]])))


    # Formatting the groups as the suffix
    def suffixName(self) -> str:
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
        else:
            return group_suffix


    # The final folder name combining the prefix and suffix for the archive/folder name
    def folderName(self) -> str:
        return f'{self.prefix} {self.suffix}'


    # Each page name
    def pageName(self, page_no: int, ext: str) -> str:
        return f'{self.prefix} - p{page_no:0>3} {self.suffix}.{ext}'



class ArchiveExporter(ExporterBase):
    def __init__(
            self,
            series_title: str,
            chapter_data: dict,
            destination: str,
            chapter_prefix: str,
            add_data: bool,
            save_format: bool):
        super().__init__(series_title, chapter_data, chapter_prefix)
        
        self.add_data = add_data
        self.destination = destination
        self.save_format = save_format
        self.path = Path(destination)
        self.path.mkdir(parents=True, exist_ok=True)
        self.archive_path = os.path.join(destination, f'{self.folder_name}.{save_format}')
        self.archive = self.checkZip()
 

    # Make a zipfile, if it exists, open it instead
    def makeZip(self) -> zipfile.ZipFile:
        try:
            return zipfile.ZipFile(self.archive_path, mode="a", compression=zipfile.ZIP_DEFLATED) 
        except zipfile.BadZipFile:
            sys.exit('Error creating archive')
        except PermissionError:
            raise PermissionError("The file is open by another process.")


    # Check the zipfile to see if it is a duplicate or not
    def checkZip(self) -> zipfile.ZipFile:
        version_no = 1
        self.archive = self.makeZip()
        chapter_hash = self.archive.comment.decode().split('\n')[-1]
        to_add = f'{self.chapter_data["id"]}\n{self.chapter_data["title"]}\n{self.chapter_data["hash"]}'

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
    

    # Add images to the archive
    def imageCompress(self):
        self.archive.writestr(self.page_name, self.response)
        return


    # Check if the image is in the archive, skip if it is
    def checkImages(self):
        if self.page_name not in self.archive.namelist():
            self.imageCompress()
        return


    # Format the image name then add to archive
    def addImage(self, response: bytes, page_no: int, ext: str):
        self.page_name = self.pageName(page_no, ext)
        self.response = response

        self.checkImages()
        return


    # Close the archive
    def close(self, status: bool=0):
        if not status:
            # Add the chapter data json to the archive
            if self.add_data and f'{self.chapter_id}.json' not in self.archive.namelist():
                self.archive.writestr(f'{self.chapter_id}.json', json.dumps(self.chapter_data, indent=4, ensure_ascii=False))

        self.archive.close()

        if status:
            os.remove(self.archive_path)
        return



class FolderExporter(ExporterBase):
    def __init__(
            self,
            series_title: str,
            chapter_data: dict,
            destination: str,
            chapter_prefix: str,
            add_data: bool):
        super().__init__(series_title, chapter_data, chapter_prefix)

        self.add_data = add_data
        self.path = Path(destination)
        self.path.mkdir(parents=True, exist_ok=True)
        self.checkFolder()


    # Make the folder
    def makeFolder(self) -> bool:
        try:
            if os.path.exists(self.folder_path):
                return 1
            else:
                self.folder_path.mkdir(parents=True, exist_ok=True)
                return 0
        except OSError:
            sys.exit('Error creating folder')


    # Check if the image is in the folder, skip if it is
    def checkFolder(self):
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
        return


    # Add images to the folder
    def folderAdd(self):
        with open(self.folder_path.joinpath(self.page_name), 'wb') as file:
            file.write(self.response)
        return


    # Check if images are in the folder
    def checkImages(self):
        if self.page_name not in os.listdir(self.folder_path):
            self.folderAdd()
        return


    # Format the image name then add to folder
    def addImage(self, response: bytes, page_no: int, ext: str):
        self.page_name = self.pageName(page_no, ext)
        self.response = response

        self.checkImages()
        return


    # Save chapter data to the folder
    def close(self, status: bool=0):
        if not status:
            # Add the chapter data json to the folder
            if self.add_data and f'{self.chapter_id}.json' not in os.listdir(self.folder_path):
                with open(self.folder_path.joinpath(f'{self.chapter_id}.json'), 'w') as json_file:
                    json.dump(self.chapter_data, json_file, indent=4, ensure_ascii=False)
        else:
            shutil.rmtree(self.folder_path)
        return
