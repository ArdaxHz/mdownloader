import json

from requests.models import Response


class NotLoggedInError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class MDownloaderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class NoChaptersError(MDownloaderError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class MDRequestError(MDownloaderError):
    def __init__(self, download_id: str, download_type: str, error_response: Response, data: dict = {}) -> None:

        http_error_codes = {
            "400": "Bad request.",
            "401": "Unauthorised.",
            "403": "Forbidden.",
            "404": "Not found.",
            "429": "Too many requests.",
        }

        status_code = error_response.status_code
        error_converting_json_print_message = (
            f"{status_code}: Couldn't convert api reposnse into json for id: {download_id}, {download_type}."
        )
        error_message = ""

        if status_code == 429:
            error_message = f"429: {http_error_codes.get(str(status_code))}"
            super().__init__(error_message)

        # Api didn't return json object
        try:
            error_json = error_response.json()
        except json.JSONDecodeError as e:
            super().__init__(error_converting_json_print_message)
        # Maybe already a json object
        except AttributeError:
            # Try load as a json object
            try:
                error_json = json.loads(error_response.content)
            except json.JSONDecodeError as e:
                super().__init__(error_converting_json_print_message)

        # Api response doesn't follow the normal api error format
        try:
            errors = [f'{e["status"]}: {e["detail"] if e["detail"] is not None else ""}' for e in error_json["errors"]]
            errors = ", ".join(errors)

            if not errors:
                errors = http_error_codes.get(str(status_code), "")

            error_message = f"Error: {errors}."
            super().__init__(error_message)
        except KeyError:
            error_message = f"KeyError {status_code}: {error_json}."
            super().__init__(error_message)

        super().__init__(error_message)
