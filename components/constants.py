import os
import re
from dotenv import load_dotenv

load_dotenv()



class ImpVar:
    scheme = 'https'
    domain = 'mangadex'
    tld = 'org'

    MANGAPLUS_GROUP_ID = '4f1de6a2-f0c5-4ac5-bce5-02c7dbb67deb'

    TOKEN_FILE = os.getenv("TOKEN_FILE", '.mdauth')
    CACHE_PATH = os.getenv("CACHE_PATH", '.cache')

    GLOBAL_TIME_TO_WAIT = int(os.getenv("GLOBAL_TIME_TO_WAIT", 1))
    RETRY_MAX_TIMES = int(os.getenv("IMAGE_RETRY_MAX_TIMES", 3))
    TIME_TO_SLEEP = int(os.getenv("IMAGE_RETRY_SLEEP", 3))
    CACHE_REFRESH_TIME = int(os.getenv("CACHE_REFRESH_TIME", 24))

    GROUP_BLACKLIST_FILE = os.getenv("GROUP_BLACKLIST_FILE", 'group_blacklist.txt')
    GROUP_WHITELIST_FILE = os.getenv("GROUP_WHITELIST_FILE", 'group_whitelist.txt')
    USER_BLACKLIST_FILE = os.getenv("USER_BLACKLIST_FILE", 'user_blacklist.txt')
    USER_WHITELIST_FILE = os.getenv("USER_WHITELIST_FILE", 'user_whitelist.txt')

    MANGADEX_URL = '{}://{}.{}'.format(scheme, domain, tld)
    MANGADEX_API_URL = '{}://api.{}.{}'.format(scheme, domain, tld)
    MANGADEX_CDN_URL = '{}://uploads.{}.{}'.format(scheme, domain, tld)

    API_MESSAGE = r"The global requests rate limit is 5/sec for the API. This program has waiting time to avoid bans, but it's not 100% guaranteed."

    MD_URL = re.compile(r'(?:https:\/\/)?(?:www.|api.)?(?:mangadex\.org\/)(?:api\/)?(?:v\d\/)?(title|chapter|manga|group|user|list)(?:\/)((?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})|(?:\d+))')
    MD_IMAGE_URL = re.compile(r'(?:https:\/\/)?(?:(?:(?:s\d|www)\.)?(?:mangadex\.org\/)|.+\.mangadex\.network(?::\d+)?\/)(?:.+)?(?:data\/)([a-f0-9]+)(?:\/)((?:\w+|\w+-\w+)\.(?:jpg|jpeg|png|gif))')
    MD_FOLLOWS_URL = re.compile(r'(?:https:\/\/)?(?:www.|api.)?(?:mangadex\.org\/)(?:api\/)?(?:v\d\/)?(?:user)(?:\/)(follows)(?:.+)')
    MD_RSS_URL = re.compile(r'(?:https:\/\/)?(?:www.)?(?:mangadex\.org\/)(rss)(?:\/)([A-Za-z0-9]+)')
    URL_RE = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')

    REGEX = r'[\\\\/:*?"<>|]'
    UUID_REGEX = r'[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}'
    FILE_NAME_REGEX = r'(?P<title>.+?)(?:\s\[(?P<language>[a-zA-Z]+)\])?\s-\s(?P<prefix>[c-z])?(?P<chapter>\S+)(?:\s\((?:v)(?P<volume>\S+?)\))?\s?(?:.+)(?:\[(?P<group>.+)\])(?:\{(?:v)(?P<version>\d)\})?(?:\.(?P<extension>zip|cbz))?'
