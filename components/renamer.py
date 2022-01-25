import html
import multiprocessing
import os
import re
import zipfile
from copy import copy
from pathlib import Path
from typing import Dict, List

from .constants import ImpVar


class DownloadedFilesRenamer:
    def __init__(self, *, manga_data: dict, manga_download_path: Path, downloads_root_path: Path) -> None:
        self._manga_data = manga_data
        self._manga_download_path = manga_download_path
        self._downloads_root_path = downloads_root_path
        self._manga_data_attrs = self._manga_data["attributes"]

        self._manga_id = self._manga_data["id"]
        self.main_manga_title = self._main_title(self._manga_data_attrs["title"])
        self.alt_titles = self._get_other_titles(self._manga_data_attrs["title"], self._manga_data_attrs["altTitles"])
        self.file_name_regex = re.compile(ImpVar.FILE_NAME_REGEX, re.IGNORECASE)

    def _main_title(self, title) -> str:
        title = title.get("en")
        key = next(iter(title))
        if title is None:
            title = title.get(self.main_manga_title["originalLanguage"], title[key])
        return title

    def _get_other_titles(self, title_dict: Dict[str, str], alt_titles: List[Dict[str, str]]) -> List[str]:
        manga_titles = list(title_dict.values())
        manga_titles.extend(
            [title_dict[key] for title_dict in alt_titles for key in title_dict if title_dict[key] != self.main_manga_title]
        )
        return manga_titles

    def _strip_illegal_characters(self, name: str) -> str:
        """Remove illegal characters from the specified name."""
        return re.sub(ImpVar.CHARA_REGEX, "_", html.unescape(name)).rstrip(" .")

    def check_downloaded_files(self):
        """Check if folders using other manga titles exist."""
        main_title: str = copy(self.main_manga_title)
        available_titles = [
            self._strip_illegal_characters(x)
            for x in self.alt_titles
            if self._strip_illegal_characters(x)
            in [
                route
                for route in os.listdir(self._downloads_root_path)
                if os.path.isdir(os.path.join(self._downloads_root_path, route))
            ]
        ]
        if not available_titles:
            return

        if main_title in available_titles:
            for title in reversed(available_titles):
                if title == main_title:
                    available_titles.remove(title)

            if not available_titles:
                return

        print(f"Renaming files and folders with {main_title}'s other titles.")

        processes = []
        for title in available_titles:
            process = multiprocessing.Process(target=self._title_rename, args=(main_title, title))
            process.start()
            processes.append(process)

        for process in processes:
            process.join()

        print(f"Finished renaming all the old titles.")

    def _title_rename(self, new_title: str, title: str):
        """Go through the files and folders in the directory and rename to use the new title."""
        # from .jsonmaker import TitleJson

        new_title_path = self._manga_download_path
        new_title_path.mkdir(parents=True, exist_ok=True)
        old_title_path = self._downloads_root_path.joinpath(title)
        old_title_files = os.listdir(old_title_path)
        old_title_json_path = old_title_path.joinpath(f"{self._manga_id}_data").with_suffix(".json")
        _version = 1

        while True:
            _version += 1
            old_title_json_new_path = new_title_path.joinpath(f"{self._manga_id}_data{{v{_version}}}").with_suffix(".json")
            if not old_title_json_new_path.is_file():
                break

        archive_downloads = [route for route in old_title_files if os.path.isfile(old_title_path.joinpath(route))]
        folder_downloads = [route for route in old_title_files if os.path.isdir(old_title_path.joinpath(route))]
        archive_downloads.reverse()
        folder_downloads.reverse()

        process = multiprocessing.Process(
            target=self._renaming_process,
            args=(new_title, new_title_path, old_title_path, archive_downloads, folder_downloads),
        )
        process.start()
        process.join()

        old_cover_route = old_title_path.joinpath("!covers")
        new_cover_route = new_title_path.joinpath("!covers")
        old_cover_route.mkdir(parents=True, exist_ok=True)
        new_cover_route.mkdir(parents=True, exist_ok=True)

        for cover in os.listdir(old_cover_route):
            old_cover_path = old_cover_route.joinpath(cover)
            if cover not in os.listdir(new_cover_route):
                new_cover_path = new_cover_route.joinpath(cover)
                old_cover_path.rename(new_cover_path)
            else:
                old_cover_path.unlink()

        try:
            old_title_json_path.rename(old_title_json_new_path)
            # old_title_json_path.unlink()
        except FileNotFoundError:
            pass
        finally:
            old_cover_route.rmdir()
            old_title_path.rmdir()

    def _renaming_process(self, new_title, new_title_path, old_title_path, archive_downloads, folder_downloads):
        pool = multiprocessing.Pool()
        pool_processes = []

        for folder_download in folder_downloads:
            p = pool.apply(self._folder_rename, args=(new_title, new_title_path, old_title_path, folder_download))
            pool_processes.append(p)

        for archive_download in archive_downloads:
            p = pool.apply(self._archive_rename, args=(new_title, new_title_path, old_title_path, archive_download))
            pool_processes.append(p)

        pool.close()
        pool.join()

    def _archive_rename(self, new_title: str, new_title_path: "Path", old_title_path: "Path", archive_download: str):
        """Rename the downloaded archives from the old title into the new title."""
        old_file_name_match = self.file_name_regex.match(archive_download)
        if not old_file_name_match:
            return

        old_archive_path = old_title_path.joinpath(archive_download)
        old_zipfile = zipfile.ZipFile(old_archive_path, mode="r", compression=zipfile.ZIP_DEFLATED)
        old_zipfile_files = old_zipfile.infolist()

        old_name = old_file_name_match.group("title")
        file_extension = old_file_name_match.group("extension")

        new_archive_path = new_title_path.joinpath(archive_download.replace(old_name, new_title)).with_suffix(
            f".{file_extension}"
        )
        new_zipfile = zipfile.ZipFile(new_archive_path, mode="a", compression=zipfile.ZIP_DEFLATED)
        new_zipfile.comment = old_zipfile.comment

        for old_image_name in old_zipfile_files:
            new_image = old_image_name.filename.replace(old_name, new_title)
            if new_image not in new_zipfile.namelist():
                new_zipfile.writestr(new_image, old_zipfile.read(old_image_name))

        # Close the archives and delete the old file
        old_zipfile.close()
        new_zipfile.close()
        old_archive_path.unlink()

    def _folder_rename(self, new_title: str, new_title_path: "Path", old_title_path: "Path", folder_download: str):
        """Rename the downloaded folders from the old title into the new title."""
        old_file_name_match = self.file_name_regex.match(folder_download)
        if not old_file_name_match:
            return
        old_folder_path = old_title_path.joinpath(folder_download)
        old_name = old_file_name_match.group("title")

        new_name = folder_download.replace(old_name, new_title)
        new_folder_path = new_title_path.joinpath(new_name)
        new_folder_path.mkdir(parents=True, exist_ok=True)

        for old_image_name in os.listdir(old_folder_path):
            new_image_name = old_image_name.replace(old_name, new_title)
            old_page_path = Path(old_folder_path.joinpath(old_image_name))
            if new_image_name not in os.listdir(new_folder_path):
                extension = os.path.splitext(old_page_path)[1]
                new_page_path = Path(new_folder_path.joinpath(new_image_name)).with_suffix(f"{extension}")
                old_page_path.rename(new_page_path)
            else:
                old_page_path.unlink()

        # Delete old folder after moving
        old_folder_path.rmdir()
