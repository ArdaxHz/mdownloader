import re



class ImpVar:
    scheme = 'https'
    domain = 'mangadex'
    tld = 'org'

    GLOBAL_TIME_TO_WAIT = 2

    MANGADEX_URL = '{}://{}.{}'.format(scheme, domain, tld)
    MANGADEX_API_URL = '{}://api.{}.{}'.format(scheme, domain, tld)

    API_MESSAGE = 'The max. requests allowed are 1500/10min for the API and 600/10min for everything else. You have to wait 10 minutes or you will get your IP banned.'

    MD_URL = re.compile(r'(?:https:\/\/)?(?:www.|api.)?(?:mangadex\.org\/)(?:api\/)?(?:v\d\/)?(title|chapter|manga|group|user|list)(?:\/)((?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})|(?:\d+))')
    MD_IMAGE_URL = re.compile(r'(?:https:\/\/)?(?:(?:(?:s\d|www)\.)?(?:mangadex\.org\/)|.+\.mangadex\.network(?::\d+)?\/)(?:.+)?(?:data\/)([a-f0-9]+)(?:\/)((?:\w+|\w+-\w+)\.(?:jpg|jpeg|png|gif))')
    MD_RSS_URL = re.compile(r'(?:https:\/\/)?(?:www.)?(?:mangadex\.org\/)(rss)(?:\/)([A-Za-z0-9]+)')
    URL_RE = re.compile(r'(?:https|ftp|http)(?::\/\/)(?:.+)')

    REGEX = r'[\\\\/:*?"<>|]'
    UUID_REGEX = r'[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}'
    FILE_NAME_REGEX = r'(?P<title>.+?)(?:\s\[(?P<language>[a-zA-Z]+)\])?\s-\s(?P<prefix>[c-z])?(?P<chapter>\S+)(?:\s\((?:v)(?P<volume>\S+?)\))?\s?(?:.+)(?:\[(?P<group>.+)\])(?:\{(?:v)(?P<version>\d)\})?(?:\.(?P<extension>.+))?'
