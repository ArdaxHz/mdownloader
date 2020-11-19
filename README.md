# mDownloader
Download from MangaDex easily without compromising quality or speed!
This is a MangaDex specific downloader, other sites will not be supported.

## Install requirements
`pip install -r requirements.txt`

## Excecute 
`python3 mdownloader.py [options] [<title|chapter|group|user link/id> or filename]`

To bulk download, create a file in the same folder as the downloader. Inside, add one id or link per line, the id being . The link can be either for chapters or titles, no need to specify which it is using the "--type" argument. Instead of typing the id when executing, enter the filename. Since title is the default download type, there is no need to add it as an option for bulk download. Any line that isn't a mangadex title/chapter/group/user link/id will be skipped.

`python3 mdownloader.py mylist.txt [-t chapter/group/user]`

```
id_1
id_2
id_3
...
```

## Options
```
    -l --language (optional. Use the MD code of the language you want to download. Default: English)
    -d --directory (optional. Must be the absolute path (i.e. /Users/bocchi/Desktop/). Default: script-folder/downloads)
    -t --type (optional. You can choose between 'title', 'chapter', 'group' or 'user' options. Default: title)
    -f --folder (optional. Makes a chapter folder. You can choose between 'yes' and 'no' options. Default: no)
    -s --save_format (optional. Choose between comic archive or zip as the file type (both are zip files). You can choose between 'cbz' and 'zip' options. Default: cbz))
    -c --covers (optional. Download the manga covers, works only with title downloads. You can choose between 'skip' and 'save' options. Default: skip)
```

Images will be downloaded in the same directory as this script with the following structure:

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

## TODO
Need Ideas