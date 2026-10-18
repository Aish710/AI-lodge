#!/usr/bin/env python3
"""Every number in the three submission drafts (README.md, docs/submission/devpost.md, docs/submission/linkedin.md) must appear in a GENERATED or recorded evidence file.
Lists every number that does not (file:line, the number, the sentence), checks the README's seven required headings in order, and lists every [PLACEHOLDER: ...] still to fill.
Exit 1 if any number is unmatched or a heading is missing. It checks that a number EXISTS in the evidence, not that the sentence around it is right: read the sentences too.

Numbers that are structure, not claims, are ignored: list and section numbers, dates, URLs, code spans and fenced code, a model id, and a short allowlist of tool versions.
Usage:  python scripts/check_claims.py [--root REPO] [--drafts DIR]      (--drafts defaults to --root; the test uses fixture trees)"""
import json
import re
import sys
from pathlib import Path

SLOTS = {"**User test (informal, small N):**": "docs/user-test/summary.md", "**Human red team (informal, small N):**": "docs/user-test/redteam-human-summary.md"}
DRAFTS = ["README.md", "docs/submission/devpost.md", "docs/submission/linkedin.md"]
CORPUS = ["docs/SUBMISSION-FACTS.md", "docs/eval-results.md", "docs/eval-results.json", "docs/README-claims.md", "docs/city-eval-results.md", "docs/baseline-results.md", "docs/baseline-results.json", "docs/itinerary-study.md", "docs/itinerary-study.json", "docs/profile-results.md", "docs/profile-results.json", "docs/hotel-comparison-results.md",
          "docs/hardening-results.md", "docs/worked-example.md", "docs/lighthouse-results.md", "docs/lighthouse-summary.json", "docs/ai-selfcheck.md", "docs/ai-selfcheck-history.md",
          "docs/redteam-results.md", "docs/redteam-results.json", "docs/redteam-live.md", "docs/redteam-live-first-run.md",
          "docs/SAFETY_LOG.md", "docs/JUDGING-SCORECARD.md", "docs/BUILD_NOTES.md", "docs/ux-metrics.md", "docs/EVIDENCE-STATUS.md", "docs/test-summary-frontend.json",
          "docs/data-verification/counts.md", "docs/data-verification/counts.json", "docs/data-verification/CHANGELOG.md", "backend/tests/results/full-suite.json", "backend/tests/results/latest-full.md"]
CORPUS_GLOBS = ["docs/eval/gold-results-live-*.md"]
HEADINGS = ["Problem Statement", "Solution Overview", "Key Features", "AI Integration", "External Tools & Datasets", "Installation & Setup", "AI Safety & Limitations"]
STRUCTURAL = [r"claude-[a-z0-9.-]+", r"Python 3\.13", r"Node 22", r"Vue 3", r"Pydantic v2", r"\bv2\b", r"UTF-8", r"CP-SAT", r"OR-Tools", r"\bsha\d*\b", r"\b\d{1,2}(?::\d{2})\b",
              r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\b", r"\bOct(?:ober)?\.? \d{1,2}\b", r"\b\d{4}-\d{2}-\d{2}\b", r"\b\d{8}T\d{6}Z\b"]
NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")


def strip_markup(text: str) -> list[tuple[int, str]]:
    """[(line number, line text with structure removed)] for the lines that are prose."""
    out, fenced = [], False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        s = re.sub(r"\[PLACEHOLDER:[^\]]*\]", " ", line)
        s = re.sub(r"`[^`]*`", " ", s)                       # inline code: file names, commands
        s = re.sub(r"\]\([^)]*\)", "]", s)                   # link targets
        s = re.sub(r"https?://\S+", " ", s)
        s = re.sub(r"^\s*(#+\s*)?\d+[.)]\s", " ", s)         # "## 1." headings and "1." list items
        s = re.sub(r"^\s*(\*\*)?\d+\.(\*\*)?\s", " ", s)
        s = re.sub(r"\*\*\d+\.\s", "**", s)                  # "**1. What I built.**"
        for pat in STRUCTURAL:
            s = re.sub(pat, " ", s)
        s = re.sub(r"(?<=\d),(?=\d{3})", "", s)              # 1,000 -> 1000
        out.append((i, s))
    return out


def numbers(s: str) -> list[str]:
    return [m.group(0).rstrip("0").rstrip(".") if "." in m.group(0) else m.group(0) for m in NUM.finditer(s)]


PAIR = re.compile(r"(?<![\w.])(\d+) of (\d+)(?![\w])")


def corpus_text(root: Path) -> str:
    files = [root / c for c in CORPUS]
    for g in CORPUS_GLOBS:
        files += sorted(root.glob(g))
    return re.sub(r"(?<=\d),(?=\d{3})", "", "\n".join(f.read_text(encoding="utf-8") for f in files if f.exists()))


def corpus_numbers(root: Path) -> set[str]:
    files = [root / c for c in CORPUS]
    for g in CORPUS_GLOBS:
        files += sorted(root.glob(g))
    nums: set[str] = set()
    for f in files:
        if f.exists():
            t = f.read_text(encoding="utf-8")
            t = re.sub(r"(?<=\d),(?=\d{3})", "", t)
            nums.update(numbers(t))
    return nums


def worked_example_pairs(root: Path, drafts_root: Path) -> list[tuple[str, int, str, str]]:
    """The measured-frequency sentences of docs/worked-example.md ("k of N") must exist in the evaluation files they cite (the money amounts in its tables come straight
    from the API response, so only the evaluation figures are checked against evidence)."""
    p = drafts_root / "docs" / "worked-example.md"
    if not p.exists():
        return []
    ctext = "\n".join((root / c).read_text(encoding="utf-8") for c in ("docs/eval-results.md", "docs/city-eval-results.md", "docs/README-claims.md") if (root / c).exists())
    bad = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if "evaluation" in line and " of " in line:
            for a, b in PAIR.findall(line):
                if not re.search(rf"(?<![\w.]){a} of {b}(?![\w])", ctext):
                    bad.append(("docs/worked-example.md", i, f"{a} of {b}", line.strip()[:160]))
    return bad


def check(root: Path, drafts_root: Path) -> dict:
    have = corpus_numbers(root)
    ctext = corpus_text(root)
    pair_ok = lambda a, b: bool(re.search(rf"(?<![\w.]){a}(?: of |/){b}(?![\w])", ctext))   # "20 of 20" or "20/20": the pair itself must be in the evidence, not just the digits
    unmatched, placeholders, missing_files = worked_example_pairs(root, drafts_root), [], []
    for rel in DRAFTS:
        p = drafts_root / rel
        if not p.exists():
            missing_files.append(rel)
            continue
        text = p.read_text(encoding="utf-8")
        placeholders += [(rel, i + 1, m) for i, l in enumerate(text.splitlines()) for m in re.findall(r"\[PLACEHOLDER:[^\]]*\]", l)]
        for i, s in strip_markup(text):
            slot = next((f for k, f in SLOTS.items() if k in text.splitlines()[i - 1]), None)
            if slot:       # a result slot: its numbers must come from ITS summary file, nowhere else
                sp = root / slot
                snums = set(numbers(re.sub(r"(?<=\d),(?=\d{3})", "", sp.read_text(encoding="utf-8")))) if sp.exists() else set()
                for n in numbers(re.sub(r"\*\*[^*]*\*\*", " ", s)):
                    if n not in snums:
                        unmatched.append((rel, i, n, f"slot number not in {slot}: " + text.splitlines()[i - 1].strip()[:120]))
                continue
            for n in numbers(s):
                if n not in have:
                    unmatched.append((rel, i, n, text.splitlines()[i - 1].strip()[:160]))
            for a, b in PAIR.findall(s):
                if not pair_ok(a, b):
                    unmatched.append((rel, i, f"{a} of {b}", text.splitlines()[i - 1].strip()[:160]))
    heads = []
    readme = drafts_root / "README.md"
    if readme.exists():
        heads = [re.sub(r"^\d+\.\s*", "", m.group(1)).strip() for m in re.finditer(r"^##\s+(.+)$", readme.read_text(encoding="utf-8"), re.M)]
    order = [h for h in heads if h in HEADINGS]
    heading_ok = order[:7] == HEADINGS
    return {"unmatched": unmatched, "placeholders": placeholders, "missing_files": missing_files, "headings": heads, "heading_ok": heading_ok}


def main(argv: list[str]) -> int:
    root = Path(argv[argv.index("--root") + 1]).resolve() if "--root" in argv else Path(__file__).resolve().parents[1]
    drafts = Path(argv[argv.index("--drafts") + 1]).resolve() if "--drafts" in argv else root
    r = check(root, drafts)
    print("README headings (in order):", " | ".join(r["headings"]))
    print("Required headings present and in order:", "yes" if r["heading_ok"] else "NO")
    for f in r["missing_files"]:
        print(f"MISSING draft: {f}")
    for rel, line, n, sentence in r["unmatched"]:
        print(f"UNMATCHED {rel}:{line} | {n} | {sentence}")
    print(f"\n{len(r['placeholders'])} placeholder(s) to fill:")
    for rel, line, m in r["placeholders"]:
        print(f"  {rel}:{line} {m}")
    print(f"\n{len(r['unmatched'])} unmatched number(s).")
    return 1 if (r["unmatched"] or not r["heading_ok"] or r["missing_files"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
