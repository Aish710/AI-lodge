"""Budget/time alternatives: dominance, de-duplication, determinism, honest labelling, consistent scoring."""
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.main import app
from app.optimiser.alternatives import dominates, explore, pareto
from test_baselines import prefs_for

ALL = load_all_city_datasets()


def c(money, minutes, coverage):
    return {"money": money, "minutes": minutes, "coverage": coverage}


def test_dominance_definition():
    assert dominates(c(1, 1, 3), c(2, 2, 2)) and dominates(c(1, 2, 2), c(2, 2, 2))
    assert not dominates(c(2, 2, 2), c(2, 2, 2))                      # equal on everything: neither dominates, so ties are both kept
    assert not dominates(c(1, 3, 2), c(2, 2, 2))                      # cheaper but slower: a genuine trade-off
    assert len(pareto([c(1, 3, 2), c(2, 2, 2), c(3, 3, 1)])) == 2


def test_explore_returns_distinct_nondominated_real_plans_and_is_deterministic():
    p, hotels = prefs_for("tokyo")
    a = explore(p, hotels, ALL["tokyo"], max_seconds=30)
    b = explore(p, hotels, ALL["tokyo"], max_seconds=30)
    assert [x["fingerprint"] for x in a["alternatives"]] == [x["fingerprint"] for x in b["alternatives"]]
    alts = a["alternatives"]
    assert alts and len({(x["hotel_id"], x["fingerprint"]) for x in alts}) == len(alts)         # no duplicate cards
    for x in alts:
        assert not any(dominates(y, x) for y in alts if y is not x)
        assert x["money"] == x["rooms"] + x["admissions"] + x["transport"]                         # money is never the score
        assert x["roles"]
    assert "not a complete Pareto frontier" in a["method"]


def test_zero_value_of_time_and_extreme_values_stay_consistent():
    p, hotels = prefs_for("seoul")
    for vot in (0, 10 * p.value_of_time_per_hour):
        r = explore(p.model_copy(update={"value_of_time_per_hour": vot}), hotels, ALL["seoul"], max_seconds=30)
        for x in r["alternatives"]:
            assert x["money"] >= 0 and x["minutes"] >= 0


def test_no_alternatives_is_reported_not_invented_for_an_infeasible_request():
    p, hotels = prefs_for("tokyo")
    r = explore(p.model_copy(update={"day_start": "09:00", "day_end": "09:20"}), hotels, ALL["tokyo"], max_seconds=10)
    assert r["alternatives"] == [] and r["feasible_candidates"] == 0


def test_the_api_route():
    p, hotels = prefs_for("tokyo")
    with TestClient(app) as cl:
        r = cl.post("/explore", json={"city_id": "tokyo", "preferences": p.model_dump(), "hotel_ids": hotels})
        assert r.status_code == 200 and r.json()["fingerprint"] and r.json()["alternatives"]
        assert cl.post("/explore", json={"city_id": "tokyo", "preferences": p.model_dump(), "hotel_ids": ["nope"]}).status_code in (422, 400)
