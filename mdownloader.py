#!/usr/bin/python3
import argparse

from components.main import main

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l', default='gb', help='Specify the language to download. NEEDED for non-English title downloads.')
    parser.add_argument('--directory', '-d', default='./downloads', help='The download location, need to specify full path.')
    parser.add_argument('--type', '-t', default='title', nargs='?', const='chapter', help='Type of id to download, title or chapter.') #title or chapter
    parser.add_argument('--folder', '-f', default='no', nargs='?', const='yes', choices=['yes', 'no'], help='Make chapter folder.') #yes or no
    parser.add_argument('--save_format', '-s', default='cbz', help='Choose to download as a zip archive or as a comic archive.') #zip or cbz
    parser.add_argument('id', help='ID to download. Can be chapter, tile, link or file.')

    args = parser.parse_args()

    main(args.id, args.language, args.directory, args.type, args.folder, args.save_format, '')