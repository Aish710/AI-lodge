#!/usr/bin/env python3
"""Summarise the user test: reads docs/user-test/results.csv, writes docs/user-test/summary.md (N, medians, quotes verbatim).
Nothing is invented or pre-filled: with no rows it says so. Extra CSV columns are refused (so personal data cannot slip in), and a quote that
looks like an email address or phone number is refused. Usage:  python scripts/summarise_user_test.py [--csv FILE] [--out FILE]"""
import csv
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["participant_id", "date", "city", "completed_task", "task_seconds", "manual_estimate_minutes",
           "q1_clear", "q2_trust", "q3_understood", "q4_useful", "q5_would_use", "quote"]
QUESTIONS = [("q1_clear", "It was clear what to do at each step"), ("q2_trust", "I trust the costs shown"),
             ("q3_understood", "I understand why the plan looks the way it does"), ("q4_useful", "This would save me effort when planning a trip"),
             ("q5_would_use", "I would use something like this for a real trip")]
PII = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?<!\d)(?:\+?\d[\s().-]?){8,}\d")


class UserTestError(ValueError):
    pass


def load_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise UserTestError(f"the CSV header must be exactly: {','.join(COLUMNS)} (got: {','.join(reader.fieldnames or [])}). Extra columns are refused.")
        rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    seen = set()
    for i, r in enumerate(rows, start=2):
        pid = r["participant_id"].strip()
        if not pid or pid in seen:
            raise UserTestError(f"row {i}: participant_id is required and must be unique")
        seen.add(pid)
        if r["completed_task"].strip().lower() not in ("yes", "no"):
            raise UserTestError(f"row {i}: completed_task must be yes or no")
        try:
            if r["completed_task"].strip().lower() == "yes":
                if int(r["task_seconds"]) < 0:
                    raise ValueError
            if float(r["manual_estimate_minutes"]) < 0:
                raise ValueError
            for q, _ in QUESTIONS:
                if not 1 <= int(r[q]) <= 5:
                    raise ValueError
        except ValueError:
            raise UserTestError(f"row {i}: task_seconds, manual_estimate_minutes and q1..q5 must be numbers (q1..q5 from 1 to 5)") from None
        if PII.search(r["quote"] or "") or PII.search(r["participant_id"]):
            raise UserTestError(f"row {i}: the quote or id looks like an email address or phone number; remove personal data")
    return rows


def num(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))


def summarise(rows: list[dict]) -> str:
    out = ["# User test summary", ""]
    if not rows:
        return "\n".join(out + ["No results yet (N = 0). Nothing here is filled in.", ""])
    done = [r for r in rows if r["completed_task"].strip().lower() == "yes"]
    out += [f"N = {len(rows)} participants. Completed the 5-minute task: {len(done)} of {len(rows)}. Small sample: indicative, not a benchmark.", ""]
    if done:
        t = [int(r["task_seconds"]) / 60 for r in done]
        m = [float(r["manual_estimate_minutes"]) for r in done]
        diff = [mm - tt for tt, mm in zip(t, m)]
        out += ["## Time", "", "| Measure | Median | N |", "|---|---|---|",
                f"| Time to an itinerary, measured (minutes) | {num(statistics.median(t))} | {len(done)} |",
                f"| Same task without the app, participants' own estimate (minutes) | {num(statistics.median(m))} | {len(done)} |",
                f"| Estimate minus measured time (minutes) | {num(statistics.median(diff))} | {len(done)} |", "",
                "The estimate is what each person guessed, not a measured time, so the difference is not a controlled comparison.", ""]
    out += ["## Questions (1 = strongly disagree, 5 = strongly agree)", "", "| Statement | Median | Lowest | Highest | N |", "|---|---|---|---|---|"]
    for key, text in QUESTIONS:
        v = [int(r[key]) for r in rows]
        out.append(f"| {text} | {num(statistics.median(v))} | {min(v)} | {max(v)} | {len(v)} |")
    quotes = [(r["participant_id"].strip(), r["quote"].strip()) for r in rows if r["quote"].strip()]
    out += ["", "## What people said (verbatim)", ""]
    out += [f'- "{q}" ({p})' for p, q in quotes] if quotes else ["- No quotes were recorded."]
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
