


class MdDownloaderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)



class NoChaptersError(MdDownloaderError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)



class MdRequestError(MdDownloaderError):
    def __init__(self, response, data: dict={}) -> None:
        if data:
            error = [e["detail"] for e in data["errors"] if e["detail"] != None]
            error = ', '.join(error)
        else:
            error = 'Non content'
        error_message = f'Error: {response.status_code}. Detail: {error}'

        super().__init__(error_message)