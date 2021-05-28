from requests.models import Response



class MDownloaderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class MDNotLoggedIn(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class NoChaptersError(MDownloaderError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)



class MDRequestError(MDownloaderError):
    def __init__(self,
                download_id: str,
                download_type: str,
                response: Response,
                data: dict={}) -> None:

        http_error_codes = {"400": "Bad request.", "401": "Unauthorised.", "403": "Forbidden.", "404": "Not found.", "429": "Too many requests."}

        if data:
            error = [e["detail"] for e in data["errors"] if e["detail"] is not None]
            error = ', '.join(error)
            code = [str(e["status"]) for e in data["errors"] if e["status"] is not None]
            code = ', '.join(code)
        else:
            code = response.status_code

            if code in range(300, 400):
                error = 'API error.'
            elif code in range(500, 600):
                error = 'server error.'
            else:
                error = http_error_codes.get(str(code), '')

        error_message = f'{download_id}: {download_type}. Error: {code}. Detail: {error}'

        super().__init__(error_message)
