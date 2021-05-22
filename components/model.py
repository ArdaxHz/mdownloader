import html
import os
import json
import re
import time
from typing import Tuple

import requests
from requests.models import Response

from .constants import ImpVar
from .errors import MDownloaderError, MdRequestError
from .languages import getLangMD


class AuthMD:

    def __init__(self) -> None:
        self.session = requests.Session()
        self.successful_login = False
        self.token_file = '.mdauth'
        self.api_url = ImpVar.MANGADEX_API_URL
        self.auth_url = f'{self.api_url}/auth'

    def postData(self, url: str, post_data: dict) -> Response:
        response = self.session.post(url, json=post_data)
        return response

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
        refresh_response = self.postData(f'{self.auth_url}/refresh', refresh_token)

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
        auth_check_response = self.session.get(f'{self.auth_url}/check')

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
        password = input('Your password: ')

        credentials = {"username": username, "password": password}
        post = self.postData(f'{self.auth_url}/login', credentials)
        
        if post.status_code == 200:
            token = post.json()["token"]
            self.session.headers = {'Authorization': f'Bearer {token["session"]}'}
            self.saveSession(token)

            return True
        
        return False

    def login(self) -> None:
        """Login to MD account using details or saved token."""
        print('Trying to login through the .mdauth file.')

        try:
            with open(self.token_file, 'r') as login_file:
                token_file = json.load(login_file)

            token = token_file
            self.session.headers = {"Authorization": f'Bearer {token["session"]}'}
            print(self.session.headers)

            logged_in = self.checkLogin(token)
        except (FileNotFoundError, json.JSONDecodeError):
            print("Couldn't find the file, trying to login using your account.")
            logged_in = self.loginUsingDetails()

        if logged_in:
            self.successful_login = True
            print('Login successful!')
        else:
            print('Login unsuccessful, continuing without being logged in.')



class MDownloader(AuthMD):

    def __init__(self) -> None:
        super().__init__()
        self.group_user_list_data = {}
        self.manga_data = {}
        self.chapters_data = []
        self.chapter_data = {}
        self.title_json = None
        self.account_json = None
        self.chapter_prefix_dict = {}
        self.exporter = None
        self.title_json_data = []
        self.account_json_data = []

        self.type_id = 0
        self.exporter_id = 1
        self.manga_id = ''
        self.chapter_id = ''
        self.title = ''
        self.prefix = ''
        self.name = ''
        self.route = ''

        self.mdh_url = f'{self.api_url}/at-home/server'
        self.chapter_api_url = f'{self.api_url}/chapter'
        self.manga_api_url = f'{self.api_url}/manga'
        self.group_api_url = f'{self.api_url}/group'
        self.user_api_url = f'{self.api_url}/user'
        self.list_api_url = f'{self.api_url}/list'
        self.cover_api_url = f'{self.api_url}/cover'
        self.legacy_url = f'{self.api_url}/legacy/mapping'
        self.report_url = 'https://api.mangadex.network/report'
        self.cdn_url = 'https://uploads.mangadex.org/covers'

    def formatArgs(self, args) -> None:
        """Format the arguments into readable data.

        Args:
            args (argparse.ArgumentParser.parse_args): Command line arguments to parse.
        """
        self.id = args.id
        self.download_type = args.type
        self.language = getLangMD(args.language)
        self.directory = args.directory
        self.save_format = self.archiveExt(args.save_format)
        self.make_folder = self.formatFolder(args.folder)
        self.covers = self.formatCovers(args.covers)
        self.add_data = self.formatAdd(args.json)
        self.range_download = self.formatRange(args.range)

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
        if range_download == 'range' and self.download_type == 'manga':
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
        if covers == 'save' and self.download_type == 'manga':
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
        elif ImpVar.MD_RSS_URL.match(url):
            id_from_url = url
            download_type_from_url = 'rss'
        else:
            input_url = ImpVar.MD_IMAGE_URL.match(url)
            id_from_url = input_url.group(1)
            download_type_from_url = 'chapter'

        return id_from_url, download_type_from_url

    def formatRoute(self) -> None:
        """The route files will be saved to."""
        self.route = os.path.join(self.directory, self.title)

    def formatTitle(self, data: dict) -> str:
        """Remove illegal characters from the manga title.

        Args:
            data (dict): The manga data returned from the api.

        Returns:
            str: The formatted title.
        """
        title = data["data"]["attributes"]["title"]["en"]
        title = re.sub(ImpVar.REGEX, '_', html.unescape(title)).rstrip(' .')
        self.title = title
        self.formatRoute()
        return title

    def requestData(self, url: str, get_chapters: bool=0, **params: dict) -> Response:
        """Connect to the API and get the response.

        Args:
            url (str): Download url.
            get_chapters (bool, optional): If the download is to get the chapters. Defaults to 0.

        Returns:
            Response: The response of the resquest.
        """
        if get_chapters:
            if self.type_id in ('group', 'user'):
                url = self.chapter_api_url
            else:
                url = f'{url}/feed'

        response = self.session.get(url, params=params)
        # print(response.url)
        return response

    def checkResponseError(self, download_id: str, download_type: str, response: Response, data: dict) -> None:
        """Check if the response status code is 200 or not.

        Args:
            download_id (str): The id of the download.
            download_type (str): The type of download.
            response (Response): Response data returned by the api.
            data (dict): Response data as a dict.

        Raises:
            MdRequestError: The server didn't return a 200.
        """
        if response.status_code != 200:
            raise MdRequestError(download_id, download_type, response, data)

    def convertJson(self, download_id: str, download_type: str, response: Response) -> dict:
        """Convert response data into a parsable json.

        Args:
            download_id (str): The id of the download.
            download_type (str): The type of download.
            response (Response): Response data returned by the api.

        Raises:
            MdRequestError: The response is not JSON serialisable.

        Returns:
            dict: The response as a dict object.
        """
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise MdRequestError(download_id, download_type, response)

        self.checkResponseError(download_id, download_type, response, data)

        return data

    def checkExist(self, pages: list) -> bool:
        """Check if all the images are downloaded.

        Args:
            pages (list): Array of images from the api.

        Returns:
            bool: True if the amount of pages downloaded match the amount on the api, False if not.
        """
        # Only image files are counted
        if self.make_folder:
            files_path = os.listdir(self.exporter.folder_path)
        else:
            files_path = self.exporter.archive.namelist()

        zip_count = [i for i in files_path if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

        if len(pages) == len(zip_count):
            return True

        return False

    def existSaveJson(self) -> None:
        """Save the chapter data to the data json and save the json."""
        if self.type_id in (1, 2, 3):
            self.title_json.chapters(self.chapter_data["data"])
            self.title_json.core()
            if self.type_id in (2, 3):
                self.account_json.chapters(self.chapter_data["data"])
                self.account_json.core()

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
            self.exporter.close()
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
        self.exporter.close()
    
    def waitingTime(self, time_to_wait: int=ImpVar.GLOBAL_TIME_TO_WAIT, print_message: bool=True) -> None:
        """Wait a certain amount of time before continuing.

        Args:
            time_to_wait (int, optional): The time to wait. Defaults to ImpVar.GLOBAL_TIME_TO_WAIT.
            print_message (bool, optional): If to print the waiting message. Defaults to True.
        """
        if time_to_wait == 0:
            return

        if time_to_wait == 1:
            sentence_ending = '.'
        else:
            sentence_ending = 's.'

        if print_message:
            print(f"Waiting {time_to_wait} second{sentence_ending}")
        time.sleep(time_to_wait)
