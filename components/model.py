import getpass
import gzip
import html
import json
import multiprocessing
import os
import re
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple, Union

import requests
from requests.models import Response

from .constants import ImpVar
from .errors import MDownloaderError, MDRequestError, NoChaptersError
from .languages import get_lang_md


class MDownloaderMisc:
    def download_message(self, status: bool, download_type: str, name: str) -> None:
        """Print the download message.

        Args:
            status (bool): If the download has started or ended.
            download_type (str): What type of data is being downloaded, chapter, manga, group, user, or list.
            name (str): Name of the chosen download.
        """
        message = "Downloading"
        if status:
            message = f"Finished {message}"

        print(f'{"-"*69}\n{message} {download_type.title()}: {name}\n{"-"*69}')


class MDownloader:
    def __init__(self) -> None:

        self.misc = MDownloaderMisc(self)
        self.title_misc = TitleDownloaderMisc(self)
