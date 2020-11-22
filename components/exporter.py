#!/usr/bin/python3
import html
import json
import os
import re
import sys
import zipfile
from pathlib import Path



class ExporterBase:

    def __init__(self, series_title, chapter_data):
        self.series_title = series_title
        self.chapter_data = chapter_data
        self.languages = self.getLangs()
        self.languages = self.languages["iso"]
        self.lang_code = chapter_data["language"]
        self.oneshot = self.oneshotChecker()
        self.chapter_regrex = re.compile(r'([0-9]+)\.([0-9]+)')
        self.name_regex = re.compile('[\\\\/:*?"<>|]')
        self.groups = self.groupNames()
        self.chapter_number = self.chapterNo()
        self.volume = self.volumeNo()
        self.language = self.langCode()
        self.prefix = self.prefixName()
        self.suffix = self.suffixName()
        self.folder_name = self.folderName()


    def getLangs(self):
        with open('languages.json', 'r') as file:
            languages = json.load(file)
        return languages


    def oneshotChecker(self):
        if self.chapter_data["title"].lower() == 'oneshot':
            return 1
        elif self.chapter_data["chapter"] == '' and self.chapter_data["volume"] == '' and self.chapter_data["title"] == '':
            return 1
        elif self.chapter_data["chapter"] == '' and self.chapter_data["volume"] == '':
            return 2
        else:
            return 0


    def chapterNo(self):
        chapter_number = self.chapter_data["chapter"]

        if self.oneshot in (1, 2):
            chapter_number = chapter_number.zfill(3)
        else:
            parts = chapter_number.split('.', 1)
            c = int(parts[0])
            chap_no = str(c).zfill(3)
            chap_prefix = 'c' if c < 1000 else 'd'
            chap_no = chap_no + '.' + parts[1] if len(parts) > 1 else chap_no
            chapter_number = chap_prefix + chap_no

        return chapter_number


    def langCode(self):
        if self.lang_code == 'gb':
            return ''
        else:
            return f' [{self.languages[self.lang_code]}]'

    
    def volumeNo(self):
        if self.chapter_data["volume"] == '' or self.oneshot in (1, 2):
            return ''
        else:
            return f' (v{self.chapter_data["volume"].zfill(2)})'


    def prefixName(self):
        return f'{self.series_title}{self.language} - {self.chapter_number}{self.volume}'


    def groupNames(self):
        return self.name_regex.sub('_', html.unescape(', '.join([g["name"] for g in self.chapter_data["groups"]])))


    def suffixName(self):
        if self.oneshot == 1:
            return f'[Oneshot] [{self.groups}]'
        elif self.oneshot == 2: 
            return f'[Oneshot] [{self.chapter_data["title"]}] [{self.groups}]'
        else:
            return f'[{self.groups}]'


    def folderName(self):
        return f'{self.prefix} {self.suffix}'


    def pageName(self, page_no, ext):
        return f'{self.prefix} - p{page_no:0>3} {self.suffix}.{ext}'



class ChapterSaver(ExporterBase):
    def __init__(self, series_title, chapter_data, destination, save_format, make_folder):
        super().__init__(series_title, chapter_data)
        self.destination = destination
        self.save_format = save_format
        self.path = Path(destination)
        self.make_folder = make_folder
        self.path.mkdir(parents=True, exist_ok=True)
        self.archive_path = os.path.join(destination, f'{self.folder_name}.{save_format}')
        self.folder_path = self.path.joinpath(self.folder_name)
        self.archive = self.checkZip()
        self.folder = None if self.make_folder == 'no' else self.makeFolder()


    def makeZip(self):
        try:
            return zipfile.ZipFile(self.archive_path, mode="a", compression=zipfile.ZIP_DEFLATED) 
        except zipfile.BadZipFile:
            sys.exit('Error creating archive')
        except PermissionError:
            raise PermissionError("The file is open by another process.")
        return


    def checkZip(self):
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


    def makeFolder(self):
        try:
            return self.folder_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            sys.exit('Error creating folder')
        return
    
    def imageCompress(self):
        self.archive.writestr(self.page_name, self.response)
        return


    def folderAdd(self):
        with open(self.folder_path.joinpath(self.page_name), 'wb') as file:
            file.write(self.response)
        return


    def checkImages(self):
        if self.page_name in self.archive.namelist():
            pass
        else:
            self.imageCompress()
        
        if self.folder is not None:
            if self.page_name in os.listdir(self.folder_path):
                pass
            else:
                self.folderAdd()
        return


    def addImage(self, response, page_no, ext):
        self.page_name = self.pageName(page_no, ext)
        self.response = response

        self.checkImages()
        return


    def close(self):
        self.archive.close()
        return
