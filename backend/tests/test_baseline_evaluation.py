"""The baseline evaluation reproduces the historical 4/52 Tokyo result, reports per city, keeps zero-gain cases, and its committed output is the output of the script."""
import importlib
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND / "scripts"))
be = importlib.import_module("run_baseline_evaluation")
RES = json.loads((ROOT / "docs" / "baseline-results.json").read_text())


def test_tokyo_at_the_default_value_of_time_reproduces_the_existing_evaluation():
    ev = json.loads((ROOT / "docs" / "eval-results.json").read_text())["metrics"]["hotel_value"]["vots"]["1000"]
    t = RES["cities"]["tokyo"]["by_multiple"]["1"]
    assert RES["cities"]["tokyo"]["default_value_of_time"] == 1000
    assert (t["joint_differs_from_cheapest"], t["n_eligible"]) == (ev["cheapest_by_rate_not_best"], ev["n_eligible"]) == (4, 52)


def test_every_city_is_reported_separately_with_the_value_of_time_as_multiples_of_its_own_default():
    assert list(RES["cities"]) == ["tokyo", "singapore", "seoul", "kuala_lumpur"]
    assert "never pooled" in (ROOT / "docs" / "baseline-results.md").read_text() and "SAMPLE data" in (ROOT / "docs" / "baseline-results.md").read_text()
    for c, r in RES["cities"].items():
        assert list(r["by_multiple"]) == ["0.5", "1", "2", "4"]
        assert [x["value_of_time_per_hour"] for x in r["by_multiple"].values()] == [round(r["default_value_of_time"] * m) for m in (0.5, 1, 2, 4)]


def test_zero_gain_cases_and_cases_where_the_joint_choice_equals_the_cheapest_are_counted_not_hidden():
    for r in RES["cities"].values():
        for x in r["by_multiple"].values():
            assert x["no_gain_vs_cheapest"] >= x["n_eligible"] - x["joint_differs_from_cheapest"]          # equal hotel -> equal score -> no gain
            assert x["joint_worse_than_a_baseline"] == 0                                                    # C minimises the same score, so it is never worse than A or B
            assert 0 <= x["joint_differs_from_cheapest"] <= x["n_eligible"] <= x["n_trips"]


def test_the_penalty_sensitivity_is_reported_per_city_and_the_decomposition_explains_the_dominance():
    for r in RES["cities"].values():
        p, d = r["penalty"], r["decomposition_summary"]
        assert p["n_eligible"] > 0 and 0 <= p["changes_when_charge_removed"] <= p["n_eligible"] and 0 <= p["changes_when_charge_doubled"] <= p["n_eligible"]
        assert d["n"] == p["n_eligible"] and d["least_travel_hotel_is_also_cheapest"] <= d["n"]


def test_percentage_improvement_is_only_defined_for_a_positive_baseline():
    assert be.pct(100, 90) == 10.0 and be.pct(0, 0) is None and be.pct(-5, -6) is None and be.pct(50, 50) == 0.0


def test_the_script_is_deterministic_in_quick_mode(tmp_path):
    be.main(["--quick", "--out", str(tmp_path)])
    a = json.loads((tmp_path / "baseline-results.json").read_text())
    be.main(["--quick", "--out", str(tmp_path)])
    b = json.loads((tmp_path / "baseline-results.json").read_text())
    for r in (a, b):
        r["meta"].pop("elapsed_seconds"), r["meta"].pop("date"), r["meta"].pop("commit")
    assert a == b and a["meta"]["quick"] is True


def test_the_committed_json_matches_a_fresh_full_run_for_the_smallest_city_slice():
    ds = importlib.import_module("app.data.loader").load_all_city_datasets()["singapore"]
    fresh = be.run_city(ds, 20, be.CITY_SEED, False)
    assert fresh["by_multiple"] == RES["cities"]["singapore"]["by_multiple"], "re-run backend/scripts/run_baseline_evaluation.py"
