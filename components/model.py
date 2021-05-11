import os
import json
import time

import requests
from requests.models import Response

from .constants import ImpVar
from .errors import MDownloaderError, MdRequestError
from .exporter import ArchiveExporter
from .languages import getLangMD


class AuthMD:

    def __init__(self) -> None:
        self.session = requests.Session()
        self.successful_login = False
        self.token_file = '.mdauth'
        self.auth_url = f'{ImpVar.MANGADEX_API_URL}/auth'

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
        self.manga_id = ''
        self.chapter_id = ''
        self.title = ''
        self.prefix = ''
        self.name = ''
        self.route = ''

    def formatArgs(self, args):
        """AI is creating summary for formatArgs

        Args:
            args (argparse.ArgumentParser.argument_parser): Assign argparse args instance properties.
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
        if save_format in ('zip', 'cbz'):
            return save_format

    def formatRange(self, range_download: str) -> bool:
        if range_download == 'range' and self.download_type in ('title', 'manga'):
            return True
        else:
            return False

    def formatAdd(self, add_data: str) -> bool:
        if add_data == 'add':
            return True
        else:
            return False

    def formatCovers(self, covers: str) -> bool:
        if covers == 'save':
            print('Covers are yet to be supported by the MangaDex api.')
            return False
            return True
        else:
            return False

    def formatFolder(self, make_folder: str) -> bool:
        if make_folder == 'yes':
            return True
        else:
            return False

    # Get the id and download type from the url
    def getIdFromUrl(self, url: str) -> str:
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
        self.route = os.path.join(self.directory, self.title)

    # Connect to the API and get the data
    def requestData(self, download_id: str, download_type: str, get_chapters: bool=0, **params: dict) -> Response:
        if download_type in ('rss', 'cover'):
            url = download_id
        else:
            url = f'{ImpVar.MANGADEX_API_URL}/{download_type}/{download_id}'

        if get_chapters:
            if download_type in ('group', 'user'):
                url = f'{ImpVar.MANGADEX_API_URL}/chapter'
            else:
                url = f'{url}/feed'

        response = self.session.get(url, params=params)
        # print(response.url)
        return response

    def checkResponseError(self, download_id: str, download_type: str, response: Response, data: dict) -> None:
        if response.status_code != 200:
            raise MdRequestError(download_id, download_type, response, data)

    # Convert response data into a parsable json
    def convertJson(self, download_id: str, download_type: str, response: Response) -> dict:
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise MdRequestError(download_id, download_type, response)

        self.checkResponseError(download_id, download_type, response, data)

        return data

    # Check if all the images are downloaded
    def checkExist(self, pages: list) -> bool:
        # Only image files are counted
        if isinstance(self.exporter, ArchiveExporter):
            zip_count = [i for i in self.exporter.archive.namelist() if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        else:
            zip_count = [i for i in os.listdir(self.exporter.folder_path) if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

        if len(pages) == len(zip_count):
            return True

        return False

    def existSaveJson(self) -> None:
        if self.type_id in (1, 2, 3):
            self.title_json.chapters(self.chapter_data["data"])
            self.title_json.core()
            if self.type_id in (2, 3):
                self.account_json.chapters(self.chapter_data["data"])
                self.account_json.core()

    def existsBeforeDownload(self, exists: dict) -> None:
        if exists:
            # Add chapter data to the json for title, group or user downloads
            self.existSaveJson()
            self.exporter.close()
            raise MDownloaderError('File already downloaded.')

    def existsAfterDownload(self, downloaded_all: dict) -> None:
        # If all the images are downloaded, save the json file with the latest downloaded chapter      
        if downloaded_all:
            self.existSaveJson()

        # Close the archive
        self.exporter.close()
    
    def waitingTime(self, time_to_wait: int=ImpVar.GLOBAL_TIME_TO_WAIT, print_message: bool=True):
        if time_to_wait == 0:
            return
        
        if time_to_wait == 1:
            sentence_ending = '.'
        else:
            sentence_ending = 's.'

        if print_message:
            print(f"Waiting {time_to_wait} second{sentence_ending}")
        time.sleep(time_to_wait)
