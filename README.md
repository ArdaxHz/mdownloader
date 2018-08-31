# mDownloader
---

`python3 mdownloader.py *manga_id*`

Images will be downloaded in the same directory as this script with the following structure:

```
    Manga Title
        |
        ----> [Vol. X Ch. Y][Group(s)] - chapter title
            |
            ----> Images
```


## TODO
---
* Retry when it fails to download an image
* Continue on the last image downloaded of the last downloaded chapter
* Custom download directory path