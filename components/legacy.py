from components.model import MDownloader
from .constants import ImpVar


def legacyMap(md_model: MDownloader, download_type: str, ids_to_convert: list) -> None:
    new_ids = []

    data = {
        "type": download_type,
        "ids": ids_to_convert
    }

    response = md_model.postData(f'{ImpVar.MANGADEX_API_URL}/legacy/mapping', data)
    data = md_model.convertJson(md_model.id, f'{download_type}-legacy', response)

    for legacy in data:
        old_id = legacy["data"]["attributes"]["legacyId"]
        new_id = legacy["data"]["attributes"]["newId"]
        ids_dict = {"old_id": old_id, "new_id": new_id}
        new_ids.append(ids_dict)

    return new_ids


def getIdType(md_model: MDownloader) -> None:
    id_from_url, download_type_from_url = md_model.getIdFromUrl(md_model.id)
    md_model.id = id_from_url
    md_model.download_type = download_type_from_url

    idFromLegacy(md_model, id_from_url)


def idFromLegacy(md_model: MDownloader, id_from_url: str) -> None:
    if id_from_url.isdigit():
        new_id = legacyMap(md_model, md_model.download_type, [int(id_from_url)])
        md_model.id = new_id[0]["new_id"]