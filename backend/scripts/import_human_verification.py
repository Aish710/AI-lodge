"""Import a person's filled verification sheet (docs/data-verification/<city>.csv) into the city's data files.

A row counts ONLY if verified_value, verified_by AND date are all filled; a row with some but not all of them is REFUSED (nothing is imported). A fully blank row is skipped.
For each accepted row: the field's verification becomes human_verified (checked_by "human", the date, the row's source_url if any), and if verified_value differs from
value_in_app the data is corrected to it. `source_status` stays "sample". This is the ONLY code that sets human_verified.
Usage:  python scripts/import_human_verification.py singapore [--csv FILE] [--root DIR]"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from make_verification_sheets import COLUMNS, format_hours, parse_hours  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PII = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?<!\d)(?:\+?\d[\s().-]?){8,}\d")


class ImportError_(ValueError):
    pass


def _dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _apply_value(a: dict, field: str, value: str) -> None:
    v = value.strip()
    if field == "hours":
        a["opening_hours"] = parse_hours(v)
    elif field == "admission":
        a["admission_cost"] = None if v.lower() == "unknown" else int(v)
    elif field == "booking":
        if v.lower() not in ("yes", "no"):
            raise ValueError("booking must be yes or no")
        a["advance_booking_required"] = v.lower() == "yes"
    elif field == "coordinates":
        lat, lon = (float(x) for x in v.split(","))
        a["lat"], a["lon"] = lat, lon
    elif field == "name_area":
        name, _, area = v.partition("|")
        if not name.strip() or not area.strip():
            raise ValueError("name_area must look like 'Name | Area'")
        a["name"], a["area"] = name.strip(), area.strip()
    else:
        raise ValueError(f"unknown field '{field}'")


def import_sheet(city: str, csv_path: Path, root: Path = ROOT) -> dict:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ImportError_(f"the sheet header must be exactly: {','.join(COLUMNS)}")
        rows = list(reader)
    d = root / "backend" / "app" / "data" / "cities" / city
    atts = json.loads((d / "attractions.json").read_text(encoding="utf-8"))
    by_id = {a["id"]: a for a in atts}
    accepted, skipped, corrections = 0, 0, []
    todo = []
    for i, r in enumerate(rows, start=2):
        filled = [bool((r[k] or "").strip()) for k in ("verified_value", "verified_by", "date")]
        if not any(filled):
            skipped += 1
            continue
        if not all(filled):
            raise ImportError_(f"row {i} ({r['id']} {r['field']}): verified_value, verified_by and date must ALL be filled; nothing was imported")
        if not ISO.match(r["date"].strip()):
            raise ImportError_(f"row {i}: date must be YYYY-MM-DD")
        if PII.search(r["verified_by"]) or PII.search(r["verified_value"]):
            raise ImportError_(f"row {i}: verified_by or verified_value looks like an email address or phone number; use initials, not contact details")
        if r["id"] not in by_id:
            raise ImportError_(f"row {i}: unknown attraction id '{r['id']}'")
        todo.append((i, r))
    for i, r in todo:
        a = by_id[r["id"]]
        field = r["field"]
        ver = a.setdefault("verification", {})
        rec = {"state": "human_verified", "checked_on": r["date"].strip(), "checked_by": "human", "note": f"Confirmed by {r['verified_by'].strip()}."}
        if r["source_url"].strip():
            rec["source_url"] = r["source_url"].strip()
        if field.startswith("alias:"):
            alias = field[6:]
            if alias not in a["aliases"]:
                raise ImportError_(f"row {i}: '{alias}' is not an alias of {a['id']}")
            if r["verified_value"].strip() != alias:
                a["aliases"] = [r["verified_value"].strip() if x == alias else x for x in a["aliases"]]
                corrections.append((r["id"], field, alias, r["verified_value"].strip()))
                alias = r["verified_value"].strip()
            ver.setdefault("aliases", {})[alias] = rec
        else:
            before = {"hours": lambda: format_hours(a["opening_hours"]), "admission": lambda: "unknown" if a["admission_cost"] is None else str(a["admission_cost"]),
                      "booking": lambda: "yes" if a["advance_booking_required"] else "no", "coordinates": lambda: f"{a['lat']},{a['lon']}",
                      "name_area": lambda: f"{a['name']} | {a['area']}"}[field]()
            try:
                _apply_value(a, field, r["verified_value"])
            except (ValueError, TypeError) as e:
                raise ImportError_(f"row {i} ({r['id']} {field}): cannot read '{r['verified_value']}': {e}") from None
            if before != r["verified_value"].strip():
                corrections.append((r["id"], field, before, r["verified_value"].strip()))
            ver[field] = rec
        accepted += 1
    _dump(d / "attractions.json", atts)
    return {"accepted": accepted, "skipped_blank": skipped, "corrections": corrections}


if __name__ == "__main__":
    args = sys.argv[1:]
    root = Path(args[args.index("--root") + 1]) if "--root" in args else ROOT
    csv_path = Path(args[args.index("--csv") + 1]) if "--csv" in args else root / "docs" / "data-verification" / f"{args[0]}.csv"
    try:
        res = import_sheet(args[0], csv_path, root)
    except ImportError_ as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"imported {res['accepted']} row(s); {res['skipped_blank']} blank row(s) skipped; {len(res['corrections'])} value(s) corrected")
    for c in res["corrections"]:
        print("  corrected:", c)
