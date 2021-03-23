from .__version__ import __version__

scheme = 'https'
domain = 'mangadex'
tld = 'org'

MANGADEX_URL = '{}://{}.{}/{}/{}/'.format(scheme, domain, tld, {}, {})
MANGADEX_API_URL = '{}://api.{}.{}/v2/{}/{}/'.format(scheme, domain, tld, {}, {})

HEADERS = {'User-Agent': f'mDownloader/{__version__}'}
REGEX = r'[\\\\/:*?"<>|]'

FILE_NAME_REGEX = r'(?P<title>.+?)(?:\s\[(?P<language>[a-zA-Z]+)\])?\s-\s(?P<prefix>[c-z])?(?P<chapter>\S+)(?:\s\((?:v)(?P<volume>\S+?)\))?\s?(?:.+)(?:\[(?P<group>.+)\])(?:\{(?:v)(?P<version>\d)\})?(?:\.(?P<extension>.+))?'
