#!/usr/bin/env python3
"""Summarise docs/user-test/redteam-human.csv into docs/user-test/redteam-human-summary.md: N, counts per outcome and category, and every attempt whose final result was wrong.
Informal, small N. Nothing is pre-filled. Usage:  python scripts/summarise_human_redteam.py [--csv FILE] [--out FILE]"""
import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("add_human_attack", ROOT / "scripts" / "add_human_attack.py")
ha = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ha)


def summarise(rows: list[dict]) -> str:
    out = ["# Human red team summary", ""]
    if not rows:
        return "\n".join(out + ["No human attempts yet (N = 0). Nothing here is filled in.", ""])
    wrong = [r for r in rows if r["outcome"].strip() == "final_result_wrong"]
    out += [f"Human attempts: {len(rows)}, final result wrong in {len(wrong)}. Informal, small N: it finds obvious holes, it is not coverage and not proof of safety.", "",
            "| Outcome | Attempts |", "|---|---|"]
    c = Counter(r["outcome"].strip() for r in rows)
    out += [f"| {o} | {c.get(o, 0)} |" for o in ha.OUTCOMES]
    out += ["", "| Category | Attempts | Final result wrong |", "|---|---|---|"]
    cats = Counter(r["category"].strip() for r in rows)
    for cat in ha.CATEGORIES:
        if cats.get(cat):
            out.append(f"| {cat} | {cats[cat]} | {sum(1 for r in wrong if r['category'].strip() == cat)} |")
    out += ["", "## Attempts whose final result was wrong", ""]
    out += [f"- {r['attempt_id']} ({r['language']}, {r['category']}): {r['short_description']}" + (f" Note: {r['note']}" if r["note"].strip() else "") for r in wrong] or ["- None."]
    return "\n".join(out + [""])


def main(argv: list[str]) -> int:
    csv_path = Path(argv[argv.index("--csv") + 1]) if "--csv" in argv else ROOT / "docs" / "user-test" / "redteam-human.csv"
    out_path = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "docs" / "user-test" / "redteam-human-summary.md"
    try:
        rows = ha.load_rows(csv_path)
    except ha.HumanRedteamError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    out_path.write_text(summarise(rows), encoding="utf-8")
    print(f"wrote {out_path} (N = {len(rows)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
