


class MDownloaderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class NoChaptersError(MDownloaderError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)