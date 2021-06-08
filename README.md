# mDownloader
Download from MangaDex easily without compromising quality or speed!
This is a MangaDex specific downloader, other sites will not be supported.

*If using Windows, you'll need to use `pip` and `python`. If using Linux or Mac OS, you'll need to use `pip3` and `python3`. For this readme, the Linux python namespace format will be used.*

## Install requirements
`pip3 install -r requirements.txt`

You'll need to rename `.env.example` to `.env` and change the values to whatever would suit you best, if you don't know what it's for, leave the values as they are.

## Excecute 
`python3 mdownloader.py link/id [options]`

### Parameters
To use an additional option, you can just add the parameter by itself (except language, type or search), with no arguments. e.g. `python3 mdownloader.py id -t manga -c` will download the covers of a manga, not adding a parameter will fallback to the default parameter behaviour.

### Batch Downloading
To batch download, create a file in the same folder as the downloader. Inside, add one id or link per line. Instead of typing the id when executing, enter the filename. Since chapter is the default download type, any non-links will be treated as chapter ids and be downloaded as such. Using this will override the range download option to be False.

`python3 mdownloader.py mylist.txt [-t <manga|group|user|list>]`

```
link_1
id_1
id_2
link_2
id_3
link_3
...
```

### Searching
To search for a manga to download, instead of id, enter the manga's name. You **need** to make sure the `-s` parameter is included. If you want to enter multiple words, wrap them with quotation marks. You can still use the other options available, the type option will be overridden to type "manga".

`python3 mdownloader.py "Please Put These On, Takamine-san" -s`

## Options
- -l --language (optional. Use the MD code of the language you want to download. Default: en)
- -t --type (optional. You can choose between 'manga', 'chapter', 'group' or 'user' options. Default: chapter)
- -f --folder (optional. Downloads the images to a folder instead of an archive. Default: False)
- -c --covers (optional. Download the manga covers, *works only with manga downloads*. Default: False)
- -j --json (optional. Add the chapter data as found on the api to the archive or folder. Default: True)
- -r --range (optional. Instead of downloading all the chapters, you can download a range of chapters, or download all while excluding some. 'all' to download all chapters, '!' before a chapter number or range to exclude those chapters from the download. Default: True)
- -s --search (optional. **NEEDED** to search for manga. Wrap multiple words in quotation marks, e.g. "Please Put These On, Takamine-san". Default: False)
- --login (optional. Login to MangaDex. Default: False)
- --force (optional. Force refresh the downloaded cache. Default: False)

## Blacklisting and Whitelisting
***Whitelisting takes priority with group filtering taking priority over user filtering.***
To blacklist a group or user, create a file in the same folder as the download, it can be called whatever you want, default names are "group_blacklist.txt" and "user_blacklist.txt", however you will **need** to change the name of the files in the `.env` file if you want to use your own names. Add an id per line of the group or user's chapters you want to skip.

To whitelist a group or user, create a file in the same folder as the download, it can be called whatever you want, default names are "group_whitelist.txt" and "user_whitelist.txt", however you will **need** to change the name of the files in the `.env` file if you want to use your own names. Add an id per line of the group or user's chapters you want to download. *If both group and user whitelists are specified, group whitelisting takes priority.*

## Naming
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

| Language        | MD Code       | ISO-639 Code  | Language        | MD Code       | ISO-639 Code  |
|:---------------:| ------------- | ------------- |:---------------:| ------------- | ------------- |
| Arabic          | ar            | ara           | Italian         | it            | ita           |
| Bengali         | bd            | ben           | Japanese        | ja            | jpn           |
| Bulgarian       | bg            | bul           | Korean          | ko            | kor           |
| Burmese         | my            | bur           | Lithuanian      | li            | lit           |
| Bengali         | bn            | ben           | Malay           | ms            | may           |
| Catalan         | ca            | cat           | Mongolian       | mn            | mon           |
| Chinese (Simp)  | zh            | chi           | Norwegian       | no            | nor           |
| Chinese (Trad)  | zh-hk         | chi           | Persian         | fa            | per           |
| Czech           | cs            | cze           | Polish          | pl            | pol           |
| Danish          | da            | dan           | Portuguese (Br) | pt-br         | por           |
| Dutch           | nl            | dut           | Portuguese (Pt) | pt            | por           |
| English         | en            | eng           | Romanian        | ro            | rum           |
| Filipino        | tl            | fil           | Russian         | ru            | rus           |
| Finnish         | fi            | fin           | Serbo-Croatian  | sh            | hrv           |
| French          | fr            | fre           | Spanish (Es)    | es            | spa           |
| German          | de            | ger           | Spanish (LATAM) | es-la         | spa           |
| Greek           | el            | gre           | Swedish         | sv            | swe           |
| Hebrew          | he            | heb           | Thai            | th            | tha           |
| Hindi           | hi            | hin           | Turkish         | tr            | tur           |
| Hungarian       | hu            | hun           | Ukrainian       | uk            | ukr           |
| Indonesian      | id            | ind           | Vietnamese      | vi            | vie           |

## Other
Used the MangaPlus image decrypter from [here.](https://github.com/hurlenko/mloader)

## TODO
