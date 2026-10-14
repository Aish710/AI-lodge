"""Every id in a request must belong to the request's city. An id that exists in ANOTHER city is rejected with a clear 422 that
names the id and the city it actually belongs to; an id that exists nowhere keeps its existing, route-specific error."""
from app.data.loader import Dataset
from app.hardening.errors import ApiError


def _owner(kind: str, item_id: str, ds: Dataset, all_datasets: dict[str, Dataset]) -> tuple[str, str] | None:
    """(city_id, display_name) of another city that has this id, or None."""
    for cid, other in all_datasets.items():
        if other is ds:
            continue
        table = other.hotels if kind == "hotel" else other.attractions
        if item_id in table:
            return cid, other.city.display_name
    return None


def reject_foreign_ids(ds: Dataset, all_datasets: dict[str, Dataset], *, hotels=(), attractions=()) -> None:
    """Raise ApiError(422, 'wrong_city') when any hotel/attraction id belongs to a different city than `ds`."""
    found = []
    for kind, ids in (("hotel", hotels), ("attraction", attractions)):
        table = ds.hotels if kind == "hotel" else ds.attractions
        for item_id in ids:
            if item_id in table:
                continue
            owner = _owner(kind, str(item_id), ds, all_datasets)
            if owner:
                found.append({"kind": kind, "id": str(item_id)[:64], "belongs_to_city": owner[0], "city_name": owner[1]})
    if found:
        first = found[0]
        raise ApiError(422, "wrong_city",
                       f"The {first['kind']} id '{first['id']}' belongs to {first['city_name']}, not {ds.city.display_name}. "
                       "One trip covers one city: start a new trip to use another city.", found)
