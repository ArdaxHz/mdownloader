import os
import re

from dotenv import load_dotenv


load_dotenv()


class ImpVar:
    scheme = "https"
    domain = "mangadex"
    tld = "org"

    TOKEN_FILE = os.getenv("TOKEN_FILE", ".mdauth")
    CACHE_PATH = os.getenv("CACHE_PATH", ".cache")
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "downloads")

    GLOBAL_TIME_TO_WAIT = int(os.getenv("GLOBAL_TIME_TO_WAIT", 2))
    RETRY_MAX_TIMES = int(os.getenv("IMAGE_RETRY_MAX_TIMES", 3))
    TIME_TO_SLEEP = int(os.getenv("IMAGE_RETRY_SLEEP", 3))
    CACHE_REFRESH_TIME = int(os.getenv("CACHE_REFRESH_TIME", 24))

    GROUP_BLACKLIST_FILE = os.getenv("GROUP_BLACKLIST_FILE", "group_blacklist.txt")
    USER_BLACKLIST_FILE = os.getenv("USER_BLACKLIST_FILE", "user_blacklist.txt")

    ARCHIVE_EXTENSION = os.getenv("ARCHIVE_EXTENSION", "cbz")

    MANGADEX_URL = "{}://{}.{}".format(scheme, domain, tld)
    MANGADEX_API_URL = "{}://api.{}.{}".format(scheme, domain, tld)
    MANGADEX_CDN_URL = "{}://uploads.{}.{}".format(scheme, domain, tld)

    API_MESSAGE = r"The global requests rate limit is 5/sec for the API. This downloader has measures in place to avoid bans, but it's not guaranteed."

    MD_URL = re.compile(
        r"(?:https:\/\/)?(?:www.|api.)?(?:mangadex\.org\/)(?:api\/)?(?:v\d\/)?(title|chapter|manga|group|user|list)(?:\/)((?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})|(?:\d+))"
    )
    MD_IMAGE_URL = re.compile(
        r"(?:https:\/\/)?(?:(?:(?:s\d|www)\.)?(?:mangadex\.org\/)|.+\.mangadex\.network(?::\d+)?\/)(?:.+)?(?:data\/)([a-f0-9]+)(?:\/)((?:\w+|\w+-\w+)\.(?:jpg|jpeg|png|gif))"
    )
    MD_FOLLOWS_URL = re.compile(
        r"(?:https:\/\/)?(?:www.|api.)?(?:mangadex\.org\/)(?:api\/)?(?:v\d\/)?(?:user|titles)(?:\/)(follows|feed)"
    )
    MD_RSS_URL = re.compile(r"(?:https:\/\/)?(?:www.)?(?:mangadex\.org\/)(rss)(?:\/)([A-Za-z0-9]+)")

    URL_RE = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    CHARA_REGEX = r'[\\\\/:*?"<>|]'
    UUID_REGEX = r"[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}"
    FILE_NAME_REGEX = r"(?P<title>.+?)(?:\s\[(?P<language>[a-zA-Z]+)\])?\s-\s(?P<prefix>[c-z])?(?P<chapter>\S+)(?:\s\((?:v)(?P<volume>\S+?)\))?\s?(?:.+)(?:\[(?P<group>.+)\])(?:\{(?:v)(?P<version>\d)\})?(?:\.(?P<extension>zip|cbz))?"
