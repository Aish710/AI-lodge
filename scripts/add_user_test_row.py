#!/usr/bin/env python3
"""Append ONE validated row to docs/user-test/results.csv from prompts. Never pre-fills anything: every answer is typed by you.
Refuses names, emails and phone numbers (the same checks as the summary script). Usage:  python scripts/add_user_test_row.py [--csv FILE]
For tests, answers can come from a JSON file instead of prompts:  --answers FILE.json"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("summarise_user_test", ROOT / "scripts" / "summarise_user_test.py")
ut = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ut)

PROMPTS = {
    "participant_id": "Participant id (P1 to P10, no names)",
    "city": "City they planned (tokyo / singapore / seoul / kuala_lumpur)",
    "winner_changed_in_comparison": "Read from the app: was the best-value hotel different from the cheapest-rate hotel? (yes/no)",
    "time_to_first_plan_seconds": "Observer's time from landing to first plan (seconds)",
    "hotel_before": "Hotel they would book, seeing nightly rates only",
    "confidence_before": "Confidence before the comparison (1-5)",
    "hotel_after": "Hotel they chose after the comparison",
    "confidence_after": "Confidence after the comparison (1-5)",
    "changed_choice": "Did the comparison change their choice? (yes/no)",
    "why_changed": "Why, in a few words (blank if none)",
    "self_estimated_manual_minutes": "Their own estimate: minutes to plan without the app (self-reported)",
    "rating_clear": "Rating 1-5: clear what to do", "rating_trust": "Rating 1-5: trust in the result", "rating_use": "Rating 1-5: would use something like this",
    "rating_ai_helped": "Rating 1-5: the AI part helped", "rating_ai_findable": "Rating 1-5: easy to find the AI",
    "confused_most": "What confused them most (blank if nothing)", "quote_ok": "Permission to quote anonymously? (yes/no)",
}
assert list(PROMPTS) == ut.COLUMNS


def append_row(csv_path: Path, row: dict) -> None:
    row = {k: str(row.get(k, "")).strip() for k in ut.COLUMNS}
    ut.check_row(row, "this row")
    existing = ut.load_rows(csv_path) if csv_path.exists() and csv_path.stat().st_size else []
    if any(r["participant_id"].strip() == row["participant_id"] for r in existing):
        raise ut.UserTestError(f"{row['participant_id']} is already in the file")
    new = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ut.COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)


def main(argv: list[str]) -> int:
    csv_path = Path(argv[argv.index("--csv") + 1]) if "--csv" in argv else ROOT / "docs" / "user-test" / "results.csv"
    try:
        if "--answers" in argv:
            row = json.loads(Path(argv[argv.index("--answers") + 1]).read_text(encoding="utf-8"))
        else:
            row = {k: input(f"{q}: ") for k, q in PROMPTS.items()}
        append_row(csv_path, row)
    except ut.UserTestError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    print(f"added {row['participant_id']} to {csv_path}. Run scripts/summarise_user_test.py next.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
