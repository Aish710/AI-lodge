"""Load and validate the curated dataset. Fails loudly, naming the bad record."""
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app import config
from app.schemas import Attraction, Hotel, WEEKDAYS, to_minutes

DATA_DIR = Path(__file__).resolve().parent


class DataError(ValueError):
    """Raised when a dataset file or record is invalid."""


@dataclass(frozen=True)
class Dataset:
    attractions: dict[str, Attraction]
    hotels: dict[str, Hotel]
    matrix_meta: dict
    minutes: dict[str, dict[str, int]]
    fare_jpy: dict[str, dict[str, int]]


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise DataError(f"{path.name}: cannot read file ({e})") from e


def _load_records(path: Path, model, label: str) -> dict:
    raw = _read_json(path)
    if not isinstance(raw, list):
        raise DataError(f"{path.name}: expected a list of records")
    out = {}
    for i, rec in enumerate(raw):
        rec_id = rec.get("id", "?") if isinstance(rec, dict) else "?"
        try:
            # JSON-mode strict validation: no silent str->int / float->int coercion.
            obj = model.model_validate_json(json.dumps(rec))
        except ValidationError as e:
            raise DataError(f"{path.name}: {label} #{i} (id={rec_id}) is invalid: {e}") from e
        if obj.id in out:
            raise DataError(f"{path.name}: duplicate id '{obj.id}'")
        out[obj.id] = obj
    return out


def load_attractions_file(path: Path) -> dict[str, Attraction]:
    return _load_records(Path(path), Attraction, "attraction")


def load_dataset(data_dir: Path = DATA_DIR) -> Dataset:
    data_dir = Path(data_dir)
    attractions = _load_records(data_dir / "attractions.json", Attraction, "attraction")
    hotels = _load_records(data_dir / "hotels.json", Hotel, "hotel")
    overlap = set(attractions) & set(hotels)
    if overlap:
        raise DataError(f"ids used by both an attraction and a hotel: {sorted(overlap)}")

    m = _read_json(data_dir / "travel_times.json")
    try:
        meta, nodes, minutes, fare = m["_meta"], m["nodes"], m["minutes"], m["fare_jpy"]
    except KeyError as e:
        raise DataError(f"travel_times.json: missing key {e}") from e
    expected = set(attractions) | set(hotels)
    if set(nodes) != expected:
        raise DataError(
            f"travel_times.json: nodes differ from dataset ids "
            f"(missing {sorted(expected - set(nodes))}, extra {sorted(set(nodes) - expected)}); "
            f"re-run scripts/build_travel_matrix.py"
        )
    return Dataset(attractions, hotels, meta, minutes, fare)


def validate_must_visit(ds: Dataset, ids: list[str]) -> None:
    unknown = [i for i in ids if i not in ds.attractions]
    if unknown:
        raise DataError(f"unknown must_visit attraction id(s): {unknown}")


def is_open(attraction: Attraction, weekday: str, time_hhmm: str) -> bool | str:
    """True / False / "unknown". Unknown hours are never treated as open."""
    if weekday not in WEEKDAYS:
        raise ValueError(f"bad weekday '{weekday}'")
    day = attraction.opening_hours[weekday]
    if day == "unknown":
        return "unknown"
    if day is None:
        return False
    t = to_minutes(time_hhmm)
    return any(to_minutes(o) <= t < to_minutes(c) for o, c in day)


def travel_minutes(ds: Dataset, a: str, b: str) -> int:
    try:
        return ds.minutes[a][b]
    except KeyError as e:
        raise DataError(f"no travel time between '{a}' and '{b}'") from e


def travel_fare(ds: Dataset, a: str, b: str) -> int:
    try:
        return ds.fare_jpy[a][b]
    except KeyError as e:
        raise DataError(f"no fare between '{a}' and '{b}'") from e


def unknown_price_placeholder(ds: Dataset) -> int:
    """JPY value used ONLY inside the optimiser for attractions with an unknown admission price."""
    if config.UNKNOWN_PRICE_PLACEHOLDER_OVERRIDE_JPY is not None:
        return config.UNKNOWN_PRICE_PLACEHOLDER_OVERRIDE_JPY
    known = [a.admission_cost for a in ds.attractions.values() if a.admission_cost is not None]
    return int(statistics.median(known)) if known else 0
