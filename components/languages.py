#!/usr/bin/python3

from typing import Optional

language_error = 'Not a valid language option, exiting.'

languages_iso = {
    "sa": "ara",
    "bd": "ben",
    "bg": "bul",
    "mm": "bur",
    "ct": "cat",
    "cn": "chi",
    "hk": "chi",
    "cz": "cze",
    "dk": "dan",
    "nl": "dut",
    "gb": "eng",
    "ph": "fil",
    "fi": "fin",
    "fr": "fre",
    "de": "ger",
    "gr": "gre",
    "hu": "hun",
    "id": "ind",
    "it": "ita",
    "jp": "jpn",
    "kr": "kor",
    "my": "may",
    "mn": "mon",
    "ir": "per",
    "pl": "pol",
    "br": "por",
    "pt": "por",
    "ro": "rum",
    "ru": "rus",
    "rs": "hrv",
    "es": "spa",
    "mx": "spa",
    "se": "swe",
    "th": "tha",
    "tr": "tur",
    "ua": "ukr",
    "vn": "vie",
    " ": "N/A"
}

languages_names = {
    "sa": "Arabic",
    "bd": "Bengali",
    "bg": "Bulgarian",
    "mm": "Burmese",
    "ct": "Catalan",
    "cn": "Chinese (Simp)",
    "hk": "Chinese (Trad)",
    "cz": "Czech",
    "dk": "Danish",
    "nl": "Dutch",
    "gb": "English",
    "ph": "Filipino",
    "fi": "Finnish",
    "fr": "French",
    "de": "German",
    "gr": "Greek",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "jp": "Japanese",
    "kr": "Korean",
    "my": "Malay",
    "mn": "Mongolian",
    "ir": "Persian",
    "pl": "Polish",
    "br": "Portuguese (Br)",
    "pt": "Portuguese (Pt)",
    "ro": "Romanian",
    "ru": "Russian",
    "rs": "Serbo-Croatian",
    "es": "Spanish (Es)",
    "mx": "Spanish (LATAM)",
    "se": "Swedish",
    "th": "Thai",
    "tr": "Turkish",
    "ua": "Ukrainian",
    "vn": "Vietnamese",
    " ": "Other"
}


# Get key from value
def __getKey(language, languages_dict):
    for key, value in languages_dict.items():
        if language == value:
            return key
    return " "


# Convert the inputted language into the format MangaDex uses
def getLangMD(language: str) -> Optional[str]:

    if len(language) < 2:
        print(language_error)
        return
    elif len(language) == 2:
        return language
    elif len(language) == 3:
        return __getKey(language, languages_iso)
    else:
        languages_match = [l for l in languages_names.values() if language.lower() in l.lower()]

        if len(languages_match) > 1:
            print("Found multiple matching languages, please choose the language you want to download from the following options.")

            for count, item in enumerate(languages_match, start=1):
                print(f'{count}: {item}')

            lang = int(input(f'Choose a number matching the position of the language: '))

            if lang not in range(1, (len(languages_match) + 1)):
                print(language_error)
                return
            else:
                lang_to_use = languages_match[(lang - 1)]
                return __getKey(lang_to_use, languages_names)
        else:
            return __getKey(languages_match[0], languages_names)
