#!/usr/bin/python3

import re

from .errors import MDownloaderError

language_error = 'Not a valid language option, exiting.'

languages = [{"English":"English","md":"en","iso":"eng"},{"English":"Japanese","md":"ja","iso":"jpn"},{"English":"Polish","md":"pl","iso":"pol"},{"English":"Serbo-Croatian","md":"sh","iso":"hrv"},{"English":"Dutch","md":"nl","iso":"dut"},{"English":"Italian","md":"it","iso":"ita"},{"English":"Russian","md":"ru","iso":"rus"},{"English":"German","md":"de","iso":"ger"},{"English":"Hungarian","md":"hu","iso":"hun"},{"English":"French","md":"fr","iso":"fre"},{"English":"Finnish","md":"fi","iso":"fin"},{"English":"Vietnamese","md":"vi","iso":"vie"},{"English":"Greek","md":"el","iso":"gre"},{"English":"Bulgarian","md":"bg","iso":"bul"},{"English":"Spanish (Es)","md":"es","iso":"spa"},{"English":"Portuguese (Br)","md":"pt-br","iso":"por"},{"English":"Portuguese (Pt)","md":"pt","iso":"por"},{"English":"Swedish","md":"sv","iso":"swe"},{"English":"Arabic","md":"ar","iso":"ara"},{"English":"Danish","md":"da","iso":"dan"},{"English":"Chinese (Simp)","md":"zh","iso":"chi"},{"English":"Bengali","md":"bn","iso":"ben"},{"English":"Romanian","md":"ro","iso":"rum"},{"English":"Czech","md":"cs","iso":"cze"},{"English":"Mongolian","md":"mn","iso":"mon"},{"English":"Turkish","md":"tr","iso":"tur"},{"English":"Indonesian","md":"id","iso":"ind"},{"English":"Korean","md":"ko","iso":"kor"},{"English":"Spanish (LATAM)","md":"es-la","iso":"spa"},{"English":"Persian","md":"fa","iso":"per"},{"English":"Malay","md":"ms","iso":"may"},{"English":"Thai","md":"th","iso":"tha"},{"English":"Catalan","md":"ca","iso":"cat"},{"English":"Filipino","md":"tl","iso":"fil"},{"English":"Chinese (Trad)","md":"zh-hk","iso":"chi"},{"English":"Ukrainian","md":"uk","iso":"ukr"},{"English":"Burmese","md":"my","iso":"bur"},{"English":"Lithuanian","md":"lt","iso":"lit"},{"English":"Hebrew","md":"he","iso":"heb"},{"English":"Hindi","md":"hi","iso":"hin"},{"English":"Norwegian","md":"no","iso":"nor"},{"English":"Other","md":"NULL","iso":"NULL"}]


def getLangIso(language: str) -> str:
    language_iso = [l["iso"] for l in languages if language == l["md"]]

    if language_iso:
        return language_iso[0]
    return "N/A"


def getLangMD(language: str) -> str:
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
        languages_match = [l for l in languages if language.lower() in l["English"].lower()]

        if len(languages_match) > 1:
            print("Found multiple matching languages, please choose the language you want to download from the following options.")

            for count, item in enumerate(languages_match, start=1):
                print(f'{count}: {item["English"]}')

            lang = int(input(f'Choose a number matching the position of the language: '))

            if lang not in range(1, (len(languages_match) + 1)):
                raise MDownloaderError(language_error)

            lang_to_use = languages_match[(lang - 1)]
            return lang_to_use["md"]

        return languages_match[0]["md"]
