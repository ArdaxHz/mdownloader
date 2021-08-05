#!/usr/bin/python3

import re

from .errors import MDownloaderError

language_error = 'Not a valid language option, exiting.'

languages = [{"english":"English","md":"en","iso":"eng"},{"english":"Japanese","md":"ja","iso":"jpn"},{"english":"Polish","md":"pl","iso":"pol"},{"english":"Serbo-Croatian","md":"sh","iso":"hrv"},{"english":"Dutch","md":"nl","iso":"dut"},{"english":"Italian","md":"it","iso":"ita"},{"english":"Russian","md":"ru","iso":"rus"},{"english":"German","md":"de","iso":"ger"},{"english":"Hungarian","md":"hu","iso":"hun"},{"english":"French","md":"fr","iso":"fre"},{"english":"Finnish","md":"fi","iso":"fin"},{"english":"Vietnamese","md":"vi","iso":"vie"},{"english":"Greek","md":"el","iso":"gre"},{"english":"Bulgarian","md":"bg","iso":"bul"},{"english":"Spanish (Es)","md":"es","iso":"spa"},{"english":"Portuguese (Br)","md":"pt-br","iso":"por"},{"english":"Portuguese (Pt)","md":"pt","iso":"por"},{"english":"Swedish","md":"sv","iso":"swe"},{"english":"Arabic","md":"ar","iso":"ara"},{"english":"Danish","md":"da","iso":"dan"},{"english":"Chinese (Simp)","md":"zh","iso":"chi"},{"english":"Bengali","md":"bn","iso":"ben"},{"english":"Romanian","md":"ro","iso":"rum"},{"english":"Czech","md":"cs","iso":"cze"},{"english":"Mongolian","md":"mn","iso":"mon"},{"english":"Turkish","md":"tr","iso":"tur"},{"english":"Indonesian","md":"id","iso":"ind"},{"english":"Korean","md":"ko","iso":"kor"},{"english":"Spanish (LATAM)","md":"es-la","iso":"spa"},{"english":"Persian","md":"fa","iso":"per"},{"english":"Malay","md":"ms","iso":"may"},{"english":"Thai","md":"th","iso":"tha"},{"english":"Catalan","md":"ca","iso":"cat"},{"english":"Filipino","md":"tl","iso":"fil"},{"english":"Chinese (Trad)","md":"zh-hk","iso":"chi"},{"english":"Ukrainian","md":"uk","iso":"ukr"},{"english":"Burmese","md":"my","iso":"bur"},{"english":"Lithuanian","md":"lt","iso":"lit"},{"english":"Hebrew","md":"he","iso":"heb"},{"english":"Hindi","md":"hi","iso":"hin"},{"english":"Norwegian","md":"no","iso":"nor"},{"english":"Other","md":"NULL","iso":"NULL"}]


def get_lang_iso(language: str) -> str:
    """Get the ISO 639-3 code of the language of the chapter.

    Args:
        language (str): ISO 639-2 code used by md.

    Returns:
        str: ISO 639-3 code.
    """
    language_iso = [l["iso"] for l in languages if language == l["md"]]

    if language_iso:
        return language_iso[0]
    return "N/A"


def get_lang_md(language: str) -> str:
    """Convert the inputted language into the format MangaDex uses

    Args:
        language (str): Can be the full language name, ISO 639-2 or ISO 639-3 codes.

    Raises:
        MDownloaderError: Couldn't find the language selected.

    Returns:
        str: ISO 639-2 code, which MangaDex uses for languages.
    """

    if len(language) < 2:
        raise MDownloaderError(language_error)
    elif re.match(r'^[a-zA-Z\-]{2,5}$', language):
        return language
    elif len(language) == 3:
        available_langs = [l["md"] for l in languages if l["iso"] == language]

        if available_langs:
            return available_langs[0]
        return "NULL"
    else:
        languages_match = [l for l in languages if language.lower() in l["english"].lower()]

        if len(languages_match) > 1:
            print("Found multiple matching languages, please choose the language you want to download from the following options.")

            for count, item in enumerate(languages_match, start=1):
                print(f'{count}: {item["english"]}')

            try:
                lang = int(input(f'Choose a number matching the position of the language: '))
            except ValueError:
                raise MDownloaderError("That's not a number.")

            if lang not in range(1, (len(languages_match) + 1)):
                raise MDownloaderError(language_error)

            lang_to_use = languages_match[(lang - 1)]
            return lang_to_use["md"]

        return languages_match[0]["md"]
