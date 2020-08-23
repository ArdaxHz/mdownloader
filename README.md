# mDownloader

## Install requirements
`pip install -r requirements.txt`

## Excecute 
`python3 mdownloader.py [options] [title link/id, chapter link/id or filename]`

To bulk download titles or chapters, create a file in the same folder as the downloader. Inside, add one title/chapter id per line. Instead of typing the title id when executing, enter the filename.
Since title is the default download type, there is no need to add it as an option for bulk download.

`python3 mdownloader.py mylist.txt [-t chapter]`

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
    -t --type (optional. You can choose between 'title' and 'chapter' option. Use the title id or the chapter id. Default: title)
    -r --remove_folder (optional. Removes the chapter folder after download. You can choose between 'yes' and 'no' option. Default: yes)
    -c --check_images (optional. Check if the downloaded image data is the same as on MD. You can choose between 'data' and 'names' option. Default: names)
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

## TODO
