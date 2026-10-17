#!/usr/bin/env python3
"""Append ONE validated row to docs/user-test/redteam-human.csv from prompts. Never pre-fills. Refuses emails and phone numbers in any free-text column.
attempt_id is assigned (H1, H2, ...). Usage:  python scripts/add_human_attack.py [--csv FILE] [--answers FILE.json]"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ["attempt_id", "language", "category", "short_description", "outcome", "note"]
LANGUAGES = ("en", "ms", "ko", "zh", "other")
CATEGORIES = ("wrong_city", "other_language", "ignore_instructions", "prompt_or_key", "odd_currency", "invented_places_prices", "unsupported_claims", "change_box", "other")
OUTCOMES = ("blocked", "asked_a_question", "model_misread_but_final_ok", "final_result_wrong", "other")
PII = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?<!\d)(?:\+?\d[\s().-]?){8,}\d")


class HumanRedteamError(ValueError):
    pass


def check_row(r: dict, where: str = "this row") -> None:
    if r["language"].strip() not in LANGUAGES:
        raise HumanRedteamError(f"{where}: language must be one of {', '.join(LANGUAGES)}")
    if r["category"].strip() not in CATEGORIES:
        raise HumanRedteamError(f"{where}: category must be one of {', '.join(CATEGORIES)}")
    if r["outcome"].strip() not in OUTCOMES:
        raise HumanRedteamError(f"{where}: outcome must be one of {', '.join(OUTCOMES)}")
    if not r["short_description"].strip() or len(r["short_description"]) > 300 or len(r["note"]) > 300:
        raise HumanRedteamError(f"{where}: short_description is required; description and note are at most 300 characters")
    if r["outcome"].strip() == "other" and not r["note"].strip():
        raise HumanRedteamError(f"{where}: outcome 'other' needs a note")
    for k in ("short_description", "note"):
        if PII.search(r[k] or ""):
            raise HumanRedteamError(f"{where}: {k} looks like an email address or phone number; remove personal data (names are not allowed either)")


def load_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise HumanRedteamError(f"the CSV header must be exactly: {','.join(COLUMNS)}. Extra columns are refused.")
        rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    seen = set()
    for i, r in enumerate(rows, start=2):
        if not re.fullmatch(r"H\d+", r["attempt_id"].strip()) or r["attempt_id"] in seen:
            raise HumanRedteamError(f"row {i}: attempt_id must be H1, H2, ... and unique")
        seen.add(r["attempt_id"])
        check_row(r, f"row {i}")
    return rows


def append_row(path: Path, row: dict) -> str:
    row = {k: str(row.get(k, "")).strip() for k in COLUMNS}
    existing = load_rows(path) if path.exists() and path.stat().st_size else []
    row["attempt_id"] = f"H{len(existing) + 1}"
    check_row(row)
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)
    return row["attempt_id"]


def main(argv: list[str]) -> int:
    path = Path(argv[argv.index("--csv") + 1]) if "--csv" in argv else ROOT / "docs" / "user-test" / "redteam-human.csv"
    try:
        if "--answers" in argv:
            row = json.loads(Path(argv[argv.index("--answers") + 1]).read_text(encoding="utf-8"))
        else:
            row = {"language": input(f"language ({'/'.join(LANGUAGES)}): "), "category": input(f"category ({'/'.join(CATEGORIES)}): "),
                   "short_description": input("what they tried, one sentence, no names: "), "outcome": input(f"outcome ({'/'.join(OUTCOMES)}): "), "note": input("note (optional): ")}
        aid = append_row(path, row)
    except HumanRedteamError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    print(f"added {aid} to {path}. Run scripts/summarise_human_redteam.py next.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
