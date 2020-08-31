#!/usr/bin/python3
import argparse

from components.main import main

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l', default='gb', help='Specify the language to download. NEEDED for non-English title downloads.')
    parser.add_argument('--directory', '-d', default='./downloads', help='The download location, need to specify full path.')
    parser.add_argument('--type', '-t', default='title', nargs='?', const='chapter', help='Type of id to download, title or chapter.') #title or chapter
    parser.add_argument('--check_images', '-c', default='names', choices=['names', 'skip'], help='Check if the chapter folder and/or zip has the same files as the chapter on MangaDex. Read the Readme for more information.') #data or names or skip
    parser.add_argument('--save_format', '-s', default='zip', help='Choose to download as a zip archive or as a comic archive.') #zip or cbz
    parser.add_argument('id', help='ID to download. Can be chapter, tile, link or file.')

    args = parser.parse_args()

    main(args.id, args.language, args.directory, args.type, args.check_images, args.save_format, '')