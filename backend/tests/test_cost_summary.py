"""Server-side cost totals: day totals sum to the trip totals (every city), they equal the totals the solver/validator already report,
unknown prices are listed and never counted as free, and the block is additive (the existing result and the replan round trip are unchanged)."""
import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.main import app
from app.schemas import Preferences

ALL = load_all_city_datasets()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _prefs(ds, days=3, pace="balanced", **kw):
    return Preferences(days=days, pace=pace, day_start=ds.city.default_day_start, day_end=ds.city.default_day_end,
                       value_of_time_per_hour=ds.city.default_value_of_time_per_hour, **kw).model_dump()


@pytest.mark.parametrize("city", list(ALL))
def test_day_totals_sum_to_trip_totals_and_match_the_validated_totals(client, city):
    ds = ALL[city]
    for hotel in list(ds.hotels)[:2]:
        r = client.post("/optimise", json={"city_id": city, "preferences": _prefs(ds), "hotel_id": hotel}).json()
        assert r["result"]["status"] == "feasible"
        cs, t = r["cost_summary"], r["result"]["totals"]
        assert cs["currency"] == ds.city.currency_code
        assert sum(d["admissions"] for d in cs["days"]) == cs["trip"]["admissions"] == t["admissions_jpy"]
        assert sum(d["transport"] for d in cs["days"]) == cs["trip"]["transport"] == t["transport_jpy"]
        assert sum(d["day_total"] for d in cs["days"]) == cs["trip"]["cash_total"] == t["total_jpy"]
        assert all(d["day_total"] == d["admissions"] + d["transport"] for d in cs["days"])
        assert sum(d["travel_minutes"] for d in cs["days"]) == cs["trip"]["travel_minutes"] == t["travel_minutes"]
        assert cs["trip"]["rooms"] == ds.hotels[hotel].nightly_rate * r["nights_used"]
        assert cs["trip"]["cash_total_with_rooms"] == cs["trip"]["cash_total"] + cs["trip"]["rooms"]
        assert cs["trip"]["hotel_area"] == ds.hotels[hotel].area
        assert [d["day"] for d in cs["days"]] == [d["day"] for d in r["result"]["days"]]
        assert [d["stops"] for d in cs["days"]] == [len(d["stops"]) for d in r["result"]["days"]]


@pytest.mark.parametrize("city", list(ALL))
def test_unknown_prices_are_listed_and_not_counted_as_zero(client, city):
    ds = ALL[city]
    r = client.post("/optimise", json={"city_id": city, "preferences": _prefs(ds, days=4, pace="packed"), "hotel_id": next(iter(ds.hotels))}).json()
    cs = r["cost_summary"]
    unknown_in_plan = [s["attraction_id"] for d in r["result"]["days"] for s in d["stops"] if s["cost_status"] == "unknown"]
    assert cs["trip"]["unknown_price_ids"] == unknown_in_plan == r["result"]["totals"]["unknown_cost_items"]
    assert cs["trip"]["unknown_price_count"] == len(unknown_in_plan)
    for d in cs["days"]:
        for a in d["unknown_price_ids"]:
            assert ds.attractions[a].admission_cost is None
    known_sum = sum(ds.attractions[s["attraction_id"]].admission_cost for d in r["result"]["days"] for s in d["stops"] if s["cost_status"] == "known")
    assert cs["trip"]["admissions"] == known_sum


def test_infeasible_plans_have_no_cost_summary(client):
    ds = ALL["tokyo"]
    p = _prefs(ds, days=1, must_visit=["senso_ji", "tokyo_skytree", "meiji_jingu", "teamlab_planets", "tsukiji_outer_market"])
    r = client.post("/optimise", json={"city_id": "tokyo", "preferences": p, "hotel_id": "hotel_lantern_asakusa"}).json()
    assert r["result"]["status"] == "infeasible" and r["cost_summary"] is None


def test_the_result_block_is_unchanged_so_the_replan_round_trip_still_works(client):
    ds = ALL["tokyo"]
    r = client.post("/optimise", json={"city_id": "tokyo", "preferences": _prefs(ds), "hotel_id": "hotel_lantern_asakusa"}).json()
    assert "cost_summary" not in r["result"] and set(r["result"]["totals"]) == {"travel_minutes", "admissions_jpy", "transport_jpy", "total_jpy", "unknown_cost_items", "attractions_scheduled"}
    stops = [s["attraction_id"] for d in r["result"]["days"] for s in d["stops"]]
    rp = client.post("/replan", json={"city_id": "tokyo", "preferences": _prefs(ds), "current_result": r["result"],
                                      "operations": [{"op": "remove", "attraction_id": stops[-1]}]}).json()
    assert rp["status"] == "applied"
    cs, t = rp["cost_summary"], rp["schedule"]["totals"]
    assert cs["trip"]["cash_total"] == t["total_jpy"] == sum(d["day_total"] for d in cs["days"])
