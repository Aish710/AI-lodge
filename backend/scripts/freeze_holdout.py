#!/usr/bin/env python3
"""Freeze an adversarial holdout CSV: validate its columns, record its sha256 and the freeze time, and later VERIFY that it has not changed. Nothing is evaluated here.
Required columns: id, language, city, entry_point (parse | parse-replan | explain | copilot | repair | style), attack_type, trust_boundary, intended_failure, author, text. Optional column: hostile_reply (a JSON model reply the tester wants a MOCK model to return; used only by the mock run).   `author` must be set per row: "independent" only if someone who did
not build the app wrote it, otherwise "developer". Usage:  python scripts/freeze_holdout.py FILE.csv          (freeze)      python scripts/freeze_holdout.py FILE.csv --verify"""
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ["id", "language", "city", "entry_point", "attack_type", "trust_boundary", "intended_failure", "author", "text"]
ENTRY = {"parse", "parse-replan", "explain", "copilot", "repair", "style"}
AUTHORS = {"independent", "developer"}
LANGS = {"en", "ko", "zh", "ms"}
CITIES = {"tokyo", "singapore", "seoul", "kuala_lumpur"}


def check(path: Path) -> tuple[list[dict], list[str]]:
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    errs = []
    if not rows:
        return rows, ["the file has no attacks"]
    missing = [c for c in REQUIRED if c not in rows[0]]
    if missing:
        return rows, [f"missing columns: {', '.join(missing)}"]
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        errs.append("duplicate ids")
    for r in rows:
        if r["entry_point"] not in ENTRY or r["author"] not in AUTHORS or r["language"] not in LANGS or r["city"] not in CITIES or not r["text"].strip():
            errs.append(f"{r['id']}: invalid entry_point, author, language, city or empty text")
    if not 30 <= len(rows) <= 50:
        errs.append(f"{len(rows)} attacks; the protocol asks for 30 to 50")
    return rows, errs


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".sha256")


def freeze(path: Path) -> dict:
    rows, errs = check(path)
    if errs:
        raise SystemExit("not frozen: " + "; ".join(errs))
    m = {"file": path.name, "sha256": digest(path), "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "attacks": len(rows),
         "authors": sorted({r["author"] for r in rows}), "label": "independent" if {r["author"] for r in rows} == {"independent"} else "developer-generated (or mixed): do not report as independent"}
    manifest_path(path).write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    return m


def verify(path: Path) -> bool:
    mp = manifest_path(path)
    return mp.exists() and json.loads(mp.read_text())["sha256"] == digest(path)


if __name__ == "__main__":
    f = Path(sys.argv[1])
    if "--verify" in sys.argv:
        ok = verify(f)
        print("unchanged since freeze" if ok else "CHANGED or never frozen")
        sys.exit(0 if ok else 1)
    print(json.dumps(freeze(f), indent=1))
