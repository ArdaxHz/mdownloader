from .constants import ImpVar
from .model import MDownloader


def legacyMap(md_model: MDownloader, download_type: str, ids_to_convert: list) -> list:
    """Convert the old MangaDex ids into the new ones.

    Args:
        md_model (MDownloader): The base class this program runs on.
        download_type (str): The type of ids to convert.
        ids_to_convert (list): Array of ids to convert.

    Returns:
        list: Array of new ids.
    """
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
    """Get the id and download type from the url.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    id_from_url, download_type_from_url = md_model.getIdFromUrl(md_model.id)
    md_model.id = id_from_url
    md_model.download_type = download_type_from_url

    idFromLegacy(md_model, id_from_url)


def idFromLegacy(md_model: MDownloader, old_id: str) -> None:
    """Check if the id is only digits and use the default download type to try convert the ids.

    Args:
        md_model (MDownloader): The base class this program runs on.
        old_id (str): The old id to convert.
    """
    if old_id.isdigit():
        new_id = legacyMap(md_model, md_model.download_type, [int(old_id)])
        md_model.id = new_id[0]["new_id"]
