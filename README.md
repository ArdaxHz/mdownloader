# mDownloader

## Install requirements
`pip install -r requirements.txt`

## Excecute 
`python3 mdownloader.py [options] [title, chapter id or filename]`

To bulk download titles, create a file in the same folder as the downloader. Inside, add one title id per line. Instead of typing the title id when executing, enter the filename.

`python3 mdownloader.py mylist.txt`

```
id_1
id_2
id_3
...
```

## Options
```
    -l --language (optional. Default: English)
    -d --directory (optional. Must be the absolute path (i.e. /Users/bocchi/Desktop/). Default: Current script folder.)
    -t --type (optional. You can choose between 'title' and 'chapter' option. Use the title id or the chapter id. Default: title.)
```

Images will be downloaded in the same directory as this script with the following structure:

```
    Manga Title
        |
        ----> [Language][Vol. X Ch. Y][Group(s)] - chapter title
            |
            ----> Images
```
Downloading a chapter will create a chapter folder with the Group IDs instead of the names.

## Languages

| Code          | Language        | Code          | Language        |
| ------------- |:---------------:| ------------- |:---------------:|
| sa            | Arabic          | jp            | Japanese        |
| bd            | Bengali         | kr            | Korean          |
| bg            | Bulgarian       | my            | Malay           |
| mm            | Burmese         | mn            | Mongolian       |
| ct            | Catalan         | ir            | Persian         |
| cn            | Chinese (Simp)  | pl            | Polish          |
| hk            | Chinese (Trad)  | br            | Portuguese (Br) |
| cz            | Czech           | pt            | Portuguese (Pt) |
| dk            | Danish          | ro            | Romanian        |
| nl            | Dutch           | ru            | Russian         |
| gb            | English         | rs            | Serbo-Croatian  |
| ph            | Filipino        | es            | Spanish (Es)    |
| fi            | Finnish         | mx            | Spanish (LATAM) |
| fr            | French          | se            | Swedish         |
| de            | German          | th            | Thai            |
| gr            | Greek           | tr            | Turkish         |
| hu            | Hungarian       | ua            | Ukrainian       |
| id            | Indonesian      | vn            | Vietnamese      |
| it            | Italian         |

## TODO
* Continue on the last image downloaded of the last downloaded chapter
