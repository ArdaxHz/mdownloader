


class MDownloaderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)



class NoChaptersError(MDownloaderError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)



class MdRequestError(MDownloaderError):
    def __init__(self, download_id, download_type, response, **data: dict) -> None:
        if data:
            error = [e["detail"] for e in data["errors"] if e["detail"] != None]
            error = ', '.join(error)
        else:
            error = 'No content'
        error_message = f'{download_id}: {download_type}. Error: {response.status_code}. Detail: {error}'

        super().__init__(error_message)
