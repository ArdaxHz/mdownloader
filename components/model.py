import getpass
import gzip
import html
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Union

import requests
from requests.models import Response

from .constants import ImpVar
from .errors import MDownloaderError, MDRequestError, NoChaptersError
from .languages import get_lang_md



class ModelsBase:

    def __init__(self, model) -> None:
        self.model = model



class MDownloaderBase:

    def __init__(self) -> None:
        self.id = str()
        self.debug = bool(False)
        self.force_refresh = bool(False)
        self.download_type = str()
        self.directory = ImpVar.DOWNLOAD_PATH
        self.file_download = bool(False)

        self.data = {}
        self.manga_data = {}
        self.chapters = []
        self.chapters_data = []
        self.chapter_data = {}
        self.title_json = None
        self.bulk_json = None
        self.chapter_prefix_dict = {}
        self.exporter = None
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
        self.manga_download = bool(False)

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
        if self.model.debug: print(response.url)
        return response

    def request_data(self, url: str, get_chapters: bool=0, **params: dict) -> Response:
        """Connect to the API and get the response.

        Args:
            url (str): Download url.
            get_chapters (bool, optional): If the download is to get the chapters. Defaults to 0.

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

    def check_response_error(self, download_id: str, download_type: str, response: Response, data: dict) -> None:
        """Check if the response status code is 200 or not."""
        if response.status_code != 200:
            raise MDRequestError(download_id, download_type, response, data)

    def convert_to_json(self, download_id: str, download_type: str, response: Response) -> dict:
        """Convert the response data into a parsable json."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise MDRequestError(download_id, download_type, response)

        self.check_response_error(download_id, download_type, response, data)

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

    def save_session(self, token: dict) -> None:
        """Save the session and refresh tokens."""
        with open(self.token_file, 'w') as login_file:
            login_file.write(json.dumps(token, indent=4))

    def update_headers(self, session_token: str) -> None:
        """Update the session headers to include the auth token."""
        self.model.api.session.headers = {"Authorization": f"Bearer {session_token}"}

    def refresh_token(self, token: dict) -> bool:
        """Use the refresh token to get a new session token.

        Returns:
            bool: If login using the refresh token or account was successful.
        """
        refresh_token = {"token": token["refresh"]}
        refresh_response = self.model.api.post_data(f'{self.auth_url}/refresh', refresh_token)

        if refresh_response.status_code == 200:
            refresh_data = refresh_response.json()["token"]

            self.update_headers(token["session"])
            self.save_session(refresh_data)
            return True
        elif refresh_response.status_code in (401, 403):
            print("Couldn't login using refresh token, login using your account.")
            return self.login_using_details()
        else:
            print("Couldn't refresh token.")
            return False

    def check_login(self, token: dict) -> bool:
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
                return self.refresh_token(token)

    def login_using_details(self) -> bool:
        """Login using account details.

        Returns:
            bool: If login was successful.
        """
        username = input('Your username: ')
        password = getpass.getpass(prompt='Your password: ', stream=None)

        credentials = {"username": username, "password": password}
        post = self.model.api.post_data(f'{self.auth_url}/login', credentials)
        
        if post.status_code == 200:
            token = post.json()["token"]
            self.update_headers(token["session"])
            self.save_session(token)
            return True
        return False

    def login(self) -> None:
        """Login to MD account using details or saved token."""
        print('Trying to login through the .mdauth file.')

        try:
            with open(self.token_file, 'r') as login_file:
                token = json.load(login_file)

            self.update_headers(token["session"])
            logged_in = self.check_login(token)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Couldn't find the file, trying to login using your account.")
            logged_in = self.login_using_details()

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
        self.search_manga = False
        self.download_in_order = False
        self.naming_scheme_options = ["default", "original", "number"]
        self.naming_scheme = "default"

    def format_args(self, args) -> None:
        """Format the command line arguments into readable data."""
        args_dict = vars(args)

        self.model.id = str(args_dict["id"])
        self.model.debug = bool(args_dict["debug"])
        self.model.force_refresh = bool(args_dict["force"])
        self.model.download_type = str(args_dict["type"])
        self.language = get_lang_md(args_dict["language"])
        self.archive_extension = ImpVar.ARCHIVE_EXTENSION
        self.check_archive_extension(self.archive_extension)
        self.folder_download = bool(args_dict["folder"])
        self.cover_download = bool(args_dict["covers"])
        self.save_chapter_data = bool(args_dict["json"])
        self.range_download = bool(args_dict["range"])
        self.download_in_order = bool(args_dict["order"])
        if args_dict["login"]: self.model.auth.login()
        if args_dict["search"] and self.model.download_type in ('title', 'manga'):
            self.search_manga = True
            self.find_manga()

    def check_archive_extension(self, archive_extension: str) -> str:
        """Check if the file extension is an accepted format. Default: cbz.

        Raises:
            MDownloaderError: The extension chosen isn't allowed.
        """
        if archive_extension not in ('zip', 'cbz'):
            raise MDownloaderError("This archive save format is not allowed.")

    def find_manga(self):
        """Search for a manga by title."""
        manga_response = self.model.api.request_data(f'{self.model.manga_api_url}', **{"title": self.model.id, "limit": 100, "includes[]": ["artist", "author", "cover"]})
        data = self.model.api.convert_to_json(self.model.id, 'manga-search', manga_response)
        data = data["results"]

        for count, manga in enumerate(data, start=1):
            title = self.model.formatter.get_title(manga)
            print(f'{count}: {title}')

        try:
            manga_to_use_num = int(input(f'Choose a number matching the position of the manga you want to download: '))
        except ValueError:
            raise MDownloaderError("That's not a number.")

        if manga_to_use_num not in range(1, (len(data) + 1)):
            raise MDownloaderError("Not a valid option.")

        manga_to_use = data[(manga_to_use_num - 1)]

        self.model.id = manga_to_use["data"]["id"]
        self.model.download_type = 'manga'
        self.model.manga_data = manga_to_use



class ExistChecker(ModelsBase):

    def check_exist(self, pages: list) -> bool:
        """Check if the number of images in the archive or folder match that of the API."""
        # Only image files are counted
        if self.model.args.folder_download:
            files_path = os.listdir(self.model.exporter.folder_path)
        else:
            files_path = self.model.exporter.archive.namelist()

        zip_count = [i for i in files_path if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

        if len(pages) == len(zip_count):
            return True
        return False

    def save_json(self) -> None:
        """Save the chapter data to the data json and save the json."""
        if self.model.type_id in (1,):
            self.model.title_json.core()

        if self.model.type_id in (2, 3):
            self.model.manga_download = False
            self.model.bulk_json.core()
            self.model.manga_download = True

    def before_download(self, exists: bool) -> None:
        """Skip chapter if its already downloaded."""
        if exists:
            # Add chapter data to the json for title, group or user downloads
            self.save_json()
            self.model.exporter.close()
            raise MDownloaderError('File already downloaded.')

    def after_download(self, downloaded_all: bool) -> None:
        """Save json if all the images were downloaded and close the archive."""
        # If all the images are downloaded, save the json file with the latest downloaded chapter
        # not downloaded_all
        if downloaded_all:
            # # Remove chapter data from json
            # if self.model.type_id in (1,):
            #     self.model.title_json.remove_chapter(self.model.chapter_data)
            # if self.model.type_id in (2, 3):
            #     self.model.bulk_json.remove_chapter(self.model.chapter_data)
            self.save_json()

        # Close the archive
        self.model.exporter.close()



class DataFormatter(ModelsBase):

    def get_title(self, data: dict) -> str:
        """Get the title from the manga data, looks for other languages if English is not available."""
        attributes = data["data"]["attributes"]

        if 'en' in attributes["title"]:
            title = attributes["title"]["en"]
        elif attributes["originalLanguage"] in attributes["title"]:
            title = attributes["title"]["originalLanguage"]
        else:
            key = next(iter(attributes["title"]))
            title = attributes["title"][key]

        return title

    def strip_illegal(self, name: str) -> str:
        """Remove illegal characters from the specified name."""
        return re.sub(ImpVar.CHARA_REGEX, '_', html.unescape(name))

    def format_route(self) -> None:
        """The route files will be saved to."""
        self.model.route = os.path.join(self.model.directory, self.model.title)

    def format_title(self, data: dict) -> str:
        """Remove illegal characters from the manga title."""
        title = self.get_title(data)
        title = self.strip_illegal(title).rstrip(' .')
        self.model.title = title
        self.format_route()
        return title

    def id_from_url(self, url: str) -> Tuple[str, str]:
        """Get the id and download type from url."""
        if ImpVar.MD_URL.match(url):
            input_url = ImpVar.MD_URL.match(url)
            download_type_from_url = input_url.group(1)
            id_from_url = input_url.group(2)
        elif ImpVar.MD_FOLLOWS_URL.match(url):
            id_from_url = url
            download_type_from_url = 'follows'
        else:
            input_url = ImpVar.MD_IMAGE_URL.match(url)
            id_from_url = input_url.group(1)
            download_type_from_url = 'chapter'

        return id_from_url, download_type_from_url



class CacheRead(ModelsBase):

    def __init__(self, model) -> None:
        super().__init__(model)
        self.cache_refresh_time = ImpVar.CACHE_REFRESH_TIME
        self.root = Path(ImpVar.CACHE_PATH)
        self.root.mkdir(parents=True, exist_ok=True)
        self.force_reset_cache_time = "1970-01-01 00:00:00.000000"

    def save_cache(self, cache_time: Union[str, datetime], download_id: str, data: dict={}, chapters: list=[], covers: list=[]) -> None:
        """Save the data to the cache.

        Args:
            cache_time (str): The time the cache was saved.
            download_id (str): The id of the data to cache.
            data (dict, optional): The data to cache. Defaults to {}.
            chapters (list, optional): The chapters to cache. Defaults to [].
            covers (list, optional): The covers of the manga.. Defaults to [].
        """
        if cache_time == '':
            cache_time = self.force_reset_cache_time

        cache_json = {"cache_date": str(cache_time), "data": data, "covers": covers, "chapters": chapters}
        cache_file_path = self.root.joinpath(f'{download_id}').with_suffix('.json.gz')
        if self.model.debug: print(cache_file_path)

        with gzip.open(cache_file_path, 'w') as cache_json_fp:
            cache_json_fp.write(json.dumps(cache_json, indent=4, ensure_ascii=False).encode('utf-8'))

    def load_cache(self, download_id: str) -> dict:
        """Load the cache data.

        Args:
            download_id (str): The id of the cache data to load.

        Returns:
            dict: The cache's data.
        """
        cache_file_path = self.root.joinpath(f'{download_id}').with_suffix('.json.gz')
        if self.model.debug: print(cache_file_path)

        try:
            with gzip.open(cache_file_path, 'r') as cache_json_fp:
                cache_json = json.loads(cache_json_fp.read().decode('utf-8'))
            return cache_json
        except (FileNotFoundError, json.JSONDecodeError, gzip.BadGzipFile):
            return {}

    def check_cache_time(self, cache_json: dict) -> bool:
        """Check if the cache needs to be refreshed.

        Args:
            cache_json (dict): The cache data.

        Returns:
            bool: If a refresh is needed.
        """
        refresh = True
        if cache_json:
            cache_time = cache_json.get("cache_date", self.force_reset_cache_time)
            timestamp = datetime.strptime(cache_time, "%Y-%m-%d %H:%M:%S.%f") + timedelta(hours=self.cache_refresh_time)
            if datetime.now() >= timestamp:
                pass
            else:
                refresh = False

        if self.model.force_refresh:
            refresh = True

        if refresh:
            if self.model.debug: print('Refreshing cache.')
        else:
            if self.model.debug: print('Using cache data.')
        return refresh



class Filtering(ModelsBase):

    def __init__(self, model) -> None:
        super().__init__(model)
        self.root = Path("")
        self._group_blacklist_file = self.root.joinpath(ImpVar.GROUP_BLACKLIST_FILE)
        self._group_whitelist_file = self.root.joinpath(ImpVar.GROUP_WHITELIST_FILE)
        self._user_blacklist_file = self.root.joinpath(ImpVar.USER_BLACKLIST_FILE)
        self._user_userlist_file = self.root.joinpath(ImpVar.USER_WHITELIST_FILE)

        self.group_blacklist = self.read_file(self._group_blacklist_file)
        self.group_whitelist = self.read_file(self._group_whitelist_file)
        self.user_blacklist = self.read_file(self._user_blacklist_file)
        self.user_whitelist = self.read_file(self._user_userlist_file)

    def read_file(self, file_path: str) -> list:
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
                chapters = [c for c in chapters if [g for g in c["data"]["relationships"] if g["type"] == 'scanlation_group' and g["id"] in self.group_whitelist]]
            else:
                if self.user_whitelist:
                    chapters = [c for c in chapters if [u for u in c["data"]["relationships"] if u["type"] == 'user' and u["id"] in self.user_whitelist]]
        else:
            chapters = [c for c in chapters if 
                (([g for g in c["data"]["relationships"] if g["type"] == 'scanlation_group' and g["id"] not in self.group_blacklist]) 
                    or [u for u in c["data"]["relationships"] if u["type"] == 'user' and u["id"] not in self.user_blacklist])]
        return chapters



class MDownloaderMisc(ModelsBase):

    def check_url(self, url: str) -> bool:
        """Check if the url given is a MangaDex one."""
        return bool(ImpVar.MD_URL.match(url) or ImpVar.MD_IMAGE_URL.match(url) or ImpVar.MD_FOLLOWS_URL.match(url))

    def check_for_links(self, links: list, message: str) -> None:
        """Check the file has any MangaDex urls or ids. 

        Args:
            links (list): Array of urls and ids.
            message (str): The error message.

        Raises:
            NoChaptersError: End the program with the error message.
        """
        if not links:
            raise NoChaptersError(message)

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
        download_id = self.model.id
        count = data.get('total', 0)

        if not data["results"]:
            count = 0

        if self.model.type_id == 1:
            download_type = 'manga'
            name = self.model.title
        else:
            download_type = self.model.download_type
            name = self.model.name

        if count == 0:
            raise NoChaptersError(f'{download_type.title()}: {download_id} - {name} has no chapters. Possibly because of the language chosen or because there are no uploads.')
        return count

    def check_manga_data(self, chapter_data: dict) -> dict:
        """Uses the chapter data to check if the manga data is available, if not, call the manga api.

        Returns:
            dict: The manga data to use.
        """
        manga = dict([c for c in chapter_data["data"]["relationships"] if c["type"] == 'manga'][0])
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
            manga_data = {"data": manga}
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
        url = ''

        if 'externalUrl' in chapter_data:
            if chapter_data["externalUrl"] is not None and chapter_data["externalUrl"] != '':
                url = chapter_data["externalUrl"]
                external = True

        if not external and bool(ImpVar.URL_RE.match(chapter_data["data"][0])):
            url = chapter_data["data"][0]
            external = True

        if external:
            if any(s in url for s in ('mangaplus', 'comikey')):
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
            c = c["data"]["attributes"]
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

    def natsort(self, x) -> Union[float, str]:
        """Sort the chapter numbers naturally."""
        try:
            return float(x)
        except TypeError:
            return '0'
        except ValueError:
            return x

    def get_chapters_range(self, chapters_list: list, chap_list: list) -> list:
        """Loop through the lists and get the chapters between the upper and lower bounds.

        Args:
            chapters_list (list): All the chapters in the manga.
            chap_list (list): A list of chapter numbers to download.

        Returns:
            list: The chapters to download the data of.
        """
        chapters_range = []

        for c in chap_list:
            if "-" in c:
                chapter_range = c.split('-')
                chapter_range = [None if v == 'oneshot' else v for v in c]
                lower_bound = chapter_range[0].strip()
                upper_bound = chapter_range[1].strip()
                try:
                    lower_bound_i = chapters_list.index(lower_bound)
                except ValueError:
                    print(f'Chapter lower bound {lower_bound} does not exist. Skipping {c}.')
                    continue
                try:
                    upper_bound_i = chapters_list.index(upper_bound)
                except ValueError:
                    print(f'Chapter upper bound {upper_bound} does not exist. Skipping {c}.')
                    continue
                c = chapters_list[lower_bound_i:upper_bound_i+1]
            else:
                if c == 'oneshot':
                    c = None
                try:
                    c = [chapters_list[chapters_list.index(c)]]
                except ValueError:
                    print(f'Chapter {c} does not exist. Skipping.')
                    continue
            chapters_range.extend(c)
        return chapters_range

    def download_range_chapters(self, chapters: list) -> list:
        """Get the chapter numbers you want to download.

        Returns:
            list: The chapters to download.
        """
        chapters_list = [c["data"]["attributes"]["chapter"] for c in chapters]
        chapters_list_str = ['oneshot' if c is None else c for c in chapters_list]
        chapters_list = list(set(chapters_list))
        chapters_list.sort(key=self.natsort)
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
            chapters_to_download = self.get_chapters_range(chapters_list, chap_list)
        else:
            chapters_to_download = chapters_list

        # Get the chapters to remove from the download list
        remove_chapters = self.get_chapters_range(chapters_list, chapters_to_remove)

        for i in remove_chapters:
            chapters_to_download.remove(i)
        return [c for c in chapters if c["data"]["attributes"]["chapter"] in chapters_to_download]



class MDownloader(MDownloaderBase):

    def __init__(self) -> None:
        super().__init__()

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
