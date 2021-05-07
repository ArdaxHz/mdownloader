import json
import os
from components.errors import MDownloaderError
import http
import pickle
import random
import re
from typing import Union

import requests
from requests.models import Response
from .__version__ import __version__
from .languages import getLangMD



class Headers:
    USER_AGENT_LIST = [
        #Chrome
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        #Firefox
        'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
    ]

    def get_header():
        return random.choice(Headers.USER_AGENT_LIST)



class ImpVar:
    scheme = 'https'
    domain = 'mangadex'
    tld = 'org'

    MANGADEX_URL = '{}://{}.{}'.format(scheme, domain, tld)
    MANGADEX_API_URL = '{}://api.{}.{}'.format(scheme, domain, tld)

    API_MESSAGE = 'The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.'

    MD_URL = re.compile(r'(?:https:\/\/)?(?:www.|api.)?(?:mangadex\.org\/)(?:api\/)?(?:v\d\/)?(title|chapter|manga|group|user)(?:\/)((?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})|(?:\d+))')
    MD_IMAGE_URL = re.compile(r'(?:https:\/\/)?(?:(?:(?:s\d|www)\.)?(?:mangadex\.org\/)|.+\.mangadex\.network(?::\d+)?\/)(?:.+)?(?:data\/)([a-f0-9]+)(?:\/)((?:\w+|\d+-\w+)\.(?:jpg|jpeg|png|gif))')
    MD_RSS_URL = re.compile(r'(?:https:\/\/)?(?:www.)?(?:mangadex\.org\/)(rss)(?:\/)([A-Za-z0-9]+)')
    URL_RE = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')

    HEADERS = {'User-Agent': Headers.get_header()}

    REGEX = r'[\\\\/:*?"<>|]'
    UUID_REGEX = r'[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}'
    FILE_NAME_REGEX = r'(?P<title>.+?)(?:\s\[(?P<language>[a-zA-Z]+)\])?\s-\s(?P<prefix>[c-z])?(?P<chapter>\S+)(?:\s\((?:v)(?P<volume>\S+?)\))?\s?(?:.+)(?:\[(?P<group>.+)\])(?:\{(?:v)(?P<version>\d)\})?(?:\.(?P<extension>.+))?'



class AuthMD:

    def __init__(self) -> None:
        self.session = requests.Session()
        self.successful_login = False
        self.token_file = '.mdauth'


    def loginUsingDetails(self):
        print("Couldn't find the file, trying to login using your account.")
        username = input('Your username: ')
        password = input('Your password: ')

        url = f"{ImpVar.MANGADEX_API_URL}/auth/login"

        credentials = {"username": username, "password": password}

        post = self.session.post(url, json=credentials)
        
        if post.status_code in range(200, 300):
            print('Login successful!')

            token = post.json()["token"]["session"]

            self.session.headers.update({'Authorization': f'Bearer {token}'})

            with open(self.token_file, 'w') as login_file:
                login_file.write(json.dumps({'token': token}, indent=4))

            self.successful_login = True
        else:
            print('Login unsuccessful, continuing without being logged in.')

        return
    
    def login(self):
        print('Trying to login through the .mdauth file.')

        try:
            with open(self.token_file, 'r') as login_file:
                token_file = json.loads(login_file)

            token = token_file["token"]
            self.session.headers.update({'Authorization': f'Bearer {token}'})

            self.successful_login = True
            print('Login successful!')
        except (FileNotFoundError, json.JSONDecodeError):
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
            self.download_type = input_url.group(1)
            self.id = input_url.group(2)
        elif ImpVar.MD_RSS_URL.match(url):
            self.id = url
            self.download_type = 'rss'
        else:
            input_url = ImpVar.MD_IMAGE_URL.match(url)
            self.id = input_url.group(1)
            self.download_type = 'chapter'
    

    # Check if all the images are downloaded
    def checkExist(self, pages: list) -> bool:
        # pylint: disable=unsubscriptable-object
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
            if self.type_id in (1, 2):
                self.title_json.core()
                if self.type_id == 2:
                    self.account_json.core()
            self.exporter.close()
        raise MDownloaderError('File already downloaded.')


    def existsAfterDownload(self, downloaded_all):
        # If all the images are downloaded, save the json file with the latest downloaded chapter
        if downloaded_all and self.type_id in (1, 2):
            self.title_json.core()
            if self.type_id == 2:
                self.account_json.core()
        
        # Close the archive
        self.exporter.close()
        del self.exporter
        return


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
        data = response.json()

        if response.status_code not in range(200, 300):
            error = [e["detail"] for e in data["errors"]]
            error = ', '.join(error)
            error_message = f'Error: {response.status_code}. Detail: {error}'

            raise MDownloaderError(error_message)

        return data