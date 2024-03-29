#!/usr/bin/python3
import argparse
import os
import re
import shutil
from pathlib import Path

import requests
from dotenv import load_dotenv

from components.main import main
from components.constants import ImpVar

try:
    from components.__version__ import __version__
except ModuleNotFoundError:
    pass


def check_for_update(args) -> None:
    """Check if the program is the latest version.

    Args:
        args (argparse.ArgumentParser.parse_args): Command line arguments to parse.
    """
    excluded = ['components', '.env.example']
    components_path = Path('components')
    vargs = vars(args)

    if not vargs["update"]:
        print('Looking for program update.')
        # Call GitHub api to check if there are missing local files
        root_response = requests.get('https://api.github.com/repos/ArdaxHz/mdownloader/contents')
        components_response = requests.get('https://api.github.com/repos/ArdaxHz/mdownloader/contents/components')

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
                download_missing = input("Do you want to download the missing required files? 'y' or 'n' ")

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
                else:
                    print('Skipping download, this might result in program errors.')

            # Check the local version is the same as on GitHub
            remote_version_info_response = requests.get('https://raw.githubusercontent.com/ArdaxHz/mdownloader/master/components/__version__.py')
            remote_version_info = (remote_version_info_response.content).decode()

            version_info = remote_version_info.rsplit('\n')
            ver_regex = re.compile(r'(?:__version__\s=\s\')(.+)(?:\')')
            version_number = version_info[0]
            match = ver_regex.match(version_number)
            remote_number = match.group(1)

            local_version = int(__version__.replace('.', ''))
            remote_version = int(remote_number.replace('.', ''))

            remote_components = [f["name"] for f in components_data]

            if remote_version > local_version:
                download_update = input(f"Looks like update {remote_number} is available, do you want to download?\nThe update will remove the unnecessary files from the components folder, backup any changes made if needed.\n'y' or 'n' ")

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

                    shutil.rmtree(ImpVar.CACHE_PATH)
                    print('Downloaded the update and exiting.')
                    return
                else:
                    print('Skipping update, this might result in program errors.')

    # Get announcement messages that can be added at any time
    announcement_response = requests.get('https://raw.githubusercontent.com/ArdaxHz/misc/main/mdl_msgs.txt')

    if announcement_response.status_code == 200:
        announcement_message = (announcement_response.content).decode()
        announcement_message = announcement_message.rstrip('\n')

        if len(announcement_message) > 0:
            print(announcement_message.capitalize())

    main(vargs)


if __name__ == "__main__":

    os.system("")
    load_dotenv()

    parser = argparse.ArgumentParser()

    parser.add_argument('--language', '-l', default='en', help='Specify the language to download. NEEDED to download non-English chapters on manga downloads.')
    parser.add_argument('--type', '-t', default='chapter', nargs='?', const='manga', help='Type of id to download, manga, chapter, group, user, list or follows.')
    parser.add_argument('--directory', '-d', default=None, help='Directory where to download chapters, takes priority over whats in the env file.')
    parser.add_argument('--folder', '-f', default=False, const=True, nargs='?', help='Download into a folder instead of an archive.')
    parser.add_argument('--covers', '-c', default=False, const=True, nargs='?', help='Download the covers of the manga. Works only with manga downloads.')
    parser.add_argument('--json', '-j', default=True, const=False, nargs='?', help='Add the chapter data as a json in the chapter archive/folder.')
    parser.add_argument('--range', '-r', default=False, const=True, nargs='?',
        help='Download a range of chapters, or all while excluding some. Put "!" in front of the chapters you want to exclude.')
    parser.add_argument('--search', '-s', default=False, const=True, nargs='?',
        help='Search for the manga specified. Wrap multiple words in quotation marks, e.g. "Please Put These On, Takamine-san"')
    parser.add_argument('--order', '-o', default=False, const=True, nargs='?', help='Download chapters in descending order instead of grouping by manga.')
    parser.add_argument('--debug', default=False, const=True, nargs='?', help=argparse.SUPPRESS)
    parser.add_argument('--refresh', default=False, const=True, nargs='?', help='Force refresh the cache.')
    parser.add_argument('--login', default=False, const=True, nargs='?', help='Login to MangaDex.')
    parser.add_argument('--update', default=False, const=True, nargs='?', help='Skip looking for an application update.')
    parser.add_argument('--rename', default=True, const=False, nargs='?', help='Skip renaming downloaded files if the title is wrong.')
    parser.add_argument('id', help='ID to download. Can be chapter, manga, group, user, list, link/id or file.')

    args = parser.parse_args()

    check_for_update(args)
