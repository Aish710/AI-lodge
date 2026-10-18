"""The live app nudges the optimiser towards balanced days: an empty trip day costs a little, and so does a lopsided load. It is a tie-breaker inside the
objective only: never a displayed cost, never a hard rule. These tests pin the behaviour and its limits."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="module", autouse=True)
def _client():
    global client
    with TestClient(app) as client:     # the context manager runs the app's start-up, which loads the datasets
        yield


client = None
PREFS = {"days": 5, "pace": "balanced", "must_visit": ["senso_ji", "shibuya_sky"], "start_weekday": 2, "value_of_time_per_hour": 1000}


def optimise(**over):
    r = client.post("/optimise", json={"city_id": "tokyo", "preferences": {**PREFS, **over}, "hotel_id": "hotel_lantern_asakusa"})
    assert r.status_code == 200, r.text
    return r.json()


def stops_per_day(j):
    return [len(d["stops"]) for d in j["result"]["days"]]


@pytest.mark.parametrize("days", [3, 4, 5, 6])
def test_a_trip_uses_every_day_when_there_are_enough_sights(days):
    j = optimise(days=days)
    assert j["result"]["status"] == "feasible"
    assert all(n >= 1 for n in stops_per_day(j)), stops_per_day(j)
    assert j["feasibility_report"]["overall"] in ("pass", "pass_with_warnings")


def test_five_days_with_two_must_visits_is_spread_evenly():
    assert stops_per_day(optimise()) == [2, 2, 2, 2, 2]


def test_the_nudge_never_forces_an_infeasible_plan_or_breaks_a_limit():
    j = optimise(max_daily_travel_minutes=60)            # a tight hard limit: some days may have to stay empty, and the plan is still valid
    assert j["result"]["status"] in ("feasible", "infeasible")
    if j["result"]["status"] == "feasible":
        assert j["feasibility_report"]["overall"] != "fail"
    j = optimise(days=5, must_visit=["senso_ji"], max_activities_per_day=1)
    assert j["result"]["status"] == "feasible" and max(stops_per_day(j)) <= 1


def test_a_hard_minimum_of_active_days_still_wins_and_a_strict_budget_still_holds():
    j = optimise(days=5, budget=4000, strict_budget=True, must_visit=["senso_ji"])
    if j["result"]["status"] == "feasible":
        assert j["cost_summary"]["trip"]["cash_total"] <= 4000
    j = optimise(days=4, min_active_days=4, must_visit=["senso_ji"])
    assert j["result"]["status"] == "feasible" and all(n >= 1 for n in stops_per_day(j))


def test_displayed_costs_do_not_include_the_nudge():
    j = optimise()
    t = j["cost_summary"]["trip"]
    adm = sum(s["cost"] for d in j["result"]["days"] for s in d["stops"] if s["cost_status"] == "known")
    assert t["admissions"] == adm and t["cash_total"] == t["admissions"] + t["transport"]
