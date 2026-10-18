"""Your itinerary vs the optimiser: fairness, arithmetic, honesty about different sights, and the API."""
import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.main import app
from app.optimiser.itinerary_compare import ItineraryInputError, evaluate_itinerary, place_user_plan
from app.optimiser.solver import solve
from test_baselines import prefs_for

ALL = load_all_city_datasets()


def _days_from_solver(city="tokyo"):
    p, hotels = prefs_for(city)
    ds = ALL[city]
    res = solve(p, hotels[0], ds, with_alternatives=False)
    return p, hotels[0], ds, [[s.attraction_id for s in d.stops] for d in res.days]


def test_the_optimisers_own_plan_ties_with_itself_for_the_same_sights():
    p, h, ds, days = _days_from_solver()
    r = evaluate_itinerary(p, h, ds, days, max_seconds=10)
    user, same, full = r["arms"]
    assert user["feasible"] and same["feasible"] and full["feasible"]
    assert r["same_sights"]["valid"] and r["same_sights"]["travel_minutes_saved"] >= 0 and r["same_sights"]["score_gain"] >= 0
    assert set(same["sights"]) == set(user["sights"])                                 # exactly the same sights: that is what makes it like-for-like
    assert same["known_spend_jpy"] == same["breakdown"]["rooms_jpy"] + same["breakdown"]["admissions_jpy"] + same["breakdown"]["transport_jpy"]
    assert same["score_jpy"] == same["breakdown"]["true_cost_jpy"]


def test_a_reversed_day_order_is_never_better_than_the_optimiser_for_the_same_sights():
    p, h, ds, days = _days_from_solver()
    rev = [list(reversed(d)) for d in days]
    r = evaluate_itinerary(p, h, ds, rev, max_seconds=10)
    if r["arms"][0]["feasible"]:
        assert r["same_sights"]["score_gain"] >= 0
        assert r["same_sights"]["travel_minutes_saved"] is not None
    else:                                                       # a reversed order can break opening hours: then NO saving is reported
        assert r["same_sights"]["valid"] is False and r["same_sights"]["travel_minutes_saved"] is None
        assert r["verdict"]["kind"] in {"yours_infeasible", "no_like_for_like"}


def test_an_unplaceable_stop_is_reported_with_a_reason_and_no_saving_is_claimed():
    p, h, ds, days = _days_from_solver()
    crowded = [[a for d in days for a in d]] + [[] for _ in days[1:]]          # everything on day 1
    res = place_user_plan(p, h, ds, crowded)
    if res.status == "feasible":
        pytest.skip("the whole trip fits on one day in this sample")
    r = evaluate_itinerary(p, h, ds, crowded, max_seconds=10)
    assert r["arms"][0]["feasible"] is False and r["same_sights"]["valid"] is False and r["same_sights"]["score_gain"] is None
    assert r["verdict"]["kind"] == "yours_infeasible" and "does not work as arranged" in r["verdict"]["text"]


def test_the_full_plan_says_when_it_visits_different_sights():
    p, h, ds, days = _days_from_solver()
    extra = [a for a in ds.attractions if a not in {x for d in days for x in d}][:2]
    r = evaluate_itinerary(p.model_copy(update={"value_of_time_per_hour": 20 * p.value_of_time_per_hour}), h, ds, [days[0] + extra] + days[1:], max_seconds=10)
    f = r["full_plan"]
    assert set(f["sights_left_out"]) <= set(r["target_sights"])
    if f["valid"]:
        assert f["different_sights"] == bool(f["sights_left_out"])


def test_input_errors_are_explicit():
    p, h, ds, days = _days_from_solver()
    for bad, code in (([], "empty_itinerary"), ([["nope"]], "unknown_attraction"), ([days[0] + days[0]], "duplicate_stop")):
        with pytest.raises(ItineraryInputError) as e:
            evaluate_itinerary(p, h, ds, bad, max_seconds=5)
        assert e.value.code == code
    with pytest.raises(ItineraryInputError) as e:
        evaluate_itinerary(p.model_copy(update={"must_visit": [days[0][0]]}), h, ds, [days[0][1:]] if len(days[0]) > 1 else [days[1]], max_seconds=5)
    assert e.value.code == "must_visit_not_in_itinerary"


def test_the_api_route_returns_the_arms_a_verdict_and_a_fingerprint_and_rejects_foreign_ids():
    p, h, ds, days = _days_from_solver()
    body = {"city_id": "tokyo", "preferences": p.model_dump(), "hotel_id": h, "days": days}
    with TestClient(app) as c:
        r = c.post("/evaluate-itinerary", json=body)
        assert r.status_code == 200, r.text
        j = r.json()
        assert [a["key"] for a in j["arms"]] == ["yours", "same_sights", "full_plan"] and j["fingerprint"] and j["verdict"]["text"]
        assert c.post("/evaluate-itinerary", json={**body, "days": [["definitely_not_an_attraction"]]}).status_code == 422
        assert c.post("/evaluate-itinerary", json={**body, "extra": 1}).status_code == 422


def test_every_field_the_interface_reads_is_in_the_response():
    import re
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "itinerary.js").read_text()
    p, h, ds, days = _days_from_solver()
    r = evaluate_itinerary(p, h, ds, days, max_seconds=10)
    arm = r["arms"][0]
    for f in set(re.findall(r"\ba\.([a-z_]+)", src)):
        assert f in arm, f
    for f in ("admissions_jpy", "transport_jpy"):
        assert f in arm["breakdown"]
    assert {"verdict", "target_sights", "full_plan", "same_sights"} <= set(r)
    assert {"sights_left_out", "different_sights"} <= set(r["full_plan"])


# ---- live draft check ---------------------------------------------------------------------------------------------------------------------------------
def test_the_draft_check_places_stops_validates_and_reports_cash_including_rooms_without_optimising():
    from app.optimiser.itinerary_compare import check_itinerary
    p, h, ds, days = _days_from_solver()
    r = check_itinerary(p, h, ds, days)
    assert r["feasible"] and r["cash"]["cash_total_with_rooms"] == r["cash"]["cash_total"] + r["cash"]["rooms"] and r["cash"]["rooms"] > 0
    assert all(s["placed"] and "start" in s for s in r["stops"]) and r["active_days"] == sum(1 for d in days if d)
    assert r["verification"] in ("verified", "conditional")


def test_the_draft_check_names_the_stop_that_cannot_happen_and_never_calls_it_feasible():
    from app.optimiser.itinerary_compare import check_itinerary
    p, h, ds, days = _days_from_solver()
    crowded = [[a for d in days for a in d]] + [[] for _ in days[1:]]
    r = check_itinerary(p, h, ds, crowded)
    if r["feasible"]:
        pytest.skip("the whole trip fits on one day in this sample")
    assert any(s.get("problem") for s in r["stops"]) and r["cash"] is None and r["verification"] == "none"


def test_the_draft_check_enforces_the_minimum_active_days_and_the_api_route_is_cheap_tier():
    from app.optimiser.itinerary_compare import check_itinerary
    p, h, ds, days = _days_from_solver()
    one_day = [[a for d in days for a in d][:2], [], []][: p.days]
    q = p.model_copy(update={"min_active_days": min(2, p.days), "must_visit": []})
    r = check_itinerary(q, h, ds, one_day)
    if p.days >= 2:
        assert r["active_days"] == 1 and (r["feasible"] is False and "active" in " ".join(r["failed_checks"]).lower())
    body = {"city_id": "tokyo", "preferences": p.model_dump(), "hotel_id": h, "days": days}
    with TestClient(app) as c:
        j = c.post("/check-itinerary", json=body)
        assert j.status_code == 200 and j.json()["fingerprint"] and j.json()["feasible"] in (True, False)
        assert c.post("/check-itinerary", json={**body, "days": [["not_real"]]}).status_code == 422
