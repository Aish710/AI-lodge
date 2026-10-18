#!/usr/bin/env python3
"""Summarise docs/user-test/study-v2-results.csv (real sessions only). With no rows it says so; it never fills anything in. Usage: python scripts/summarise_study_v2.py [--root DIR]"""
import csv
import statistics
import sys
from pathlib import Path

root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path(__file__).resolve().parents[1]
src, dst = root / "docs/user-test/study-v2-results.csv", root / "docs/user-test/study-v2-summary.md"
rows = [r for r in csv.DictReader(src.read_text(encoding="utf-8").splitlines()) if r.get("participant_id")]
if not rows:
    dst.write_text("# Study v2 summary\n\nNo results yet (N = 0). The study has not been conducted. Nothing here is filled in.\n", encoding="utf-8")
    print("no results")
    sys.exit(0)
people = sorted({r["participant_id"] for r in rows})
L = ["# Study v2 summary", "", f"N = {len(people)} participants, {len(rows)} task rows. Small sample: counts and medians only; nothing is significant.", "",
     "| Workflow | Task rows | Completed | Median seconds | Median errors | Median ease (1-5) | Median confidence (1-5) | Median usefulness (1-5) |", "|---|---|---|---|---|---|---|---|"]


def med(xs):
    xs = [float(x) for x in xs if x not in ("", None)]
    return round(statistics.median(xs), 1) if xs else "-"


for w in sorted({r["workflow"] for r in rows}):
    rs = [r for r in rows if r["workflow"] == w]
    L.append(f"| {w} | {len(rs)} | {sum(r['completed'].lower() in ('yes', 'true', '1') for r in rs)} | {med(r['seconds'] for r in rs)} | {med(r['errors'] for r in rs)} | {med(r['ease_1to5'] for r in rs)} | {med(r['confidence_1to5'] for r in rs)} | {med(r['usefulness_1to5'] for r in rs)} |")
L += ["", "Report participants who struggled exactly as recorded in `notes`.", ""]
dst.write_text("\n".join(L), encoding="utf-8")
print(f"summary of {len(people)} participants written")
