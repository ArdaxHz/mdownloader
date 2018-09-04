# mDownloader

`python3 mdownloader.py [options] manga_id`

## Options
```
    -l --language (optional. Default: English)
    -d --directory (optional. Must be the absolute path (i.e. /Users/bocchi/Desktop/). Default: Current script folder.)
```

Images will be downloaded in the same directory as this script with the following structure:

```
    Manga Title
        |
        ----> [Language][Vol. X Ch. Y][Group(s)] - chapter title
            |
            ----> Images
```

## Languages

| Code          | Language        |
| ------------- |:---------------:|
| sa            | Arabic          |
| bd            | Bengali         |
| bg            | Bulgarian       |
| mm            | Burmese         |
| ct            | Catalan         |
| cn            | Chinese (Simp)  |
| hk            | Chinese (Trad)  |
| cz            | Czech           |
| dk            | Danish          |
| nl            | Dutch           |
| gb            | English         |
| ph            | Filipino        |
| fi            | Finnish         |
| fr            | French          |
| de            | German          |
| gr            | Greek           |
| hu            | Hungarian       |
| id            | Indonesian      |
| it            | Italian         |
| jp            | Japanese        |
| kr            | Korean          |
| my            | Malay           |
| mn            | Mongolian       |
| ir            | Persian         |
| pl            | Polish          |
| br            | Portuguese (Br) |
| pt            | Portuguese (Pt) |
| ro            | Romanian        |
| ru            | Russian         |
| rs            | Serbo-Croatian  |
| es            | Spanish (Es)    |
| mx            | Spanish (LATAM) |
| se            | Swedish         |
| th            | Thai            |
| tr            | Turkish         |
| ua            | Ukrainian       |
| vn            | Vietnamese      |

## TODO
* Retry when it fails to download an image
* Continue on the last image downloaded of the last downloaded chapter