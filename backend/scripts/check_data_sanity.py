"""Data sanity checks for one city (also run as tests for singapore). Prints every problem; exit 1 if any.
Checks: coordinates inside the city bounding box; visit duration 15 min to 6 h; open before close; at least two weekly closures and one timed-entry (advance
booking) sight; the travel matrix is complete and symmetric; ids are unique; aliases are unique on NORMALISED forms (the resolver's own normalisation) and never equal
another place's name; hotel nightly rates inside a plausible band for the city's currency.
Usage:  python scripts/check_data_sanity.py singapore"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data.loader import load_all_city_datasets  # noqa: E402
from app.llm.names import normalise  # noqa: E402
from app.schemas import WEEKDAYS, to_minutes  # noqa: E402

# nightly rate bands (local currency) that a made-up demo hotel may plausibly have; a band is a sanity range, not a price claim
RATE_BANDS = {"singapore": (60, 600), "tokyo": (5_000, 60_000), "seoul": (50_000, 400_000), "kuala_lumpur": (80, 800)}
MIN_DURATION, MAX_DURATION = 15, 360


def problems(city_id: str, ds=None) -> list[str]:
    ds = ds or load_all_city_datasets()[city_id]
    out: list[str] = []
    b = ds.city.coordinate_bounds
    for a in ds.attractions.values():
        if not (b.lat_min <= a.lat <= b.lat_max and b.lon_min <= a.lon <= b.lon_max):
            out.append(f"{a.id}: coordinates {a.lat},{a.lon} are outside the {city_id} bounding box")
        if not MIN_DURATION <= a.duration_minutes <= MAX_DURATION:
            out.append(f"{a.id}: duration {a.duration_minutes} min is outside {MIN_DURATION}-{MAX_DURATION}")
        for day, v in a.opening_hours.items():
            if isinstance(v, list):
                for o, c in v:
                    if to_minutes(o) >= to_minutes(c):
                        out.append(f"{a.id}.{day}: opens {o} but closes {c}")
    closures = sum(v is None for a in ds.attractions.values() for v in a.opening_hours.values())
    if closures < 2:
        out.append(f"only {closures} weekly closure(s) in the data; at least 2 expected")
    if not any(a.advance_booking_required for a in ds.attractions.values()):
        out.append("no timed-entry (advance booking) sight; at least 1 expected")
    nodes = set(ds.attractions) | set(ds.hotels)
    for x in nodes:
        if set(ds.minutes.get(x, {})) < nodes - {x}:
            out.append(f"travel matrix: row {x} is incomplete")
    for x in nodes:
        for y in nodes:
            if x != y and ds.minutes[x][y] != ds.minutes[y][x]:
                out.append(f"travel matrix is not symmetric: {x}->{y} {ds.minutes[x][y]} vs {y}->{x} {ds.minutes[y][x]}")
    ids = list(ds.attractions) + list(ds.hotels)
    if len(ids) != len(set(ids)):
        out.append("duplicate ids between attractions and hotels")
    seen: dict[str, str] = {}
    for a in ds.attractions.values():
        for form in {normalise(x) for x in [a.name, *a.aliases]}:
            if form in seen and seen[form] != a.id:
                out.append(f"alias or name '{form}' of {a.id} clashes with {seen[form]} (after normalisation)")
            seen[form] = a.id
    lo, hi = RATE_BANDS[city_id]
    for h in ds.hotels.values():
        if not lo <= h.nightly_rate <= hi:
            out.append(f"{h.id}: nightly rate {h.nightly_rate} is outside the plausible band {lo}-{hi}")
    return out


if __name__ == "__main__":
    ps = problems(sys.argv[1])
    for p in ps:
        print("PROBLEM:", p)
    print(f"{len(ps)} problem(s)." if ps else "0 problems.")
    sys.exit(1 if ps else 0)
