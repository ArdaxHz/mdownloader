import getpass
import gzip
import html
import json
import multiprocessing
import os
import re
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Union, TYPE_CHECKING

import requests
from requests.models import Response

from .constants import ImpVar
from .errors import MDownloaderError, MDRequestError, NoChaptersError
from .languages import get_lang_md

if TYPE_CHECKING:
    from .jsonmaker import TitleJson, BulkJson
    from .exporter import ArchiveExporter, FolderExporter
    import hondana



class ModelsBase:

    def __init__(self, model: 'MDownloader', hd_client: 'hondana.Client') -> None:
        self.model = model
        self.hd_client = hd_client



class MDownloaderBase:

    def __init__(self, hd_client: 'hondana.Client') -> None:
        self.hd_client = hd_client
        self.id = str()
        self.debug = False
        self.force_refresh = False
        self.download_type = str()
        self.directory = ImpVar.DOWNLOAD_PATH
        self.file_download = False

        self.data = {}
        self.manga_data = {}
        self.manga_titles = []
        self.chapters = []
        self.chapters_data = []
        self.chapter_data = {}
        self.title_json: 'TitleJson' = None
        self.bulk_json: 'BulkJson' = None
        self.chapter_prefix_dict = {}
        self.exporter: Union['ArchiveExporter', 'FolderExporter'] = None
        self.params = {}
        self.cache_json = {}
        self.chapters_archive = []
        self.chapters_folder = []

        self.type_id = 0
        self.exporter_id = 1
        self.manga_id = str()
        self.chapter_id = str()
        self.title = str()
        self.prefix = str()
        self.name = str()
        self.route = str()
        self.chapter_limit = 500
        self.chapters_total = 0
        self.manga_download = False

        self.api_url = ImpVar.MANGADEX_API_URL
        self.mdh_url = f'{self.api_url}/at-home/server'
        self.chapter_api_url = f'{self.api_url}/chapter'
        self.manga_api_url = f'{self.api_url}/manga'
        self.group_api_url = f'{self.api_url}/group'
        self.user_api_url = f'{self.api_url}/user'
        self.list_api_url = f'{self.api_url}/list'
        self.cover_api_url = f'{self.api_url}/cover'
        self.legacy_url = f'{self.api_url}/legacy/mapping'
        self.report_url = 'https://api.mangadex.network/report'
        self.cover_cdn_url = f'{ImpVar.MANGADEX_CDN_URL}/covers'



class ApiMD(ModelsBase):

    def __init__(self, model) -> None:
        super().__init__(model)
        self.session = requests.Session()

    def post_data(self, url: str, post_data: dict) -> Response:
        """Send a POST request with data to the API."""
        response = self.session.post(url, json=post_data)
        # if self.model.debug: print(response.url)
        return response

    def request_data(self, url: str, get_chapters: bool=False, **params: dict) -> Response:
        """Connect to the API and get the response.

        Args:
            url (str): Download url.
            get_chapters (bool, optional): If the download is to get the chapters. Defaults to False.

        Returns:
            Response: The response of the resquest.
        """
        if get_chapters:
            if self.model.download_type in ('group', 'user'):
                url = self.model.chapter_api_url
            else:
                url = f'{url}/feed'

        response = self.session.get(url, params=params)
        if self.model.debug: print(response.url)
        return response

    def check_response_error(self, download_id: str, download_type: str, response: Response, data: dict={}) -> None:
        """Check if the response status code is 200 or not."""
        if response.status_code != 200:
            raise MDRequestError(download_id, download_type, response, data)

    def convert_to_json(self, download_id: str, download_type: str, response: Response) -> Union[dict, list]:
        """Convert the response data into a parsable json."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise MDRequestError(download_id, download_type, response)

        self.check_response_error(download_id, download_type, response, data)

        if 'result' in data and data["result"].lower() not in ('ok',):
            raise MDRequestError(download_id, download_type, response, data={"result": "error", "errors": [{"status": 200, "detail": f"Result returned `{data['result']}`."}]})

        if 'response' in data:
            if data["response"] == 'entity':
                data = data["data"]

        return data

    def get_manga_data(self, download_type: str) -> dict:
        """Call the manga api for the data.

        Args:
            download_type (str): The type of download calling the manga api.

        Returns:
            dict: The manga's data.
        """
        manga_response = self.request_data(f'{self.model.manga_api_url}/{self.model.manga_id}', **{"includes[]": ["artist", "author", "cover"]})
        return self.convert_to_json(self.model.manga_id, download_type, manga_response)



class AuthMD(ModelsBase):

    def __init__(self, model) -> None:
        super().__init__(model)
        self.successful_login = False
        self.token_file = Path('').joinpath(ImpVar.TOKEN_FILE)
        self.auth_url = f'{self.model.api_url}/auth'

    def _save_session(self, token: dict) -> None:
        """Save the session and refresh tokens."""
        with open(self.token_file, 'w') as login_file:
            login_file.write(json.dumps(token, indent=4))

    def _update_headers(self, session_token: str) -> None:
        """Update the session headers to include the auth token."""
        self.model.api.session.headers = {"Authorization": f"Bearer {session_token}"}

    def _refresh_token(self, token: dict) -> bool:
        """Use the refresh token to get a new session token.

        Returns:
            bool: If login using the refresh token or account was successful.
        """
        refresh_response = self.model.api.post_data(f'{self.auth_url}/refresh', post_data={"token": token["refresh"]})

        if refresh_response.status_code == 200:
            refresh_data = refresh_response.json()["token"]

            self._update_headers(token["session"])
            self._save_session(refresh_data)
            return True
        elif refresh_response.status_code in (401, 403):
            print("Couldn't login using refresh token, login using your account.")
            return self._login_using_details()
        else:
            print("Couldn't refresh token.")
            return False

    def _check_login(self, token: dict) -> bool:
        """Try login using saved session token.

        Returns:
            bool: If login using the session token successful.
        """
        auth_check_response = self.model.api.session.get(f'{self.auth_url}/check')

        if auth_check_response.status_code == 200:
            auth_data = auth_check_response.json()

            if auth_data["isAuthenticated"]:
                return True
            else:
                return self._refresh_token(token)

    def _login_using_details(self) -> bool:
        """Login using account details.

        Returns:
            bool: If login was successful.
        """
        username = input('Your username: ')
        password = getpass.getpass(prompt='Your password: ', stream=None)

        credentials = {"username": username, "password": password}
        post = self.model.api.post_data(f'{self.auth_url}/login', post_data=credentials)

        if post.status_code == 200:
            token = post.json()["token"]
            self._update_headers(token["session"])
            self._save_session(token)
            return True
        return False

    def login(self) -> None:
        """Login to MD account using details or saved token."""
        print('Trying to login through the .mdauth file.')

        try:
            with open(self.token_file, 'r') as login_file:
                token = json.load(login_file)

            self._update_headers(token["session"])
            logged_in = self._check_login(token)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Couldn't find the file, trying to login using your account.")
            logged_in = self._login_using_details()

        if logged_in:
            self.successful_login = True
            print('Login successful!')
        else:
            print('Login unsuccessful, continuing without being logged in.')



class ProcessArgs(ModelsBase):

    def __init__(self, model) -> None:
        super().__init__(model)
        self.language = str()
        self.archive_extension = str()
        self.folder_download = bool()
        self.cover_download = bool()
        self.save_chapter_data = bool()
        self.range_download = bool()
        self.rename_files = bool()
        self.search_manga = False
        self.download_in_order = False
        self.naming_scheme_options = ["default", "original", "number"]
        self.naming_scheme = "default"

    def format_args(self, vargs: dict) -> None:
        """Format the command line arguments into readable data."""
        args_dict = vargs

        self.model.id = str(args_dict["id"])
        self.model.debug = bool(args_dict["debug"])
        self.model.force_refresh = bool(args_dict["refresh"])
        self.model.download_type = str(args_dict["type"])
        self.model.directory = str(args_dict["directory"]) if args_dict["directory"] is not None else self.model.directory
        self.language = get_lang_md(args_dict["language"])
        self.archive_extension = ImpVar.ARCHIVE_EXTENSION
        self._check_archive_extension(self.archive_extension)
        self.folder_download = bool(args_dict["folder"])
        self.cover_download = bool(args_dict["covers"])
        self.save_chapter_data = bool(args_dict["json"])
        self.range_download = bool(args_dict["range"])
        self.rename_files = bool(args_dict["rename"])
        self.download_in_order = bool(args_dict["order"])
        if args_dict["login"]: self.model.auth.login()
        if args_dict["search"]:
            self.search_manga = True
            self._find_manga(self.model.id)

    def _check_archive_extension(self, archive_extension: str) -> str:
        """Check if the file extension is an accepted format. Default: cbz.

        Raises:
            MDownloaderError: The extension chosen isn't allowed.
        """
        if archive_extension not in ('zip', 'cbz'):
            raise MDownloaderError("This archive save format is not allowed.")

    def _find_manga(self, search_term: str) -> None:
        """Search for a manga by title."""
        manga_response = self.model.api.request_data(
            f'{self.model.manga_api_url}',
            **{"title": search_term,
               "limit": 100,
               "includes[]": ["artist", "author", "cover"],
               "contentRating[]": ["safe","suggestive","erotica", "pornographic"],
               "order[relevance]": "desc"})
        search_results = self.model.api.convert_to_json(search_term, 'manga-search', manga_response)
        search_results_data = search_results["data"]

        for count, manga in enumerate(search_results_data, start=1):
            title = self.model.formatter.get_title(manga)
            print(f'{count}: {title} | {ImpVar.MANGADEX_URL}/manga/{manga["id"]}')

        try:
            manga_to_use_num = int(input(f'Choose a number matching the position of the manga you want to download: '))
        except ValueError:
            raise MDownloaderError("That's not a number.")

        if manga_to_use_num not in range(1, (len(search_results_data) + 1)):
            raise MDownloaderError("Not a valid option.")

        manga_to_use = search_results_data[manga_to_use_num - 1]

        self.model.id = manga_to_use["id"]
        self.model.download_type = 'manga'
        self.model.manga_data = manga_to_use



class DataFormatter(ModelsBase):

    def __init__(self, model: 'MDownloader') -> None:
        super().__init__(model)
        self.file_name_regex = re.compile(ImpVar.FILE_NAME_REGEX, re.IGNORECASE)

    def _check_downloaded_files(self):
        """Check if folders using other manga titles exist."""
        new_title = self.model.title
        available_titles = [self.strip_illegal_characters(x) for x in self.model.manga_titles if self.strip_illegal_characters(x) in [
            route for route in os.listdir(self.model.directory) if os.path.isdir(os.path.join(self.model.directory, route))]]
        if not available_titles:
            return

        if new_title in available_titles:
            for title in reversed(available_titles):
                if title == new_title:
                    available_titles.remove(title)

            if not available_titles:
                return

        print(f"Renaming files and folders with {new_title}'s other titles.")

        processes = []
        for title in available_titles:
            process = multiprocessing.Process(target=self._title_rename, args=(new_title, title))
            process.start()
            processes.append(process)

        for process in processes:
            process.join()

        print(f"Finished renaming all the old titles.")

    def _title_rename(self, new_title: str, title: str):
        """Go through the files and folders in the directory and rename to use the new title."""
        from .jsonmaker import TitleJson
        new_title_path = Path(self.model.route)
        new_title_path.mkdir(parents=True, exist_ok=True)
        old_title_path = Path(os.path.join(self.model.directory, title))
        old_title_files = os.listdir(old_title_path)
        new_title_route = self.model.route

        archive_downloads = [route for route in old_title_files if os.path.isfile(old_title_path.joinpath(route))]
        folder_downloads = [route for route in old_title_files if os.path.isdir(old_title_path.joinpath(route))]
        archive_downloads.reverse()
        folder_downloads.reverse()

        process = multiprocessing.Process(
            target=self._renaming_process,
            args=(new_title, new_title_path, old_title_path, archive_downloads, folder_downloads))
        process.start()
        process.join()

        self.model.route = old_title_path
        old_title_json = TitleJson(self.model)
        self.model.route = new_title_route
        new_title_json = TitleJson(self.model)

        for chapter in old_title_json.chapters:
            new_title_json.add_chapter(chapter)

        new_title_json.core()
        old_cover_route = old_title_json.cover_route
        new_cover_route = new_title_json.cover_route
        old_cover_route.mkdir(parents=True, exist_ok=True)
        new_cover_route.mkdir(parents=True, exist_ok=True)

        for cover in os.listdir(old_cover_route):
            old_cover_path = old_title_json.cover_route.joinpath(cover)
            if cover not in os.listdir(new_cover_route):
                new_cover_path = new_title_json.cover_route.joinpath(cover)
                old_cover_path.rename(new_cover_path)
            else:
                old_cover_path.unlink()

        old_title_json.cover_route.rmdir()
        old_title_json.json_path.unlink()
        del old_title_json
        del new_title_json
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

    def _archive_rename(self, new_title: str, new_title_path: 'Path', old_title_path: 'Path', archive_download: str):
        """Rename the downloaded archives from the old title into the new title."""
        old_file_name_match = self.file_name_regex.match(archive_download)
        if not old_file_name_match:
            return

        old_archive_path = old_title_path.joinpath(archive_download)
        old_zipfile = zipfile.ZipFile(old_archive_path, mode="r", compression=zipfile.ZIP_DEFLATED)
        old_zipfile_files = old_zipfile.infolist()

        old_name = old_file_name_match.group('title')
        file_extension = old_file_name_match.group('extension')

        new_archive_path = new_title_path.joinpath(archive_download.replace(old_name, new_title)).with_suffix(f'.{file_extension}')
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

    def _folder_rename(self, new_title: str, new_title_path: 'Path', old_title_path: 'Path', folder_download: str):
        """Rename the downloaded folders from the old title into the new title."""
        old_file_name_match = self.file_name_regex.match(folder_download)
        if not old_file_name_match:
            return
        old_folder_path = old_title_path.joinpath(folder_download)
        old_name = old_file_name_match.group('title')

        new_name = folder_download.replace(old_name, new_title)
        new_folder_path = new_title_path.joinpath(new_name)
        new_folder_path.mkdir(parents=True, exist_ok=True)

        for old_image_name in os.listdir(old_folder_path):
            new_image_name = old_image_name.replace(old_name, new_title)
            old_page_path = Path(old_folder_path.joinpath(old_image_name))
            if new_image_name not in os.listdir(new_folder_path):
                extension = os.path.splitext(old_page_path)[1]
                new_page_path = Path(new_folder_path.joinpath(new_image_name)).with_suffix(f'{extension}')
                old_page_path.rename(new_page_path)
            else:
                old_page_path.unlink()

        # Delete old folder after moving
        old_folder_path.rmdir()


class Filtering(ModelsBase):

    def __init__(self, model) -> None:
        super().__init__(model)
        self.root = Path("")
        self._group_blacklist_file = self.root.joinpath(ImpVar.GROUP_BLACKLIST_FILE)
        self._group_whitelist_file = self.root.joinpath(ImpVar.GROUP_WHITELIST_FILE)
        self._user_blacklist_file = self.root.joinpath(ImpVar.USER_BLACKLIST_FILE)
        self._user_userlist_file = self.root.joinpath(ImpVar.USER_WHITELIST_FILE)

        self.group_blacklist = self._read_file(self._group_blacklist_file)
        self.group_whitelist = self._read_file(self._group_whitelist_file)
        self.user_blacklist = self._read_file(self._user_blacklist_file)
        self.user_whitelist = self._read_file(self._user_userlist_file)

    def _read_file(self, file_path: str) -> list:
        """Opens the text file and loads the ids to filter."""
        try:
            with open(file_path, 'r') as fp:
                filter_list = [line.rstrip('\n') for line in fp.readlines()]
                return filter_list
        except FileNotFoundError:
            return []

    def filter_chapters(self, chapters: list) -> list:
        """Filters the chapters according to the selected filters."""
        if self.group_whitelist or self.user_whitelist:
            if self.group_whitelist:
                chapters = [c for c in chapters if [g for g in c["relationships"] if g["type"] == 'scanlation_group' and g["id"] in self.group_whitelist]]
            if self.user_whitelist:
                chapters = [c for c in chapters if [u for u in c["relationships"] if u["type"] == 'user' and u["id"] in self.user_whitelist]]
        else:
            chapters = [c for c in chapters if
                (([g for g in c["relationships"] if g["type"] == 'scanlation_group' and g["id"] not in self.group_blacklist])
                    or [u for u in c["relationships"] if u["type"] == 'user' and u["id"] not in self.user_blacklist])]
        return chapters



class MDownloaderMisc(ModelsBase):

    def check_url(self, url: str) -> bool:
        """Check if the url given is a MangaDex one."""
        return bool(ImpVar.MD_URL.match(url) or ImpVar.MD_IMAGE_URL.match(url) or ImpVar.MD_FOLLOWS_URL.match(url))

    def check_for_links(self, links: list, error_message: str) -> None:
        """Check the file has any MangaDex urls or ids.

        Args:
            links (list): Array of urls and ids.

        Raises:
            NoChaptersError: End the program with the error message.
        """
        if not links:
            raise NoChaptersError(error_message)

    def check_uuid(self, series_id: str) -> bool:
        """Check if the id is a UUID."""
        return bool(re.match(ImpVar.UUID_REGEX, series_id))

    def download_message(self, status: bool, download_type: str, name: str) -> None:
        """Print the download message.

        Args:
            status (bool): If the download has started or ended.
            download_type (str): What type of data is being downloaded, chapter, manga, group, user, or list.
            name (str): Name of the chosen download.
        """
        message = 'Downloading'
        if status:
            message = f'Finished {message}'

        print(f'{"-"*69}\n{message} {download_type.title()}: {name}\n{"-"*69}')

    def check_for_chapters(self, data: dict) -> int:
        """Check if there are any chapters.

        Raises:
            NoChaptersError: No chapters were found.

        Returns:
            int: The amount of chapters found.
        """
        count = data.get('total', 0)

        if not data["data"]:
            count = 0

        if self.model.type_id == 1:
            download_type = 'manga'
            name = self.model.title
        else:
            download_type = self.model.download_type
            name = self.model.name

        if count == 0:
            raise NoChaptersError(f'{download_type.title()}: {self.model.id} - {name} has no chapters. Possibly because of the language chosen or because there are no uploads.')
        return count

    def check_manga_data(self, chapter_data: dict) -> dict:
        """Uses the chapter data to check if the manga data is available, if not, call the manga api.

        Returns:
            dict: The manga data to use.
        """
        manga = dict([c for c in chapter_data["relationships"] if c["type"] == 'manga'][0])
        manga_id = manga["id"]
        self.model.manga_id = manga_id
        manga_data = manga.get('attributes', {})

        if not manga_data:
            cache_json = self.model.cache.load_cache(manga_id)
            refresh_cache = self.model.cache.check_cache_time(cache_json)
            manga_data = cache_json.get('data', {})

            if refresh_cache or not manga_data:
                if self.model.debug: print('Calling api for manga data from chapter download.')
                manga_data = self.model.api.get_manga_data('chapter-manga')
                self.model.cache.save_cache(datetime.now(), manga_id, data=manga_data)
        else:
            manga_data = manga
            self.model.cache.save_cache(datetime.now(), manga_id, data=manga_data)

        return manga_data

    def check_external(self, chapter_data: dict) -> Optional[str]:
        """Checks if the chapter is internal or external to MangaDex.

        Raises:
            MDownloaderError: Chapter is external and not downloadable.

        Returns:
            Optional[str]: The external url if available.
        """
        external = False
        url = None

        if 'externalUrl' in chapter_data:
            if chapter_data["externalUrl"] is not None:
                url = chapter_data["externalUrl"]
                external = True

        if external:
            if any(s in url for s in ('mangaplus',)):
                return url
            else:
                raise MDownloaderError('Chapter external to MangaDex, unable to download. Skipping...')

        return None


class TitleDownloaderMisc(ModelsBase):

    def get_prefixes(self, chapters: list) -> dict:
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
        prefix = 'b'

        # Loop over the volume dict list and
        # check if the current iteration has the same chapter numbers as the volume before and after
        for volume in list_volume_dict:
            if volume is None or volume == '':
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

            if volume is not None or volume != '':
                if result:
                    vol_prefix = chr(ord(prefix) + next_volume_index)
                else:
                    vol_prefix = 'c'
                chapter_prefix_dict.update({volume: vol_prefix})
        return chapter_prefix_dict

    def _natsort(self, x) -> Union[float, str]:
        """Sort the chapter numbers naturally."""
        try:
            return float(x)
        except TypeError:
            return '0'
        except ValueError:
            return x

    def _get_chapters_range(self, chapters_list: list, chap_list: list) -> list:
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
                chapter_range = chapter.split('-')
                chapter_range = [None if v == 'oneshot' else v for v in chapter]
                lower_bound = chapter_range[0].strip()
                upper_bound = chapter_range[1].strip()
                try:
                    lower_bound_i = chapters_list.index(lower_bound)
                except ValueError:
                    print(f'Chapter lower bound {lower_bound} does not exist. Skipping {chapter}.')
                    continue
                try:
                    upper_bound_i = chapters_list.index(upper_bound)
                except ValueError:
                    print(f'Chapter upper bound {upper_bound} does not exist. Skipping {chapter}.')
                    continue
                chapter = chapters_list[lower_bound_i:upper_bound_i+1]
            else:
                if chapter == 'oneshot':
                    chapter = None
                try:
                    chapter = [chapters_list[chapters_list.index(chapter)]]
                except ValueError:
                    print(f'Chapter {chapter} does not exist. Skipping.')
                    continue
            chapters_range.extend(chapter)
        return chapters_range

    def download_range_chapters(self, chapters: list) -> list:
        """Get the chapter numbers you want to download.

        Returns:
            list: The chapters to download.
        """
        chapters_list = [c["attributes"]["chapter"] for c in chapters]
        chapters_list_str = ['oneshot' if c is None else c for c in chapters_list]
        chapters_list = list(set(chapters_list))
        chapters_list.sort(key=self._natsort)
        remove_chapters = []

        if not chapters_list:
            return chapters

        print(f'Available chapters:\n{", ".join(chapters_list_str)}')
        chap_list = input("\nEnter the chapter(s) to download: ").strip()

        if not chap_list:
            raise MDownloaderError('No chapter(s) chosen.')

        chap_list = [c.strip() for c in chap_list.split(',')]
        chapters_to_remove = [c.strip('!') for c in chap_list if '!' in c]
        chap_list = [c for c in chap_list if '!' not in c]

        # Find which chapters to download
        if 'all' not in chap_list:
            chapters_to_download = self._get_chapters_range(chapters_list, chap_list)
        else:
            chapters_to_download = chapters_list

        # Get the chapters to remove from the download list
        remove_chapters = self._get_chapters_range(chapters_list, chapters_to_remove)

        for i in remove_chapters:
            chapters_to_download.remove(i)
        return [c for c in chapters if c["attributes"]["chapter"] in chapters_to_download]



class MDownloader(MDownloaderBase):

    def __init__(self, hd_client: hondana.Client) -> None:
        super().__init__(hd_client)

        self.api = ApiMD(self)
        self.auth = AuthMD(self)
        self.formatter = DataFormatter(self)
        self.args = ProcessArgs(self)
        self.exist = ExistChecker(self)
        self.cache = CacheRead(self)
        self.filter = Filtering(self)
        self.misc = MDownloaderMisc(self)
        self.title_misc = TitleDownloaderMisc(self)

    def wait(self, time_to_wait: int=ImpVar.GLOBAL_TIME_TO_WAIT, print_message: bool=False) -> None:
        """Wait a certain amount of time before continuing.

        Args:
            time_to_wait (int, optional): The time to wait. Defaults to ImpVar.GLOBAL_TIME_TO_WAIT.
            print_message (bool, optional): If to print the waiting message. Defaults to False.
        """
        if time_to_wait == 0:
            return

        if print_message:
            print(f"Waiting {time_to_wait} second(s).")

        time.sleep(time_to_wait)
