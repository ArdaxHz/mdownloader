#!/usr/bin/python3
import argparse
import os
import re
from pathlib import Path

import requests

try:
    from components.main import main
    from components.__version__ import __version__
except ModuleNotFoundError:
    pass


def beforeMain(id, language, directory, type, save_format, folder, covers):

    excluded = ['LICENSE', 'README.md', 'components']
    components_path = Path('components')

    # Call GitHub api to check if there are missing local files
    root_response = requests.get('https://api.github.com/repos/Rudoal/mdownloader/contents')
    components_response = requests.get('https://api.github.com/repos/Rudoal/mdownloader/contents/components')    

    if root_response.status_code == 200 and components_response.status_code == 200:
        root_data = root_response.json()
        components_data = components_response.json()

        missing_root = [f for f in root_data if (f["name"] not in os.listdir('.') and f["name"] not in excluded)]

        try:
            missing_components = [f for f in components_data if f["name"] not in os.listdir('./components')]
        except FileNotFoundError:
            components_path.mkdir(parents=True, exist_ok=True)
            missing_components = [f for f in components_data if f["name"] not in os.listdir('./components')]
        
        if len(missing_root) > 0 or len(missing_components) > 0:
            download_missing = input('Do you want to download the missing required files? y or n ')
            
            if download_missing.lower() == 'y':
                
                if len(missing_root) > 0:
                    for f in missing_root:
                        response = requests.get(f["download_url"])
                        contents = response.content

                        with open(os.path.join('.', f["name"]), 'wb') as file:
                            file.write(contents)
                
                if len(missing_components) > 0:
                    for f in missing_components:
                        response = requests.get(f["download_url"])
                        contents = response.content

                        with open(components_path.joinpath(f["name"]), 'wb') as file:
                            file.write(contents)
            
                print('Downloaded the missing files and exiting.')
                return

        # Check the local version is the same as on GitHub
        remote_version_info_response = requests.get('https://raw.githubusercontent.com/Rudoal/mdownloader/master/components/__version__.py')
        remote_version_info = (remote_version_info_response.content).decode()

        version_info = remote_version_info.rsplit('\n')
        ver_regex = re.compile(r'(?:__version__\s=\s\')(.+)(?:\')')
        version_number = version_info[0]
        match = ver_regex.match(version_number)

        local_version = int(__version__.replace('.', ''))
        remote_version = int(match.group(1).replace('.', ''))

        remote_components = [f["name"] for f in components_data]

        if remote_version > local_version:
            download_update = input('Looks like there is an update available, do you want to download it?\nThe update will remove the unnecessary files from the components folder, backup any changes made if needed.\ny or n ')

            if download_update.lower() == 'y':
                [os.remove(i) for i in os.listdir('./components') if (i not in remote_components and i != '__pycache__')]

                for f in components_data:
                    response = requests.get(f["download_url"])
                    contents = response.content

                    with open(components_path.joinpath(f["name"]), 'wb') as file:
                        file.write(contents)

                for f in missing_root:
                    response = requests.get(f["download_url"])
                    contents = response.content

                    with open(os.path.join('.', f["name"]), 'wb') as file:
                        file.write(contents)

                print('Downloaded the update and exiting.')
                return

    # Get announcement messages that can be added at any time
    announcement_response = requests.get('https://raw.githubusercontent.com/Rudoal/misc/main/mdl_msgs.txt')

    if announcement_response.status_code == 200:
        announcement_message = (announcement_response.content).decode()
        announcement_message = announcement_message.rstrip('\n')

        if len(announcement_message) > 0:
            print(announcement_message.capitalize())

    main(id, language, directory, type, save_format, folder, covers)

    return


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l', default='gb', help='Specify the language to download. NEEDED for non-English title downloads.')
    parser.add_argument('--directory', '-d', default='./downloads', help='The download location, can be an absolute or relative path.')
    parser.add_argument('--type', '-t', default='title', nargs='?', const='chapter', help='Type of id to download, title or chapter.') #title, chapter, group or user
    parser.add_argument('--save_format', '-s', default='cbz', help='Choose to download as a zip archive or as a comic archive.') #zip or cbz
    parser.add_argument('--folder', '-f', default='no', nargs='?', const='yes', choices=['yes', 'no'], help='Make chapter folder.') #yes or no
    parser.add_argument('--covers', '-c', default='skip', nargs='?', const='save', choices=['skip', 'save'], help='Download the covers of the manga. Works only with title downloads.')
    parser.add_argument('id', help='ID to download. Can be chapter, title, link or file.')

    args = parser.parse_args()

    beforeMain(args.id, args.language, args.directory, args.type, args.save_format, args.folder, args.covers)
