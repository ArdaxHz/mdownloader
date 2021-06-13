from .model import MDownloader


def convert_ids(md_model: MDownloader, download_type: str, ids_to_convert: list) -> list:
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
        'type': download_type,
        'ids': ids_to_convert
    }

    response = md_model.api.post_data(md_model.legacy_url, post_data=data)
    data = md_model.api.convert_to_json(md_model.id, f'{download_type}-legacy', response)

    for legacy in data:
        old_id = legacy["data"]["attributes"]["legacyId"]
        new_id = legacy["data"]["attributes"]["newId"]
        ids_dict = {"old_id": old_id, "new_id": new_id}
        new_ids.append(ids_dict)

    return new_ids


def get_id_type(md_model: MDownloader) -> None:
    """Get the id and download type from the url.

    Args:
        md_model (MDownloader): The base class this program runs on.
    """
    id_from_url, download_type_from_url = md_model.formatter.id_from_url(md_model.id)
    md_model.id = id_from_url
    md_model.download_type = download_type_from_url

    id_from_legacy(md_model, id_from_url)


def id_from_legacy(md_model: MDownloader, old_id: str) -> None:
    """Check if the id is only digits and use the default download type to try convert the ids.

    Args:
        md_model (MDownloader): The base class this program runs on.
        old_id (str): The old id to convert.
    """
    if old_id.isdigit():
        new_id = convert_ids(md_model, md_model.download_type, [int(old_id)])
        md_model.id = new_id[0]["new_id"]
        if md_model.debug: print(new_id)
