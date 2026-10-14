"""One trip covers one city. Every response echoes its city_id, and every hotel/attraction id a request carries must belong to the
request's city: an id from another city is rejected with a 422 that names the id and its real city (never a 500, never a silent
solve). Parametrised over every route and every ordered pair of cities."""
import itertools

import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.hardening.config import HConfig
from app.main import create_app

DATASETS = load_all_city_datasets()
CITIES = sorted(DATASETS)
PAIRS = list(itertools.permutations(CITIES, 2))


@pytest.fixture(scope="module")
def client():
    app = create_app(HConfig(rate_expensive_per_min=10_000, rate_standard_per_min=10_000, rate_cheap_per_min=10_000))
    with TestClient(app) as c:
        yield c


def _prefs(city, **extra):
    c = DATASETS[city].city
    return {"days": 2, "day_start": c.default_day_start, "day_end": c.default_day_end,
            "value_of_time_per_hour": c.default_value_of_time_per_hour, **extra}


def _hotel(city, i=0):
    return list(DATASETS[city].hotels)[i]


def _attraction(city, i=0):
    return list(DATASETS[city].attractions)[i]


def _plan(client, city):
    return client.post("/optimise", json={"city_id": city, "preferences": _prefs(city), "hotel_id": _hotel(city)}).json()


def _check_wrong_city(resp, item_id, owner_city):
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "wrong_city"
    assert item_id in err["message"]
    assert DATASETS[owner_city].city.display_name in err["message"]
    assert any(d["id"] == item_id and d["belongs_to_city"] == owner_city for d in err["details"])
    assert err["request_id"]


@pytest.mark.parametrize("city", CITIES)
def test_every_response_echoes_its_city_id(client, city):
    assert client.get("/data/summary", params={"city_id": city}).json()["city_id"] == city
    assert client.get("/data/places", params={"city_id": city}).json()["city_id"] == city
    plan = _plan(client, city)
    assert plan["city_id"] == city
    h = list(DATASETS[city].hotels)[:2]
    cmp_ = client.post("/compare-hotels", json={"city_id": city, "preferences": _prefs(city), "hotel_ids": h}).json()
    assert cmp_["city_id"] == city
    rp = client.post("/replan", json={"city_id": city, "preferences": _prefs(city), "current_result": plan["result"], "operations": []}).json()
    assert rp["city_id"] == city
    pr = client.post("/parse", json={"city_id": city, "text": "two relaxed days"}).json()
    assert pr["city_id"] == city
    pp = client.post("/parse-replan", json={"city_id": city, "text": "make it cheaper", "preferences": _prefs(city), "current_result": plan["result"]}).json()
    assert pp["city_id"] == city


@pytest.mark.parametrize("a,b", PAIRS)
def test_foreign_hotel_is_rejected_on_optimise_and_compare(client, a, b):
    foreign = _hotel(b)
    _check_wrong_city(client.post("/optimise", json={"city_id": a, "preferences": _prefs(a), "hotel_id": foreign}), foreign, b)
    own = _hotel(a)
    _check_wrong_city(client.post("/compare-hotels", json={"city_id": a, "preferences": _prefs(a), "hotel_ids": [own, foreign]}), foreign, b)


@pytest.mark.parametrize("a,b", PAIRS)
def test_foreign_locked_stop_is_rejected_on_every_solving_route(client, a, b):
    foreign = _attraction(b)
    prefs = _prefs(a, locked=[{"attraction_id": foreign, "day": 1, "start_time": "10:00"}])
    _check_wrong_city(client.post("/optimise", json={"city_id": a, "preferences": prefs, "hotel_id": _hotel(a)}), foreign, b)
    _check_wrong_city(client.post("/compare-hotels", json={"city_id": a, "preferences": prefs, "hotel_ids": list(DATASETS[a].hotels)[:2]}), foreign, b)
    plan = _plan(client, a)["result"]
    _check_wrong_city(client.post("/replan", json={"city_id": a, "preferences": prefs, "current_result": plan, "operations": []}), foreign, b)
    _check_wrong_city(client.post("/parse-replan", json={"city_id": a, "text": "x", "preferences": prefs, "current_result": plan}), foreign, b)


@pytest.mark.parametrize("a,b", PAIRS)
def test_foreign_replan_operation_targets_are_rejected(client, a, b):
    plan = _plan(client, a)["result"]
    for op in ({"op": "remove", "attraction_id": _attraction(b)},
               {"op": "unlock", "attraction_id": _attraction(b)},
               {"op": "lock", "attraction_id": _attraction(b), "day": 1, "start_time": "10:00"},
               {"op": "move", "attraction_id": _attraction(b), "day": 1, "start_time": "10:00"}):
        _check_wrong_city(client.post("/replan", json={"city_id": a, "preferences": _prefs(a), "current_result": plan, "operations": [op]}),
                          op["attraction_id"], b)
    sw = {"op": "switch_hotel", "hotel_id": _hotel(b)}
    _check_wrong_city(client.post("/replan", json={"city_id": a, "preferences": _prefs(a), "current_result": plan, "operations": [sw]}), sw["hotel_id"], b)


@pytest.mark.parametrize("a,b", PAIRS)
def test_a_schedule_from_another_city_is_rejected_and_names_the_city(client, a, b):
    foreign_plan = _plan(client, b)["result"]
    for route, body in (("/replan", {"operations": []}), ("/parse-replan", {"text": "x"})):
        r = client.post(route, json={"city_id": a, "preferences": _prefs(a), "current_result": foreign_plan, **body})
        assert r.status_code == 422
        err = r.json()["error"]
        assert err["code"] == "invalid_schedule"
        assert DATASETS[b].city.display_name in str(err["details"])


@pytest.mark.parametrize("a,b", PAIRS)
def test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences(client, a, b):
    foreign = _attraction(b)
    plan = _plan(client, a)["result"]
    for field in ("must_visit", "skip"):
        prefs = _prefs(a, **{field: [foreign]})
        bodies = [("/optimise", {"hotel_id": _hotel(a)}), ("/compare-hotels", {"hotel_ids": list(DATASETS[a].hotels)[:2]}),
                  ("/replan", {"current_result": plan, "operations": []}), ("/parse-replan", {"text": "x", "current_result": plan})]
        for route, extra in bodies:
            _check_wrong_city(client.post(route, json={"city_id": a, "preferences": prefs, **extra}), foreign, b)
