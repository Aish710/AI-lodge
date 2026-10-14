"""Load and validate the curated dataset. Fails loudly, naming the bad record."""
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app import config
from app.schemas import Attraction, CityMeta, Hotel, WEEKDAYS, to_minutes

DATA_DIR = Path(__file__).resolve().parent
CITIES_DIR = DATA_DIR / "cities"
DEFAULT_CITY_ID = "tokyo"


class DataError(ValueError):
    """Raised when a dataset file or record is invalid."""


@dataclass(frozen=True)
class Dataset:
    city: CityMeta
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


def _load_records(path: Path, model, label: str, *, context: dict | None = None) -> dict:
    raw = _read_json(path)
    if not isinstance(raw, list):
        raise DataError(f"{path.name}: expected a list of records")
    out = {}
    for i, rec in enumerate(raw):
        rec_id = rec.get("id", "?") if isinstance(rec, dict) else "?"
        try:
            # JSON-mode strict validation: no silent str->int / float->int coercion.
            obj = model.model_validate_json(json.dumps(rec), context=context)
        except ValidationError as e:
            raise DataError(f"{path.name}: {label} #{i} (id={rec_id}) is invalid: {e}") from e
        if obj.id in out:
            raise DataError(f"{path.name}: duplicate id '{obj.id}'")
        out[obj.id] = obj
    return out


def load_attractions_file(path: Path) -> dict[str, Attraction]:
    return _load_records(Path(path), Attraction, "attraction")


def _default_city_meta() -> CityMeta:
    return CityMeta(
        id=DEFAULT_CITY_ID,
        display_name="Tokyo",
        country="Japan",
        currency_code="JPY",
        display_currency_code="SGD",
        sample_fx_to_display_currency=1 / config.SAMPLE_FX_JPY_PER_SGD,
        sample_fx_label=config.FX_LABEL,
        coordinate_bounds={"lat_min": 35.4, "lat_max": 35.95, "lon_min": 139.3, "lon_max": 140.0},
        transit_model={"detour_factor": 1.3, "speed_kmh": 20.0, "per_leg_overhead_min": 10, "base_fare": 150, "fare_per_km": 20},
        default_day_start=config.DEFAULT_DAY_START,
        default_day_end=config.DEFAULT_DAY_END,
        default_value_of_time_per_hour=config.DEFAULT_VALUE_OF_TIME_JPY_PER_HOUR,
        closing_day_conventions_note="Sample weekly closures follow each attraction record; verify before relying on them.",
        provenance="Tokyo sample pack. Figures are approximate and must be verified; hotels are fictional.",
    )


def load_city_meta(data_dir: Path = DATA_DIR) -> CityMeta:
    path = Path(data_dir) / "city.json"
    if not path.exists():
        return _default_city_meta()
    try:
        return CityMeta.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as e:
        raise DataError(f"{path.name}: city metadata is invalid: {e}") from e


def load_dataset(data_dir: Path = DATA_DIR) -> Dataset:
    data_dir = Path(data_dir)
    city = load_city_meta(data_dir)
    context = {"coordinate_bounds": city.coordinate_bounds}
    attractions = _load_records(data_dir / "attractions.json", Attraction, "attraction", context=context)
    hotels = _load_records(data_dir / "hotels.json", Hotel, "hotel", context=context)
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
    if m["_meta"].get("city_id", city.id) != city.id:
        raise DataError(f"travel_times.json: city_id does not match city.json ({m['_meta'].get('city_id')} != {city.id})")
    return Dataset(city, attractions, hotels, meta, minutes, fare)


def city_dir(city_id: str) -> Path:
    if not city_id or "/" in city_id or "\\" in city_id or city_id.startswith("."):
        raise DataError(f"unknown city id '{city_id}'")
    return CITIES_DIR / city_id


def load_city_dataset(city_id: str = DEFAULT_CITY_ID) -> Dataset:
    path = city_dir(city_id)
    if not path.exists():
        raise DataError(f"unknown city id '{city_id}'")
    return load_dataset(path)


def load_all_city_datasets(cities_dir: Path = CITIES_DIR) -> dict[str, Dataset]:
    out: dict[str, Dataset] = {}
    for path in sorted(Path(cities_dir).iterdir()):
        if path.is_dir() and (path / "city.json").exists():
            ds = load_dataset(path)
            if ds.city.id in out:
                raise DataError(f"duplicate city id '{ds.city.id}'")
            out[ds.city.id] = ds
    if DEFAULT_CITY_ID not in out:
        out[DEFAULT_CITY_ID] = load_dataset()
    return out


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
