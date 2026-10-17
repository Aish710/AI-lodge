"""docs/worked-example.md is built from real /compare-hotels output and the evaluation files; check_claims.py covers its measured-frequency sentences."""
import importlib
import importlib.util
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
we = importlib.import_module("make_worked_example")
spec = importlib.util.spec_from_file_location("check_claims", ROOT / "scripts" / "check_claims.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)
TEXT = we.build()


def test_one_city_where_the_winner_changes_and_one_where_it_does_not_and_the_honest_label():
    assert "**The winner changes.**" in TEXT and "**The winner does not change.**" in TEXT
    assert "chosen to show the trade-off. They are not representative" in TEXT and "made up" in TEXT
    sections = {s.split("\n", 1)[0].strip(): s for s in TEXT.split("\n## ")[1:]}
    assert "The winner changes" in sections["Tokyo"] and "The winner does not change" in sections["Singapore"]
    assert set(sections) == {"Tokyo", "Singapore", "Seoul", "Kuala Lumpur"}


def test_the_tables_are_the_real_api_numbers_and_the_frequencies_are_the_evaluation_numbers():
    ev = json.loads((ROOT / "docs/eval-results.json").read_text())["metrics"]["hotel_value"]["vots"]["1000"]
    assert f"in {ev['cheapest_by_rate_not_best']} of {ev['n_eligible']} trips where all three hotels were feasible" in TEXT
    cev = json.loads((ROOT / "docs/city-eval-results.json").read_text())["cities"]
    for city, name in (("singapore", "Singapore"), ("seoul", "Seoul"), ("kuala_lumpur", "Kuala Lumpur")):
        h = cev[city]["metrics"]["hotel_value"]["vots"]["1000"]
        assert f"in {h['cheapest_by_rate_not_best']} of {h['n_eligible']} eligible trips" in TEXT
    assert "57,100 JPY" in TEXT and "49,640 JPY" in TEXT          # Tokyo's pinned example, as the app returns it (also visible in test_frontend_examples)
    assert "-33 KRW" not in TEXT and " -" not in " ".join(l for l in TEXT.splitlines() if l.startswith("**The winner changes"))     # no negative amounts in the prose


def test_the_committed_file_matches_a_fresh_build_apart_from_its_timestamp():
    strip = lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("Generated "))      # noqa: E731
    assert strip((ROOT / "docs/worked-example.md").read_text()) == strip(TEXT), "re-run backend/scripts/make_worked_example.py"


def test_check_claims_flags_a_frequency_that_is_not_in_the_evaluation(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "worked-example.md").write_text("In the measured evaluation, the lowest-rate hotel was not best in 99 of 52 trips.\n")
    assert [b[2] for b in cc.worked_example_pairs(ROOT, tmp_path)] == ["99 of 52"]
    assert cc.worked_example_pairs(ROOT, ROOT) == []
