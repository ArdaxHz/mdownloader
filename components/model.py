import os
import json

import requests
from requests.models import Response

from .constants import ImpVar
from .errors import MdDownloaderError, MdRequestError
from .exporter import ArchiveExporter
from .languages import getLangMD


class AuthMD:

    def __init__(self) -> None:
        self.session = requests.Session()
        self.successful_login = False
        self.token_file = '.mdauth'

    
    def saveSession(self, token):
        with open(self.token_file, 'w') as login_file:
            login_file.write(json.dumps(token, indent=4))


    def refreshToken(self, url, token):
        refresh_token = {"token": token["refresh"]}
        refresh_response = self.session.post(f'{url}/refresh', json=refresh_token)


        if refresh_response.status_code == 200:
            refresh_data = refresh_response.json()["token"]

            self.saveSession(refresh_data)
            print('Login successful!')
        elif refresh_response.status_code in (401, 403):
            print("Couldn't login using refresh token, login using your account.")
            self.loginUsingDetails()
        else:
            print("Couldn't refresh token.")

    
    def checkLogin(self, token):
        url = f'{ImpVar.MANGADEX_API_URL}/auth'
        auth_check_response = self.session.get(f'{url}/check')

        if auth_check_response.status_code == 200:
            auth_data = auth_check_response.json()

            if auth_data["isAuthenticated"]:
                return True
            else:
                self.refreshToken(url, token)


    def loginUsingDetails(self):
        username = input('Your username: ')
        password = input('Your password: ')

        url = f"{ImpVar.MANGADEX_API_URL}/auth/login"
        credentials = {"username": username, "password": password}
        post = self.session.post(url, json=credentials)
        
        if post.status_code == 200:
            print('Login successful!')

            token = post.json()["token"]
            self.session.headers = {'Authorization': f'Bearer {token["session"]}'}
            self.saveSession(token)
            self.successful_login = True
        else:
            print('Login unsuccessful, continuing without being logged in.')

        return


    def login(self):
        print('Trying to login through the .mdauth file.')

        try:
            with open(self.token_file, 'r') as login_file:
                token_file = json.load(login_file)

            token = token_file
            self.session.headers = {"Authorization": f'Bearer {token["session"]}'}
            print(self.session.headers)

            logged_in = self.checkLogin(token)

            if logged_in:
                self.successful_login = True

                print('Login successful!')
        except (FileNotFoundError, json.JSONDecodeError):
            print("Couldn't find the file, trying to login using your account.")
            self.loginUsingDetails()



class MDownloader(AuthMD):

    def __init__(self) -> None:
        super().__init__()
        self.data = {}
        self.chapters_data = []
        self.chapter_data = {}
        self.title_json = None
        self.account_json = None
        self.chapter_prefix_dict = {}
        self.exporter = None

        self.type_id = 0
        self.chapter_id = ''
        self.title = ''
        self.prefix = ''
        self.name = ''


    def formatArgs(self, args):
        self.id = args.id
        self.download_type = args.type
        self.language = getLangMD(args.language)
        self.route = args.directory
        self.save_format = self.archiveExt(args.save_format)
        self.make_folder = self.formatFolder(args.folder)
        self.covers = self.formatCovers(args.covers)
        self.add_data = self.formatAdd(args.json)
        self.range_download = self.formatRange(args.range)


    def archiveExt(self, save_format):
        if save_format in ('zip', 'cbz'):
            return save_format


    def formatRange(self, range_download):
        if range_download == 'range':
            return True
        else:
            return False


    def formatAdd(self, add_data):
        if add_data == 'add':
            return True
        else:
            return False


    def formatCovers(self, covers):
        if covers == 'save':
            print('Covers are yet to be supported by the MangaDex api.')
            return False
            return True
        else:
            return False


    def formatFolder(self, make_folder):
        if make_folder == 'yes':
            return True
        else:
            return False


    # Get the id and download type from the url
    def getIdFromUrl(self, url):
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
    

    def formatRoute(self):
        self.route = os.path.join(self.route, self.title)
    

    # Connect to the API and get the data
    def requestData(self, download_id: str, download_type: str, get_chapters: bool=0, **params) -> Response:
        if download_type == 'rss':
            url = self.id
        else:
            url = f'{ImpVar.MANGADEX_API_URL}/{download_type}/{download_id}'

        if get_chapters:
            if download_type in ('group', 'user'):
                url = f'{ImpVar.MANGADEX_API_URL}/chapter'
            else:
                url = f'{url}/feed'

        response = self.session.get(url, params=params)
        return response


    # Convert response data into a parsable json
    def getData(self, response: Response) -> dict:
        if response.status_code == 204:
            raise MdRequestError(response)

        data = response.json()

        if response.status_code != 200:
            raise MdRequestError(response, data)

        return data


    # Check if all the images are downloaded
    def checkExist(self, pages: list) -> bool:
        exists = 0

        # Only image files are counted
        if isinstance(self.exporter, ArchiveExporter):
            zip_count = [i for i in self.exporter.archive.namelist() if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        else:
            zip_count = [i for i in os.listdir(self.exporter.folder_path) if i.endswith(('.png', '.jpg', '.jpeg', '.gif'))]

        if len(pages) == len(zip_count):
            exists = 1

        return exists


    def existsBeforeDownload(self, exists):
        if exists:
            if self.type_id == 1:
                self.title_json.core()
            elif self.type_id == 2:
                self.account_json.core()
            self.exporter.close()
            raise MdDownloaderError('File already downloaded.')


    def existsAfterDownload(self, downloaded_all):
        # If all the images are downloaded, save the json file with the latest downloaded chapter      
        if downloaded_all:
            if self.type_id == 1:
                self.title_json.core()
            elif self.type_id == 2:
                self.account_json.core()
        
        # Close the archive
        self.exporter.close()
        del self.exporter
        return
