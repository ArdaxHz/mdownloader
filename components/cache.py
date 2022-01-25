import dataclasses
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union

import hondana

from .args import ProcessArgs
from .constants import ImpVar


@dataclasses.dataclass()
class Cache:
    id: str
    type: str
    time: datetime = dataclasses.field(default="1970-01-01 00:00:00.000000")
    data: Optional[dict] = dataclasses.field(default_factory=dict)
    chapters: Optional[list] = dataclasses.field(default_factory=list)
    covers: Optional[list] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.time, str) or self.time is None:
            self.time = datetime.strptime(self.time, "%Y-%m-%d %H:%M:%S.%f")


class CacheRead:
    def __init__(self, args: ProcessArgs, *, cache_id: Optional[str] = None, cache_type: str) -> None:
        self._args = args
        self._cache_id = cache_id
        self._cache_type = cache_type
        self._force_reset_cache_time = "1970-01-01 00:00:00.000000"
        self._cache_refresh_time = ImpVar.CACHE_REFRESH_TIME
        self._root = Path(ImpVar.CACHE_PATH).joinpath(self._cache_type)
        self._root.mkdir(parents=True, exist_ok=True)

        self._cache_path: Optional[Path] = None
        self.cache: Optional[Cache] = None

        if self._cache_id is not None:
            self.update_cache_obj()

    def update_cache_obj(self):
        self._cache_path = self.update_path()
        self.cache = self.load_cache()

    def update_path(self) -> Path:
        return self._root.joinpath(self._cache_id).with_suffix(".json.gz")

    def _get_orig_dict(
        self,
        data: Union[
            "hondana.Manga",
            "hondana.Chapter",
            "hondana.User",
            "hondana.ScanlatorGroup",
            "hondana.CustomList",
            "hondana.Cover",
        ],
    ) -> dict:
        _data = {}
        _data.update(data._data)
        _data.update({"relationships": data._relationships})
        return _data

    def _get_orig_list(
        self, data: Union["hondana.CoverCollection", "hondana.ChapterFeed"]
    ) -> List[Union["hondana.Cover", "hondana.Chapter"]]:
        data_list = []
        if isinstance(data, hondana.CoverCollection):
            data_list = data.covers
        else:
            data_list = data.chapters

        return [self._get_orig_dict(x) for x in data_list]

    def save_cache(
        self,
        *,
        cache_time: Optional[Union[str, datetime]] = None,
        data: Optional[
            Union[
                dict,
                Union[
                    "hondana.Manga",
                    "hondana.Chapter",
                    "hondana.User",
                    "hondana.ScanlatorGroup",
                    "hondana.CustomList",
                    "hondana.Cover",
                ],
            ]
        ] = None,
        chapters: Optional[Union[list, "hondana.ChapterFeed"]] = None,
        covers: Optional[Union[list, "hondana.CoverCollection"]] = None,
    ) -> Cache:
        """Save the data to the cache.

        Args:
        download_id (str): The id of the data to cache.
            cache_time (str, optional): The time the cache was saved.
            data (dict, optional): The data to cache. Defaults to {}.
            chapters (list, optional): The chapters to cache. Defaults to [].
            covers (list, optional): The covers of the manga. Defaults to [].
        """
        if cache_time is None:
            cache_time = self.cache.time

        if data is None:
            data = self.cache.data

        if chapters is None:
            chapters = self.cache.chapters

        if covers is None:
            covers = self.cache.covers

        if not isinstance(data, dict):
            data = self._get_orig_dict(data)

        if not isinstance(chapters, list):
            chapters = self._get_orig_list(chapters)

        if not isinstance(covers, list):
            covers = self._get_orig_list(covers)

        cache_json = {
            "id": self._cache_id,
            "type": self._cache_type,
            "time": str(cache_time),
            "data": data,
            "chapters": chapters,
            "covers": covers,
        }
        with gzip.open(self._cache_path, "w") as cache_json_fp:
            cache_json_fp.write(json.dumps(cache_json, indent=4, ensure_ascii=False).encode("utf-8"))

        cache_obj = Cache(**cache_json)
        self.cache = cache_obj
        return cache_obj

    def load_cache(self) -> Cache:
        """Load the cache data.

        Args:
            download_id (str): The id of the cache data to load.

        Returns:
            dict: The cache's data.
        """
        try:
            with gzip.open(self._cache_path, "r") as cache_json_fp:
                cache_json = json.loads(cache_json_fp.read().decode("utf-8"))
            return Cache(**cache_json)
        except (FileNotFoundError, json.JSONDecodeError, gzip.BadGzipFile):
            return Cache(id=self._cache_id, type=self._cache_type)

    def check_cache_time(self) -> bool:
        """Check if the cache needs to be refreshed.

        Args:
            cache_json (dict): The cache data.

        Returns:
            bool: If a refresh is needed.
        """
        refresh = True
        if not (datetime.now() >= self.cache.time + timedelta(hours=self._cache_refresh_time)):
            refresh = False

        if self._args.force_refresh:
            refresh = True

        # if refresh:
        #     if self.model.debug: print('Refreshing cache.')
        # else:
        #     if self.model.debug: print('Using cache data.')
        return refresh
