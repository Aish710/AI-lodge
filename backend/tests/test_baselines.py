"""Phase 1: three FAIR baselines (cheapest-first, convenience-first, joint) read off one comparison. Fairness, tie handling, zero and extreme values of time, infeasible hotels,
cost-breakdown consistency, and the API contract."""
import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.main import app
from app.money import missed_preference_penalty
from app.optimiser.baselines import CONVENIENCE_RULE, build_baselines, convenience_hotel, convenience_minutes, target_sights
from app.optimiser.hotel_compare import _breakdown, compare_hotels
from app.optimiser.solver import ObjectiveSpec, solve
from app.schemas import Preferences, nights_for

ALL = load_all_city_datasets()
EX = json.loads((Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "examples.json").read_text())


def prefs_for(city, **over):
    ex = EX[city]["valid"]
    f = ex["form"]
    p = dict(days=f["days"], pace=f["pace"], must_visit=[k for k, v in ex["wishlist"].items() if v == "must"], skip=[k for k, v in ex["wishlist"].items() if v == "skip"],
             day_start=f["dayStart"], day_end=f["dayEnd"], value_of_time_per_hour=f["valueOfTime"], start_weekday=f["startWeekday"])
    p.update(over)
    return Preferences(**p), ex["hotel_ids"]


def entries(comp):
    return {e.key: e for e in comp.baselines.entries}


@pytest.mark.parametrize("city", ["tokyo", "singapore", "seoul", "kuala_lumpur"])
def test_the_three_baselines_exist_and_are_read_off_the_same_comparison(city):
    ds = ALL[city]
    prefs, hotels = prefs_for(city)
    comp = compare_hotels(prefs, hotels, ds)
    e = entries(comp)
    assert list(e) == ["cheapest_rate", "convenience_first", "joint"]
    assert e["cheapest_rate"].hotel_id == comp.cheapest_by_rate and e["joint"].hotel_id == comp.best_by_true_cost
    assert e["convenience_first"].hotel_id == convenience_hotel(prefs, hotels, ds)
    byid = {r.hotel_id: r for r in comp.results}
    for x in e.values():                               # the very numbers the comparison ranked: same candidates, constraints, routing and objective by construction
        assert x.score_jpy == byid[x.hotel_id].breakdown.true_cost_jpy


@pytest.mark.parametrize("city", ["tokyo", "singapore", "seoul", "kuala_lumpur"])
def test_fairness_each_baseline_equals_an_independent_solve_of_its_hotel_with_the_same_objective(city):
    ds = ALL[city]
    prefs, hotels = prefs_for(city)
    comp = compare_hotels(prefs, hotels, ds, time_limit=600)
    spec = ObjectiveSpec("true_cost", prefs.value_of_time_per_hour, missed_preference_penalty(ds))
    nights, _ = nights_for(prefs)
    for x in comp.baselines.entries:
        if not x.feasible:
            continue
        res = solve(prefs, x.hotel_id, ds, objective=spec, with_alternatives=False, max_seconds=60)
        b = _breakdown(ds, prefs, x.hotel_id, res, nights, prefs.value_of_time_per_hour)
        assert b.true_cost_jpy == x.score_jpy and b.transport_jpy == x.transport_jpy and b.travel_minutes == x.travel_minutes, x.key


def test_every_entry_adds_up_and_the_score_is_never_called_spending():
    ds = ALL["tokyo"]
    prefs, hotels = prefs_for("tokyo")
    comp = compare_hotels(prefs, hotels, ds)
    for x in comp.baselines.entries:
        assert x.known_spend_jpy == x.accommodation_jpy + x.admissions_jpy + x.transport_jpy
        assert x.score_jpy == x.known_spend_jpy + x.travel_time_value_jpy + x.omitted_charge_jpy        # the objective-only estimate for unknown admissions is in NEITHER total
        assert x.objective_estimate_for_unknown_jpy >= 0
    assert "not money spent" in comp.baselines.note and "Sample data" in comp.baselines.note
    joint, cheap = entries(comp)["joint"], entries(comp)["cheapest_rate"]
    assert joint.score_jpy <= cheap.score_jpy                                    # the joint choice is never worse than the cheapest-first one on the shared score


def test_the_convenience_rule_uses_must_visits_else_every_sight_not_skipped_and_breaks_ties_by_rate_then_id():
    ds = ALL["tokyo"]
    hotels = sorted(ds.hotels)
    prefs = Preferences(days=2, must_visit=["senso_ji"], skip=["akihabara"], value_of_time_per_hour=1000)
    assert target_sights(prefs, ds) == ["senso_ji"]
    none = Preferences(days=2, skip=["akihabara"], value_of_time_per_hour=1000)
    assert "akihabara" not in target_sights(none, ds) and len(target_sights(none, ds)) == len(ds.attractions) - 1
    mins = convenience_minutes(prefs, hotels, ds)
    assert mins == {h: ds.minutes[h]["senso_ji"] for h in hotels} and convenience_hotel(prefs, hotels, ds) == min(hotels, key=lambda h: (mins[h], ds.hotels[h].nightly_rate, h))
    assert "ESTIMATED" in CONVENIENCE_RULE and "not at the day-by-day route" in CONVENIENCE_RULE


def test_equal_hotel_prices_are_a_deterministic_tie_for_the_cheapest_baseline():
    ds = ALL["tokyo"]
    same = {k: h.model_copy(update={"nightly_rate": 9000}) for k, h in ds.hotels.items()}
    ds2 = replace(ds, hotels=same)
    prefs, hotels = prefs_for("tokyo")
    c1, c2 = compare_hotels(prefs, hotels, ds2), compare_hotels(prefs, list(reversed(hotels)), ds2)
    assert entries(c1)["cheapest_rate"].hotel_id == entries(c2)["cheapest_rate"].hotel_id == min(hotels)          # ties -> lower hotel id
    assert all(x.accommodation_jpy == 18000 for x in c1.baselines.entries if x.feasible)
    assert c1.rate_winner_differs_from_true_winner == (c1.best_by_true_cost != min(hotels))


def test_zero_value_of_time_ignores_travel_time_and_the_joint_pick_is_the_lowest_money_plus_charge():
    ds = ALL["tokyo"]
    prefs, hotels = prefs_for("tokyo", value_of_time_per_hour=0)
    comp = compare_hotels(prefs, hotels, ds)
    assert all(x.travel_time_value_jpy == 0 for x in comp.baselines.entries if x.feasible)
    ok = [r for r in comp.results if r.breakdown]
    assert entries(comp)["joint"].hotel_id == min(ok, key=lambda r: (r.breakdown.true_cost_jpy, r.nightly_rate_jpy, r.hotel_id)).hotel_id
    assert all(r.breakdown.true_cost_jpy == r.breakdown.rooms_jpy + r.breakdown.admissions_jpy + r.breakdown.transport_jpy + r.breakdown.missed_preferences.penalty_jpy for r in ok)


def test_an_extreme_value_of_time_makes_the_joint_pick_a_least_travel_hotel_and_the_scores_stay_consistent():
    ds = ALL["tokyo"]
    prefs, hotels = prefs_for("tokyo", value_of_time_per_hour=100_000)
    comp = compare_hotels(prefs, hotels, ds, time_limit=600)
    ok = [r for r in comp.results if r.breakdown]
    best = entries(comp)["joint"]
    assert best.travel_minutes == min(r.breakdown.travel_minutes for r in ok) or best.omitted_optional != []      # time dominates; a sight count difference can still matter
    assert all(r.breakdown.true_cost_jpy == r.breakdown.rooms_jpy + r.breakdown.admissions_jpy + r.breakdown.transport_jpy + r.breakdown.time_cost_jpy + r.breakdown.missed_preferences.penalty_jpy for r in ok)


def test_an_infeasible_request_gives_infeasible_baselines_not_invented_numbers():
    ds = ALL["tokyo"]
    prefs = Preferences(days=1, must_visit=["senso_ji", "meiji_jingu", "tokyo_skytree", "shibuya_sky", "teamlab_planets"], pace="relaxed", value_of_time_per_hour=1000)
    comp = compare_hotels(prefs, sorted(ds.hotels)[:2], ds)
    for x in comp.baselines.entries:
        assert not x.feasible and x.score_jpy is None and x.known_spend_jpy is None and x.omitted_optional == []
    assert entries(comp)["joint"].hotel_id is None


def test_same_hotel_flags_say_when_baselines_agree():
    ds = ALL["tokyo"]
    prefs, hotels = prefs_for("tokyo")
    e = entries(compare_hotels(prefs, hotels, ds))
    for x in e.values():
        assert x.same_hotel_as == [k for k, y in e.items() if k != x.key and y.hotel_id == x.hotel_id]


def test_the_api_contract_carries_the_baselines_with_every_field_the_interface_reads():
    prefs, hotels = prefs_for("seoul")
    with TestClient(app) as c:
        r = c.post("/compare-hotels", json={"city_id": "seoul", "preferences": prefs.model_dump(), "hotel_ids": hotels, "include_sensitivity": False, "explain": False}).json()
    b = r["baselines"]
    assert [e["key"] for e in b["entries"]] == ["cheapest_rate", "convenience_first", "joint"] and set(b) == {"entries", "convenience_minutes", "target_sights", "note"}
    need = {"key", "label", "rule", "hotel_id", "hotel_name", "area", "feasible", "status", "accommodation_jpy", "admissions_jpy", "transport_jpy", "known_spend_jpy", "travel_minutes",
            "travel_time_value_jpy", "omitted_optional", "omitted_charge_jpy", "unknown_price_items", "objective_estimate_for_unknown_jpy", "score_jpy", "same_hotel_as"}
    assert all(need <= set(e) for e in b["entries"])
