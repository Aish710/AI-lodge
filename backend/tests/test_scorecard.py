"""The judging scorecard is generated from files; it must not drift from them, and it must never grade itself."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_scorecard", ROOT / "scripts" / "make_scorecard.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
DOC = (ROOT / "docs" / "JUDGING-SCORECARD.md").read_text()


def test_the_three_criteria_are_covered_with_gaps_and_no_self_grading():
    for heading in ("## 1. AI Integration Effectiveness", "## 2. LLM Safety & Responsible AI", "## 3. Usefulness & Business Value"):
        assert heading in DOC
    assert DOC.count("**Remaining gaps:**") == 3
    assert not re.search(r"\b[A-F][+-]?\s*(grade|score)\b|\b\d+\s*/\s*(10|100)\b(?!\s*cases)|\bscore[: ]+\d", DOC, re.I)
    assert "does not grade anything" in DOC


def test_facts_in_the_scorecard_match_the_files_they_come_from():
    f = mod.facts()
    assert f"{f['risk_rows']} rows" in DOC
    assert f"{f['injections']} injection prompts" in DOC
    assert f["hardening"] in DOC
    assert (len(f["cities"]) == 4) and f"{len(f['cities'])} packs" in DOC


def test_unrun_things_are_stated_as_not_run_and_nothing_is_pre_filled():
    f = mod.facts()
    if not f["live_eval"]:
        assert "**Not run.** `backend/scripts/run_llm_live_eval.py`" in DOC
    if not f["user_rows"]:
        assert "**Not run.** The kit exists" in DOC
    if not f["verification_sheets"]:
        assert "no verification sheets exist yet" in DOC


def test_every_generated_claim_sentence_is_copied_verbatim():
    claims = (ROOT / "docs" / "README-claims.md").read_text()
    for key, text in mod.facts()["claims"]:
        assert text in claims and f"`{key}`: {text}" in DOC
