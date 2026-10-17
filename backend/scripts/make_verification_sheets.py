"""Write docs/data-verification/<city>.csv: one row per checkable field and alias, LOW confidence first, for a person to fill in.
Columns: id, field, value_in_app, confidence, what_to_check, source_url, verified_value, verified_by, date. The last three are always BLANK here; source_url is
pre-filled only where the web-assisted check found one. Formats a person can type back:
  hours        mon=10:00-12:00,14:00-16:00;tue=closed;wed=unknown;...        admission  integer | unknown        booking  yes | no
  coordinates  lat,lon                                                       name_area  Name | Area                alias  the spelling
Usage:  python scripts/make_verification_sheets.py singapore [--root DIR]"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data.loader import load_all_city_datasets  # noqa: E402
from app.schemas import WEEKDAYS  # noqa: E402
from app.verification import attraction_fields  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
COLUMNS = ["id", "field", "value_in_app", "confidence", "what_to_check", "source_url", "verified_value", "verified_by", "date"]
ORDER = {"low": 0, "medium": 1, "high": 2}


def format_hours(oh: dict) -> str:
    def one(v):
        if v is None:
            return "closed"
        if v == "unknown":
            return "unknown"
        return ",".join(f"{a}-{b}" for a, b in v)
    return ";".join(f"{d}={one(oh[d])}" for d in WEEKDAYS)


def parse_hours(text: str) -> dict:
    out = {}
    for part in text.strip().split(";"):
        day, _, val = part.partition("=")
        day, val = day.strip().lower(), val.strip().lower()
        if day not in WEEKDAYS:
            raise ValueError(f"unknown weekday '{day}'")
        if val == "closed":
            out[day] = None
        elif val == "unknown":
            out[day] = "unknown"
        else:
            rng = []
            for r in val.split(","):
                a, _, b = r.partition("-")
                rng.append([a.strip(), b.strip()])
            out[day] = rng
    if set(out) != set(WEEKDAYS):
        raise ValueError("hours must list all seven weekdays")
    return out


def _conf(state: str, base: str) -> str:
    return {"source_checked": "high", "human_verified": "high"}.get(state, base)


def rows_for(city: str, ds) -> list[dict]:
    rows = []
    for a in ds.attractions.values():
        fields = {g: (v, r) for g, v, r in attraction_fields(a)}
        value = {"hours": format_hours(a.opening_hours), "admission": "unknown" if a.admission_cost is None else str(a.admission_cost),
                 "booking": "yes" if a.advance_booking_required else "no", "coordinates": f"{a.lat},{a.lon}", "name_area": f"{a.name} | {a.area}"}
        what = {"hours": "Official page: opening hours for every weekday AND the weekly closing day(s). A day that is 'unknown' is a deliberate sample gap; fill it only if the official page states it.",
                "admission": "Official page: the base adult price for a visitor (say if the price varies by ticket type). Unknown stays 'unknown' if no price is stated.",
                "booking": "Official page: is advance booking or timed entry required (yes) or not (no)?",
                "coordinates": "Official address or map pin (decimal degrees, lat,lon). The sample values are approximate.",
                "name_area": "Official spelling of the name, and the neighbourhood it belongs to."}
        base_conf = {"hours": "low", "admission": "low", "booking": "low", "coordinates": "medium", "name_area": "medium"}
        for g in ("hours", "admission", "booking", "coordinates", "name_area"):
            _, rec = fields[g]
            rows.append({"id": a.id, "field": g, "value_in_app": value[g], "confidence": _conf(rec.state, base_conf[g]), "what_to_check": what[g],
                         "source_url": rec.source_url or "", "verified_value": "", "verified_by": "", "date": ""})
        for al in a.aliases:
            _, rec = fields[f"alias:{al}"]
            rows.append({"id": a.id, "field": f"alias:{al}", "value_in_app": al, "confidence": _conf(rec.state, "medium"),
                         "what_to_check": "Is this spelling a name people really use for this place (and not another place)?", "source_url": rec.source_url or "",
                         "verified_value": "", "verified_by": "", "date": ""})
    rows.sort(key=lambda r: ORDER[r["confidence"]])   # stable: low confidence first, original order kept inside a level
    return rows


def write(city: str, root: Path = ROOT, ds=None) -> Path:
    ds = ds or load_all_city_datasets()[city]
    path = root / "docs" / "data-verification" / f"{city}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows_for(city, ds))
    return path


if __name__ == "__main__":
    args = sys.argv[1:]
    root = Path(args[args.index("--root") + 1]) if "--root" in args else ROOT
    p = write(args[0], root)
    print(f"wrote {p}")
