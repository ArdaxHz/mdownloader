# mDownloader
Download from MangaDex easily without compromising quality or speed!
This is a MangaDex specific downloader, other sites will not be supported.

## Install requirements
`pip install -r requirements.txt`

## Excecute 
`python3 mdownloader.py [options] (<manga|chapter|group|user|list link/id> or filename)`

To bulk download, create a file in the same folder as the downloader. Inside, add one id or link per line, the id being . The link can be either for chapters or titles, no need to specify which it is using the "--type" argument. Instead of typing the id when executing, enter the filename. Since title is the default download type, there is no need to add it as an option for bulk download. Any line that isn't a mangadex manga/chapter/group/user/list link/id will be skipped.

`python3 mdownloader.py mylist.txt [-t <chapter|group|user|list>]`

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
    -j --json (optional. Add the chapter data as found on the api to the archive or folder. You can choose between 'add' and 'ignore' options. Default: add)
    -r --range (optional. Instead of downloading all the chapters, you can download a range of chapters, or download all while excluding some. 'all' to download all chapters, '!' before a chapter number or range to exclude those chapters from the download. You can choose between 'all' and 'range' options. Default: range)
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
Maybe add MDList download