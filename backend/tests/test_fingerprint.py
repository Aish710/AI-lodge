"""Plan fingerprints: stable, input-sensitive, additive on the API."""
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.fingerprint import dataset_version, plan_fingerprint
from app.main import app
from test_baselines import prefs_for

ALL = load_all_city_datasets()


def test_same_inputs_same_fingerprint_and_every_input_matters():
    p, hotels = prefs_for("tokyo")
    ds = ALL["tokyo"]
    a = plan_fingerprint(p, hotels[0], ds)
    assert a == plan_fingerprint(p.model_copy(), hotels[0], ds)
    assert a != plan_fingerprint(p, hotels[1], ds)
    assert a != plan_fingerprint(p.model_copy(update={"value_of_time_per_hour": p.value_of_time_per_hour + 1}), hotels[0], ds)
    assert a != plan_fingerprint(p.model_copy(update={"max_activities_per_day": 2}), hotels[0], ds)
    assert plan_fingerprint(p, hotels, ds) == plan_fingerprint(p, list(reversed(hotels)), ds)      # a hotel SET is order-free


def test_dataset_versions_differ_per_city_and_are_stable():
    v = {c: dataset_version(c) for c in ALL}
    assert len(set(v.values())) == len(v) and all(len(x) == 12 for x in v.values())
    assert v == {c: dataset_version(c) for c in ALL}


def test_the_api_returns_fingerprints_additively_for_optimise_compare_and_replan():
    p, hotels = prefs_for("tokyo")
    with TestClient(app) as c:
        o = c.post("/optimise", json={"city_id": "tokyo", "preferences": p.model_dump(), "hotel_id": hotels[0], "explain": False}).json()
        k = c.post("/compare-hotels", json={"city_id": "tokyo", "preferences": p.model_dump(), "hotel_ids": hotels, "include_sensitivity": False, "explain": False}).json()
        o2 = c.post("/optimise", json={"city_id": "tokyo", "preferences": p.model_dump(), "hotel_id": hotels[0], "explain": False}).json()
        r = c.post("/replan", json={"city_id": "tokyo", "preferences": p.model_dump(), "current_result": o["result"], "operations": [], "explain": False}).json()
    assert o["fingerprint"] == o2["fingerprint"] and o["dataset_version"] == dataset_version("tokyo")
    assert k["fingerprint"] != o["fingerprint"] and "fingerprint" in r


def test_version_lists_the_features_the_page_needs_so_an_older_server_can_be_detected():
    with TestClient(app) as c:
        j = c.get("/version").json()
    assert j["api"] == "fitinerary" and {"check-itinerary", "evaluate-itinerary", "explore", "copilot", "apply-repair", "plan-verification"} <= set(j["features"])
    # every route a feature names really exists on this server
    import app.main as m
    paths = {r.path for r in m.router.routes}
    for f in ("check-itinerary", "evaluate-itinerary", "explore", "copilot", "parse-repair", "apply-repair", "parse-profile"):
        assert "/" + f in paths, f
