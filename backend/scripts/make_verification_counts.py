"""Write docs/data-verification/counts.json and counts.md: per-city verification counts computed from the data files (never typed by hand).
The Proof page and the README sentence read these. Usage:  python scripts/make_verification_counts.py [--root DIR] [--first singapore]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data.loader import load_all_city_datasets  # noqa: E402
from app.verification import STATES, count_dataset  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def build(first: str = "singapore") -> dict:
    ds = load_all_city_datasets()
    ids = sorted(ds, key=lambda c: (c != first, c))
    cities = {c: count_dataset(ds[c]) for c in ids}
    total = {s: sum(cities[c][s] for c in ids) for s in STATES}
    f = cities[first]
    others = [c for c in ids if c != first]
    other_unchecked = all(cities[c]["source_checked"] == 0 and cities[c]["human_verified"] == 0 for c in others)
    sentence = (f"{ds[first].city.display_name}: {f['source_checked']} fields source-checked, {f['human_verified']} rows human-verified, {f['unchecked']} unchecked; "
                f"{'other cities unchecked' if other_unchecked else 'other cities partly checked'}; all data is still sample data")
    return {"first_city": first, "cities": cities, "source_checked": total["source_checked"], "human_verified": total["human_verified"],
            "unchecked": total["unchecked"], "not_applicable": total["not_applicable"], "readme_sentence": sentence,
            "note": "A field is one checkable group of an attraction (hours and closing days, admission, advance booking, coordinates, name and area), one alias spelling, or one hotel rate. "
                    "Visit durations and made-up hotel rates are not_applicable. source_checked means an official page stated the value; human_verified means a person confirmed it."}


def render(d: dict, names: dict) -> str:
    lines = ["# Data verification counts (generated)", "", "Computed by `backend/scripts/make_verification_counts.py` from the data files. " + d["note"], "",
             f"**{d['readme_sentence']}.**", "", "| City | Unchecked | Source-checked | Human-verified | Not applicable | Fields |", "|---|---|---|---|---|---|"]
    for c, v in d["cities"].items():
        lines.append(f"| {names.get(c, c)} | {v['unchecked']} | {v['source_checked']} | {v['human_verified']} | {v['not_applicable']} | {v['total_fields']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    args = sys.argv[1:]
    root = Path(args[args.index("--root") + 1]) if "--root" in args else ROOT
    first = args[args.index("--first") + 1] if "--first" in args else "singapore"
    d = build(first)
    out = root / "docs" / "data-verification"
    out.mkdir(parents=True, exist_ok=True)
    (out / "counts.json").write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    names = {c: v.city.display_name for c, v in load_all_city_datasets().items()}
    (out / "counts.md").write_text(render(d, names), encoding="utf-8")
    print(d["readme_sentence"])
