#!/usr/bin/env python3
"""Summarise the user test: reads docs/user-test/results.csv, writes docs/user-test/summary.md.
Informal, small N: it reports counts and medians and nothing else (no significance, no percentage saving). Nothing is pre-filled or invented: with no
rows it says so. Extra CSV columns are refused (so personal data cannot slip in), and free text that looks like an email address or phone number is
refused. Quotes are shown only where quote_ok is "yes".
Usage:  python scripts/summarise_user_test.py [--csv FILE] [--out FILE]"""
import csv
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["participant_id", "city", "winner_changed_in_comparison", "time_to_first_plan_seconds", "hotel_before", "confidence_before", "hotel_after",
           "confidence_after", "changed_choice", "why_changed", "self_estimated_manual_minutes", "rating_clear", "rating_trust", "rating_use",
           "rating_ai_helped", "rating_ai_findable", "confused_most", "quote_ok"]
CITIES = ("tokyo", "singapore", "seoul", "kuala_lumpur")
YESNO = ("winner_changed_in_comparison", "changed_choice", "quote_ok")
CONFIDENCE = ("confidence_before", "confidence_after")
RATINGS = [("rating_clear", "It was clear what to do"), ("rating_trust", "I trust the result"), ("rating_use", "I would use something like this"),
           ("rating_ai_helped", "The AI part helped"), ("rating_ai_findable", "It was easy to find the AI")]
FREE_TEXT = ("participant_id", "hotel_before", "hotel_after", "why_changed", "confused_most")
PII = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?<!\d)(?:\+?\d[\s().-]?){8,}\d")
PID = re.compile(r"^P([1-9]|10)$")


class UserTestError(ValueError):
    pass


def check_row(r: dict, where: str) -> None:
    """Raise UserTestError when a row is invalid. Used by the loader and by add_user_test_row.py, so both refuse the same things."""
    if not PID.match(r["participant_id"].strip()):
        raise UserTestError(f"{where}: participant_id must be an anonymous id P1 to P10")
    if r["city"].strip() not in CITIES:
        raise UserTestError(f"{where}: city must be one of {', '.join(CITIES)}")
    for k in YESNO:
        if r[k].strip().lower() not in ("yes", "no"):
            raise UserTestError(f"{where}: {k} must be yes or no")
    try:
        if int(r["time_to_first_plan_seconds"]) < 0 or float(r["self_estimated_manual_minutes"]) < 0:
            raise ValueError
        for k in CONFIDENCE + tuple(q for q, _ in RATINGS):
            if not 1 <= int(r[k]) <= 5:
                raise ValueError
    except ValueError:
        raise UserTestError(f"{where}: time and minutes must be non-negative numbers; confidence and ratings must be whole numbers from 1 to 5") from None
    for k in FREE_TEXT:
        if PII.search(r[k] or ""):
            raise UserTestError(f"{where}: {k} looks like an email address or phone number; remove personal data (names are not allowed either)")


def load_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise UserTestError(f"the CSV header must be exactly: {','.join(COLUMNS)} (got: {','.join(reader.fieldnames or [])}). Extra columns are refused.")
        rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    seen = set()
    for i, r in enumerate(rows, start=2):
        check_row(r, f"row {i}")
        pid = r["participant_id"].strip()
        if pid in seen:
            raise UserTestError(f"row {i}: participant_id must be unique")
        seen.add(pid)
    return rows


def num(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))


def _yes(r: dict, k: str) -> bool:
    return r[k].strip().lower() == "yes"


def summarise(rows: list[dict]) -> str:
    out = ["# User test summary", ""]
    if not rows:
        return "\n".join(out + ["No results yet (N = 0). Nothing here is filled in.", ""])
    n = len(rows)
    out += [f"N = {n} participants. Informal, small sample: indicative, not a benchmark, and nothing here is statistically significant. Self-reported where stated.", ""]
    t = [int(r["time_to_first_plan_seconds"]) for r in rows]
    m = [float(r["self_estimated_manual_minutes"]) for r in rows]
    out += ["## Planning time", "", "| Measure | Median | N |", "|---|---|---|",
            f"| Landing to first plan, with the app, timed by the observer (minutes) | {num(statistics.median(t) / 60)} | {n} |",
            f"| Same planning without the app, the participant's own estimate (self-reported, minutes) | {num(statistics.median(m))} | {n} |", "",
            "The second figure is a guess by each person, not a measured time, so the two are not a controlled comparison.", ""]
    cb = [int(r["confidence_before"]) for r in rows]
    ca = [int(r["confidence_after"]) for r in rows]
    changed = [r for r in rows if _yes(r, "changed_choice")]
    out += ["## Decision confidence and the hotel comparison", "", "| Measure | Value | N |", "|---|---|---|",
            f"| Median confidence (1 to 5) before seeing the comparison, nightly rates only | {num(statistics.median(cb))} | {n} |",
            f"| Median confidence (1 to 5) after seeing the comparison | {num(statistics.median(ca))} | {n} |",
            f"| Changed their hotel choice after the comparison | {len(changed)} of {n} | {n} |"]
    for label, flag in (("the app's best-value hotel differed from the cheapest-rate hotel", True), ("the best-value hotel was also the cheapest-rate hotel", False)):
        grp = [r for r in rows if _yes(r, "winner_changed_in_comparison") == flag]
        out.append(f"| Changed their choice, on trips where {label} | {sum(_yes(r, 'changed_choice') for r in grp)} of {len(grp)} | {len(grp)} |")
    out += ["", "Counts only: with this few people they say how it went for them, not how it would go for travellers in general.", ""]
    out += ["## Ratings (1 = strongly disagree, 5 = strongly agree)", "", "| Statement | Median | Lowest | Highest | N |", "|---|---|---|---|---|"]
    for key, text in RATINGS:
        v = [int(r[key]) for r in rows]
        out.append(f"| {text} | {num(statistics.median(v))} | {min(v)} | {max(v)} | {n} |")
    quotes = [(r["participant_id"].strip(), q.strip()) for r in rows if _yes(r, "quote_ok") for q in (r["why_changed"], r["confused_most"]) if q.strip()]
    out += ["", "## What people said (verbatim, only where they allowed quoting)", ""]
    out += [f'- "{q}" ({p})' for p, q in quotes] if quotes else ["- No quotes are shown (none recorded, or quoting was not allowed)."]
    return "\n".join(out + [""])


def main(argv: list[str]) -> int:
    csv_path = Path(argv[argv.index("--csv") + 1]) if "--csv" in argv else ROOT / "docs" / "user-test" / "results.csv"
    out_path = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "docs" / "user-test" / "summary.md"
    try:
        rows = load_rows(csv_path)
    except UserTestError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    out_path.write_text(summarise(rows), encoding="utf-8")
    print(f"wrote {out_path} (N = {len(rows)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
