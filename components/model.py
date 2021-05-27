import getpass
import gzip
import html
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Union

import requests
from requests.models import Response

from .constants import ImpVar
from .errors import MDownloaderError, MDRequestError
from .languages import getLangMD



class MDownloaderBase:

    def __init__(self) -> None:
        self.id = ''
        self.debug = False
        self.download_type = ''

        self.data = {}
        self.manga_data = {}
        self.chapters = []
        self.chapters_data = []
        self.chapter_data = {}
        self.title_json = None
        self.account_json = None
        self.chapter_prefix_dict = {}
        self.exporter = None
        self.title_json_data = []
        self.account_json_data = []
        self.params = {}
        self.cache_json = {}

        self.type_id = 0
        self.exporter_id = 1
        self.manga_id = ''
        self.chapter_id = ''
        self.title = ''
        self.prefix = ''
        self.name = ''
        self.route = ''
        self.chapter_limit = 500
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
        self.cdn_url = f'{ImpVar.MANGADEX_CDN_URL}/covers'



class ApiMD:

    def __init__(self, model) -> None:
        self.model = model
        self.session = requests.Session()

    def postData(self, url: str, post_data: dict) -> Response:
        response = self.session.post(url, json=post_data)
        return response

    def requestData(self, url: str, get_chapters: bool=0, **params: dict) -> Response:
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

    def checkResponseError(self, download_id: str, download_type: str, response: Response, data: dict) -> None:
        """Check if the response status code is 200 or not.

        Args:
            download_id (str): The id of the download.
            download_type (str): The type of download.
            response (Response): Response data returned by the api.
            data (dict): Response data as a dict.

        Raises:
            MDRequestError: The server didn't return a 200.
        """
        if response.status_code != 200:
            raise MDRequestError(download_id, download_type, response, data)

    def convertJson(self, download_id: str, download_type: str, response: Response) -> dict:
        """Convert response data into a parsable json.

        Args:
            download_id (str): The id of the download.
            download_type (str): The type of download.
            response (Response): Response data returned by the api.

        Raises:
            MDRequestError: The response is not JSON serialisable.

        Returns:
            dict: The response as a dict object.
        """
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise MDRequestError(download_id, download_type, response)

        self.checkResponseError(download_id, download_type, response, data)

        return data



class AuthMD:

    def __init__(self, model) -> None:
        self.model = model
        self.successful_login = False
        self.token_file = Path('').joinpath(ImpVar.TOKEN_FILE)
        self.auth_url = f'{self.model.api_url}/auth'    

    def saveSession(self, token: dict) -> None:
        """Save the session and refresh tokens.

        Args:
            token (dict): Token returned by the api.
        """
        with open(self.token_file, 'w') as login_file:
            login_file.write(json.dumps(token, indent=4))

    def refreshToken(self, token: dict) -> bool:
        """Use the refresh token to get a new session token.

        Args:
            token (dict): Token returned by the api.

        Returns:
            bool: If login using the refresh token or account was successful.
        """
        refresh_token = {"token": token["refresh"]}
        refresh_response = self.model.api.postData(f'{self.auth_url}/refresh', refresh_token)

        if refresh_response.status_code == 200:
            refresh_data = refresh_response.json()["token"]

            self.saveSession(refresh_data)
            return True
        elif refresh_response.status_code in (401, 403):
            print("Couldn't login using refresh token, login using your account.")
            return self.loginUsingDetails()
        else:
            print("Couldn't refresh token.")
            return False

    def checkLogin(self, token: dict) -> bool:
        """Try login using saved session token.

        Args:
            token (dict): Token returned by the api.

        Returns:
            bool: If login using the session token successful.
        """
        auth_check_response = self.model.api.session.get(f'{self.auth_url}/check')

        if auth_check_response.status_code == 200:
            auth_data = auth_check_response.json()

            if auth_data["isAuthenticated"]:
                return True
            else:
                return self.refreshToken(token)

    def loginUsingDetails(self) -> bool:
        """Login using account details.

        Returns:
            bool: If login was successful.
        """
        username = input('Your username: ')
        password = getpass.getpass(prompt='Your password: ', stream=None)

        credentials = {"username": username, "password": password}
        post = self.model.api.postData(f'{self.auth_url}/login', credentials)
        
        if post.status_code == 200:
            token = post.json()["token"]
            self.model.api.session.headers = {'Authorization': f'Bearer {token["session"]}'}
            self.saveSession(token)
            return True
        return False

    def login(self) -> None:
        """Login to MD account using details or saved token."""
        print('Trying to login through the .mdauth file.')

        try:
            with open(self.token_file, 'r') as login_file:
                token = json.load(login_file)

            self.model.api.session.headers = {"Authorization": f'Bearer {token["session"]}'}
            logged_in = self.checkLogin(token)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Couldn't find the file, trying to login using your account.")
            logged_in = self.loginUsingDetails()

        if logged_in:
            self.successful_login = True
            print('Login successful!')
        else:
            print('Login unsuccessful, continuing without being logged in.')



class ProcessArgs:

    def __init__(self, model) -> None:
        self.model = model

    def formatArgs(self, args) -> None:
        """Format the arguments into readable data.

        Args:
            args (argparse.ArgumentParser.parse_args): Command line arguments to parse.
        """
        self.model.id = str(args.id)
        self.model.debug = bool(args.debug)
        self.model.download_type = str(args.type)
        self.language = getLangMD(args.language)
        self.directory = str(args.directory)
        self.save_format = self.archiveExt(args.save_format)
        self.make_folder = self.formatFolder(args.folder)
        self.covers = self.formatCovers(args.covers)
        self.add_data = self.formatAdd(args.json)
        self.range_download = self.formatRange(args.range)
        if args.login: self.model.auth.login()

    def archiveExt(self, save_format: str) -> str:
        """Check if the file extension is accepted. Default: cbz.

        Args:
            save_format (str): The file extension.

        Raises:
            MDownloaderError: The extension chosen isn't allowed.

        Returns:
            str: The file extension.
        """
        if save_format in ('zip', 'cbz'):
            return save_format
        else:
            raise MDownloaderError("This archive save format is not allowed.")

    def formatRange(self, range_download: str) -> bool:
        """Select the chapters to download. Works only on manga downloads. Default: range.

        Args:
            range_download (str): The command line argument.

        Returns:
            bool: True if to download in range, False if not.
        """
        if range_download == 'range' and self.model.download_type == 'manga':
            return True
        else:
            return False

    def formatAdd(self, add_data: str) -> bool:
        """Add the chapter data to the save file/folder. Default: add.

        Args:
            add_data (str): The command line argument.

        Returns:
            bool: True if to save the data, False if not.
        """
        if add_data == 'add':
            return True
        else:
            return False

    def formatCovers(self, covers: str) -> bool:
        """Download manga covers. Works only on manga downloads. Default: skip.

        Args:
            covers (str): The command line argument.

        Returns:
            bool: True if to download the covers, False if not.
        """
        if covers == 'save':
            return True
        else:
            return False

    def formatFolder(self, make_folder: str) -> bool:
        """Download chapters to a folder or file. Default: file.

        Args:
            make_folder (str): The command line argument.

        Returns:
            bool: True if save to folder, False if not.
        """
        if make_folder == 'yes':
            return True
        else:
            return False



class ExistChecker:

    def __init__(self, model) -> None:
        self.model = model

    def checkExist(self, pages: list) -> bool:
        """Check if all the images are downloaded.

        Args:
            pages (list): Array of images from the api.

        Returns:
            bool: True if the amount of pages downloaded match the amount on the api, False if not.
        """
        # Only image files are counted
        if self.model.args.make_folder:
            files_path = os.listdir(self.model.exporter.folder_path)
        else:
            files_path = self.model.exporter.archive.namelist()

        zip_count = [i for i in files_path if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

        if len(pages) == len(zip_count):
            return True
        return False

    def existSaveJson(self) -> None:
        """Save the chapter data to the data json and save the json."""
        if self.model.type_id in (1, 2, 3) or self.model.manga_download:
            self.model.title_json.core()
            if self.model.type_id in (2, 3):
                self.model.manga_download = False
                self.model.account_json.core()
                self.model.manga_download = True

    def existsBeforeDownload(self, exists: bool) -> None:
        """Check if the chapter exists before downloading the images.

        Args:
            exists (bool): If the chapter exists or not.

        Raises:
            MDownloaderError: The chapter has already been downloaded.
        """
        if exists:
            # Add chapter data to the json for title, group or user downloads
            self.existSaveJson()
            self.model.exporter.close()
            raise MDownloaderError('File already downloaded.')

    def existsAfterDownload(self, downloaded_all: bool) -> None:
        """Check if all the images have been downloaded.

        Args:
            downloaded_all (bool): If all the images have been downloaded or not.
        """
        # If all the images are downloaded, save the json file with the latest downloaded chapter      
        if downloaded_all:
            self.existSaveJson()

        # Close the archive
        self.model.exporter.close()



class DataFormatter:

    def __init__(self, model) -> None:
        self.model = model

    def stripIllegal(self, name: str) -> str:
        """Remove illegal characters from the specified name.

        Args:
            name (str): Name to strip illegal characterss from.

        Returns:
            str: The now-legal name.
        """
        return re.sub(ImpVar.REGEX, '_', html.unescape(name))

    def formatRoute(self) -> None:
        """The route files will be saved to."""
        self.model.route = os.path.join(self.model.args.directory, self.model.title)

    def formatTitle(self, data: dict) -> str:
        """Remove illegal characters from the manga title.

        Args:
            data (dict): The manga data returned from the api.

        Returns:
            str: The formatted title.
        """
        attributes = data["data"]["attributes"]

        if 'en' in attributes["title"]:
            title = attributes["title"]["en"]
        elif attributes["originalLanguage"] in attributes["title"]:
            title = attributes["title"]["originalLanguage"]
        else:
            title = next(iter(attributes["title"]))

        title = self.stripIllegal(title).rstrip(' .')
        self.model.title = title
        self.formatRoute()
        return title

    def getIdFromUrl(self, url: str) -> Tuple[str, str]:
        """Get the download type and if from the url.

        Args:
            url (str): The url to parse.

        Returns:
            Tuple[str, str]: The id and type from the url.
        """
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



class CacheRead:

    def __init__(self, model) -> None:
        self.model = model
        self.cache_refresh_time = ImpVar.CACHE_REFRESH_TIME
        self.root = Path(ImpVar.CACHE_PATH)
        self.root.mkdir(parents=True, exist_ok=True)

    def saveCacheData(self, cache_time: Union[str, datetime], download_id: str, data: dict={}, chapters: list=[], covers: list=[]) -> None:
        """Save the data to the cache.

        Args:
            cache_time (str): The time the cache was saved.
            download_id (str): The id of the data to cache.
            data (dict, optional): The data to cache. Defaults to {}.
            chapters (list, optional): The chapters to cache. Defaults to [].
            covers (list, optional): The covers of the manga.. Defaults to [].
        """
        cache_json = {"cache_date": str(cache_time), "data": data, "covers": covers, "chapters": chapters}

        with gzip.open(self.root.joinpath(f'{download_id}').with_suffix('.json.gz'), 'w') as cache_json_fp:
            cache_json_fp.write(json.dumps(cache_json, indent=4, ensure_ascii=False).encode('utf-8'))

    def loadCacheData(self, download_id: str) -> dict:
        """Load the cache data.

        Args:
            download_id (str): The id of the cache data to load.

        Returns:
            dict: The cache's data.
        """
        try:
            with gzip.open(self.root.joinpath(f'{download_id}').with_suffix('.json.gz'), 'r') as cache_json_fp:
                cache_json = json.loads(cache_json_fp.read().decode('utf-8'))
            return cache_json
        except (FileNotFoundError, json.JSONDecodeError, gzip.BadGzipFile):
            return {}

    def checkCacheTime(self, cache_json: dict) -> bool:
        """Check if the cache needs to be refreshed.

        Args:
            cache_json (dict): The cache data.

        Returns:
            bool: If a refresh is needed.
        """
        refresh = True
        if cache_json:
            timestamp = datetime.strptime(cache_json["cache_date"], "%Y-%m-%d %H:%M:%S.%f") + timedelta(hours=self.cache_refresh_time)
            if datetime.now() >= timestamp:
                pass
            refresh = False

        if refresh:
            if self.model.debug: print('Refreshing cache.')
        else:
            if self.model.debug: print('Using cache data.')
        return refresh



class Filtering:

    def __init__(self, model) -> None:
        self.model = model
        self.root = Path("")
        self._group_blacklist_file = self.root.joinpath(ImpVar.GROUP_BLACKLIST_FILE)
        self._group_whitelist_file = self.root.joinpath(ImpVar.GROUP_WHITELIST_FILE)
        self._user_blacklist_file = self.root.joinpath(ImpVar.USER_BLACKLIST_FILE)
        self._user_userlist_file = self.root.joinpath(ImpVar.USER_WHITELIST_FILE)

        self.group_blacklist = self.readFile(self._group_blacklist_file)
        self.group_whitelist = self.readFile(self._group_whitelist_file)
        self.user_blacklist = self.readFile(self._user_blacklist_file)
        self.user_whitelist = self.readFile(self._user_userlist_file)

    def readFile(self, file_path):
        try:
            with open(file_path, 'r') as fp:
                filter_list = [line.rstrip('\n') for line in fp.readlines()]
                return filter_list
        except FileNotFoundError:
            return []



class MDownloader(MDownloaderBase):

    def __init__(self) -> None:
        super().__init__()

        self.api = ApiMD(self)
        self.auth = AuthMD(self)
        self.args = ProcessArgs(self)
        self.formatter = DataFormatter(self)
        self.exist = ExistChecker(self)
        self.cache = CacheRead(self)
        self.filter = Filtering(self)

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
