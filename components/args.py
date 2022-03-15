import dataclasses
import getpass
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, List, Literal, Optional, Tuple, Union

import hondana

from .constants import ImpVar
from .errors import MDownloaderError
from .languages import get_lang_md


if TYPE_CHECKING:
    from .cache import CacheRead
    from .jsonmaker import BulkJson, TitleJson


@dataclasses.dataclass()
class MDArgs:
    id: str
    type: str
    data: Optional[
        Union[hondana.Manga, hondana.Chapter, hondana.ScanlatorGroup, hondana.User, hondana.CustomList]
    ] = dataclasses.field(default=None)
    chapters: Optional[List[hondana.Chapter]] = dataclasses.field(default=None)
    cache: Optional["CacheRead"] = dataclasses.field(default=None)
    json_obj: Optional[Union["TitleJson", "BulkJson"]] = dataclasses.field(default=None)


class AuthMD:
    def __init__(self, args: "ProcessArgs"):
        self._args = args
        self.first_login = True
        self.successful_login = False
        self.token = None
        self.refresh_token = None
        self.token_file = Path(".mdauth")

    def _open_auth_file(self) -> Optional[str]:
        try:
            with open(self.token_file, "r") as login_file:
                token = login_file.readline()
            return token
        except (FileNotFoundError, json.JSONDecodeError):
            # logging.error(
            #     "Couldn't find the file, trying to login using your account details."
            # )
            return None

    def _save_session(self):
        """Save the session and refresh tokens."""
        self._args._hondana_client.dump_refresh_token(self.token_file)
        # logging.debug("Saved .mdauth file.")

    async def _static_login(self) -> bool:
        try:
            await self._args._hondana_client.static_login()
        except (hondana.APIException, ValueError):
            return False
        else:
            self.refresh_token = self._args._hondana_client._http._refresh_token
            self._save_session()
            return True

    async def _login(self) -> bool:
        username = input("Your username: ")
        password = getpass.getpass(prompt="Your password: ", stream=None)
        self._args._hondana_client.login(username=username, password=password)

        return await self._static_login()

    async def login(self, check_login=True):
        """Login to MD account using details or saved token."""

        if not check_login and self.successful_login:
            # logging.info("Already logged in, not checking for login.")
            return

        # logging.info("Trying to login through the .mdauth file.")

        if self.first_login or self.refresh_token is None:
            refresh_token = self._open_auth_file()
            if refresh_token is None:
                self.successful_login = self._login()
            else:
                self._args._hondana_client.login(refresh_token=refresh_token)
                self.successful_login = await self._static_login()
        else:
            self.successful_login = await self._static_login()

        if self.successful_login:
            print("Logged in.")
        else:
            print("Couldn't login.")


class ProcessArgs:
    def __init__(self, unparsed_arguments, hondana_client: hondana.Client) -> None:
        self._hondana_client = hondana_client
        self._unparsed_arguments = unparsed_arguments
        self._login_obj = AuthMD(self)
        self._arg_id = unparsed_arguments["id"]
        self._arg_type = unparsed_arguments["type"]
        self.args: Optional[MDArgs] = None
        self.debug = bool(unparsed_arguments["debug"])
        self.force_refresh = bool(unparsed_arguments["refresh"])
        self.directory: Path = (
            Path(unparsed_arguments["directory"])
            if unparsed_arguments["directory"] is not None
            else Path(ImpVar.DOWNLOAD_PATH)
        )
        self.language = get_lang_md(unparsed_arguments["language"])
        self.archive_extension = self._check_archive_extension(ImpVar.ARCHIVE_EXTENSION)
        self.folder_download = bool(unparsed_arguments["folder"])
        self.cover_download = bool(unparsed_arguments["covers"])
        self.save_chapter_data = bool(unparsed_arguments["json"])
        self.range_download = bool(unparsed_arguments["range"])
        self.rename_files = bool(unparsed_arguments["rename"])
        self.download_in_order = bool(unparsed_arguments["order"])
        self.search_manga = bool(unparsed_arguments["search"])

        self.naming_scheme_options = Literal["default", "original", "number"]
        self.naming_scheme = "default"

    async def _check_legacy(self, download_id: str, download_type: str):
        if download_id.isdigit():
            return await self._map_single_legacy_uuid(download_id, download_type)
        return download_id

    async def _map_single_legacy_uuid(self, download_id: Union[str, int], download_type: str) -> str:
        download_id = int(download_id)
        response: hondana.LegacyMappingCollection = await self._hondana_client.legacy_id_mapping(
            download_type, item_ids=[download_id]
        )
        return response.legacy_mappings[0].obj_new_id

    def check_url(self, url: str) -> Optional[re.Match[str]]:
        """Check if the url given is a MangaDex one."""
        return ImpVar.MD_URL.match(url)

    def parse_url(self, url: str) -> Tuple[str, str]:
        """Get the id and download type from url."""
        md_url_match = self.check_url(url)
        if md_url_match is None:
            raise MDownloaderError("That url is not recognised.")

        download_type_from_url: str = md_url_match.group(1)
        id_from_url: str = md_url_match.group(2)

        if download_type_from_url == "title":
            download_type_from_url = "manga"

        return id_from_url, download_type_from_url

    def check_uuid(self, series_id: str) -> bool:
        """Check if the id is a UUID."""
        return bool(re.match(ImpVar.UUID_REGEX, series_id))

    async def _parse_id(self, download_id: str, download_type: str) -> Tuple[Union[str, Path], Optional[str]]:
        to_return_id = None
        to_return_type = None
        if self.check_uuid(download_id):
            to_return_id = download_id
        elif download_id.isdigit():
            to_return_id = await self._map_single_legacy_uuid(download_id, download_type)
        elif ImpVar.URL_RE.search(download_id):
            parsed_id, parsed_type = self.parse_url(download_id)
            to_return_type = parsed_type
            to_return_id = await self._check_legacy(parsed_id, download_type)
        else:
            download_id_path = Path(download_id)
            if download_id_path.exists():
                to_return_id = download_id_path
            else:
                raise MDownloaderError("The id argument entered is not recognised.")
        return to_return_id, to_return_type

    def _check_archive_extension(self, archive_extension: str) -> str:
        """Check if the file extension is an accepted format. Default: cbz.

        Raises:
            MDownloaderError: The extension chosen isn't allowed.
        """
        if archive_extension not in ("zip", "cbz"):
            raise MDownloaderError("This archive save format is not allowed.")
        return archive_extension

    async def find_manga(self, search_term: str) -> hondana.Manga:
        """Search for a manga by title."""
        manga_response = await self._hondana_client.manga_list(title=search_term)

        for count, manga in enumerate(manga_response.manga, start=1):
            print(f"{count}: {manga.title} | {manga.url}")

        try:
            manga_to_use_num = int(input(f"Choose a number matching the position of the manga you want to download: "))
        except ValueError:
            raise MDownloaderError("That's not a number.")

        if manga_to_use_num not in range(1, len(manga_response.manga) + 1):
            raise MDownloaderError("Not a valid option.")

        manga_to_use = manga_response.manga[manga_to_use_num - 1]
        return manga_to_use

    async def process_args(self, *, download_id: Optional[str] = None, download_type: Optional[str] = None) -> MDArgs:
        if self._unparsed_arguments["login"]:
            await self._login_obj.login()

        if download_type is None:
            download_type = self._arg_type

        if self.search_manga:
            found_manga = await self.find_manga(download_id)
            self._arg_type = "manga"
            obj = MDArgs(id=found_manga.id, type="manga", data=found_manga)
            self.args = obj
            return obj

        download_id, inner_download_type = await self._parse_id(str(download_id), download_type)
        if inner_download_type is None:
            inner_download_type = download_type
        self._arg_type = inner_download_type
        obj = MDArgs(id=download_id, type=inner_download_type)
        self.args = obj
        return obj
