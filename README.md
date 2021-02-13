# mDownloader
Download from MangaDex easily without compromising quality or speed!
This is a MangaDex specific downloader, other sites will not be supported.

## Install requirements
`pip install -r requirements.txt`

## Excecute 
`python3 mdownloader.py [options] (<title|chapter|group|user link/id> or filename)`

To bulk download, create a file in the same folder as the downloader. Inside, add one id or link per line, the id being . The link can be either for chapters or titles, no need to specify which it is using the "--type" argument. Instead of typing the id when executing, enter the filename. Since title is the default download type, there is no need to add it as an option for bulk download. Any line that isn't a mangadex title/chapter/group/user link/id will be skipped.

`python3 mdownloader.py mylist.txt [-t <chapter|group|user>]`

```
link_1
id_1
id_2
link_2
id_3
link_3
...
```

## Options
```
    -l --language (optional. Use the MD code of the language you want to download. Default: English)
    -d --directory (optional. Can be an absolute or relative path. Default: script-folder/downloads)
    -t --type (optional. You can choose between 'title', 'chapter', 'group' or 'user' options. Default: title)
    -s --save_format (optional. Choose between comic archive or zip as the file type (both are zip files). You can choose between 'cbz' and 'zip' options. Default: cbz))
    -f --folder (optional. Downloads the images to a folder instead of an archive. You can choose between 'yes' and 'no' options. Default: no)
    -c --covers (optional. Download the manga covers, works only with title downloads. You can choose between 'skip' and 'save' options. Default: skip)
    -j --json (optional. Add the chapter data as found on the api to the archive or folder. You can choose between 'add' and 'ignore' options. Default: ignore)
    -r --range (optional. Instead of downloading all the chapters, you can download a range of chapters, or download all while excluding some. 'all' to download all chapters, '!' before a chapter number or range to exclude those chapters from the download. You can choose between 'all' and 'range' options. Default: all)
```

Images will be downloaded in the download directory relative to the script location with the following structure:

```
    Manga Title
        |
        ----> Manga Title [lang_iso_code] - cXXX (vYY) [Group(s)]
            |
            ----> Manga Title [lang_iso_code] - cXXX (vYY) - pZZZ [Group(s)].extension
```
Language code and volume number will only be applied if applicable.
This follows Daiz's [naming scheme](https://github.com/Daiz/manga-naming-scheme).

## Languages

| Language        | MD Code       | ISO Code      | Language        | MD Code       | ISO Code      |
|:---------------:| ------------- | ------------- |:---------------:| ------------- | ------------- |
| Arabic          | sa            | ara           | Japanese        | jp            | jpn           |
| Bengali         | bd            | ben           | Korean          | kr            | kor           |
| Bulgarian       | bg            | bul           | Malay           | my            | may           |
| Burmese         | mm            | bur           | Mongolian       | mn            | mon           |
| Catalan         | ct            | cat           | Persian         | ir            | per           |
| Chinese (Simp)  | cn            | chi           | Polish          | pl            | pol           |
| Chinese (Trad)  | hk            | chi           | Portuguese (Br) | br            | por           |
| Czech           | cz            | cze           | Portuguese (Pt) | pt            | por           |
| Danish          | dk            | dan           | Romanian        | ro            | rum           |
| Dutch           | nl            | dut           | Russian         | ru            | rus           |
| English         | gb            | eng           | Serbo-Croatian  | rs            | hrv           |
| Filipino        | ph            | fil           | Spanish (Es)    | es            | spa           |
| Finnish         | fi            | fin           | Spanish (LATAM) | mx            | spa           |
| French          | fr            | fre           | Swedish         | se            | swe           |
| German          | de            | ger           | Thai            | th            | tha           |
| Greek           | gr            | gre           | Turkish         | tr            | tur           |
| Hungarian       | hu            | hun           | Ukrainian       | ua            | ukr           |
| Indonesian      | id            | ind           | Vietnamese      | vn            | vie           |
| Italian         | it            | ita           |

## Other
Used the MangaPlus image decrypter from [here.](https://github.com/hurlenko/mloader)

**Extremely Beta:**
Chapter number prefix (usually 'c') is determined by looking at the all the series' chapters and comparing each volume's chapters with each other. If a volume has a chapter number that is in another volume, the chapter prefix will be incremented relative to the volume number. E.g. *Vol. 1 > c*, *Vol. 2 > d*, etc.

## TODO
Maybe add MDList download