"""Apply docs/data-verification/<city>-findings.json to a city's data files, deterministically and repeatably.

Writes (1) the `verification` block of every attraction and hotel and (2) the corrections the findings list, each only if the current value is the recorded
OLD value (or already the NEW one), so a wrong or stale findings file cannot silently overwrite data. Then rewrites docs/data-verification/CHANGELOG.md from the
findings. `source_status` is never touched: it stays "sample". Nothing here ever sets "human_verified" (only scripts/import_human_verification.py does).

Usage:  python scripts/apply_verification_findings.py singapore [--root DIR]      (--root is for tests)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FindingsError(ValueError):
    pass


def _dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply(city: str, root: Path = ROOT) -> list[dict]:
    findings = json.loads((root / "docs" / "data-verification" / f"{city}-findings.json").read_text(encoding="utf-8"))
    d = root / "backend" / "app" / "data" / "cities" / city
    atts = json.loads((d / "attractions.json").read_text(encoding="utf-8"))
    hotels = json.loads((d / "hotels.json").read_text(encoding="utf-8"))
    by_id = {a["id"]: a for a in atts}
    applied = []
    for aid, f in findings["attractions"].items():
        if aid not in by_id:
            raise FindingsError(f"findings name an unknown attraction id '{aid}'")
        a = by_id[aid]
        for c in f.get("corrections", []):
            if c["field"] != "opening_hours":
                raise FindingsError(f"{aid}: only opening_hours corrections are supported here (got {c['field']})")
            for day in c["days"]:
                new = c["new"][day] if isinstance(c["new"], dict) else c["new"]
                cur = a["opening_hours"][day]
                if cur == new:
                    continue
                if cur != c["old"]:
                    raise FindingsError(f"{aid}.{day}: the data holds {cur!r}, not the recorded old value {c['old']!r}; refusing to overwrite")
                a["opening_hours"][day] = new
                applied.append({"id": aid, "field": f"opening_hours.{day}", "old": c["old"], "new": new, "source_url": c["source_url"], "quote": c["quote"], "note": c.get("note", "")})
        v = dict(f["verification"])
        v.setdefault("visit_duration", {"state": "not_applicable", "note": "Visit durations are the project's own estimates, not a checkable fact."})
        a["verification"] = v
    na = findings["hotels"]["all"]["nightly_rate"]
    for h in hotels:
        h["verification"] = {"nightly_rate": na}
    _dump(d / "attractions.json", atts)
    _dump(d / "hotels.json", hotels)
    write_changelog(root, city, findings)
    return applied


def write_changelog(root: Path, city: str, findings: dict) -> None:
    lines = ["# Data verification changelog", "", f"City: **{city}**. Checked on {findings['checked_on']}. {findings['method']}", "",
             "All records keep `source_status: sample`. A correction is made only where an official page clearly states the value.", "",
             "## Corrections (old, new, source)", "", "| Attraction | Field | Old value | New value | Official source | What the page says |", "|---|---|---|---|---|---|"]
    n = 0
    for aid, f in findings["attractions"].items():
        for c in f.get("corrections", []):
            days = c["days"]
            new = c["new"]
            for day in days:
                nv = new[day] if isinstance(new, dict) else new
                lines.append(f"| {aid} | opening_hours.{day} | {json.dumps(c['old'])} | {json.dumps(nv)} | {c['source_url']} | \"{c['quote']}\" |")
                n += 1
    if not n:
        lines.append("| none | | | | | |")
    lines += ["", "Notes on corrections:", ""] + [f"- {aid}: {c['note']}" for aid, f in findings["attractions"].items() for c in f.get("corrections", []) if c.get("note")]
    lines += ["", "## Not changed, and why", "", f"- FX rate: {findings['fx']['note']}", f"- Travel-time calibration: {findings['calibration']['note']}", f"- Holiday notes: {findings['holiday_notes']['note']}", ""]
    (root / "docs" / "data-verification" / "CHANGELOG.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    root = Path(args[args.index("--root") + 1]) if "--root" in args else ROOT
    city = args[0]
    done = apply(city, root)
    print(f"applied {len(done)} day-level correction(s) for {city}")
