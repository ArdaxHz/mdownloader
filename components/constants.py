from .__version__ import __version__

__https = 'https://'
__mangadex = 'mangadex.org'

MANGADEX_URL = '{}{}/{}/{}'.format(__https, __mangadex, {}, {})
MANGADEX_API_URL = '{}{}/api/v2/{}/{}'.format(__https, __mangadex, {}, {})

HEADERS = {'User-Agent': f'mDownloader/{__version__}'}
REGEX = '[\\\\/:*?"<>|]'
