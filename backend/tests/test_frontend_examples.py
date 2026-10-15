"""The demo helpers in the frontend are pre-tested here against the REAL routes.
frontend/src/lib/examples.json is the single source for both the UI and this test, and tests/e2e checks the same in a browser."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

EXAMPLES = json.loads((Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "examples.json").read_text())


def prefs_from(ex: dict) -> dict:
    """Mirror of frontend/src/lib/prefs.js buildPreferences (JPY budgets only in the examples)."""
    f, w = ex["form"], ex["wishlist"]
    budget = None if f["budgetAmount"] in ("", None) else int(f["budgetAmount"])
    return {"days": f["days"], "budget": budget, "strict_budget": bool(f["strictBudget"] and budget is not None), "pace": f["pace"], "interests": [],
            "must_visit": [k for k, v in w.items() if v == "must"], "skip": [k for k, v in w.items() if v == "skip"], "day_start": f["dayStart"],
            "day_end": f["dayEnd"], "value_of_time_per_hour": f["valueOfTime"], "max_walking_minutes_per_day": 90, "start_weekday": f["startWeekday"],
            "allow_unknown_hours": f["allowUnknownHours"], "nights": f["nights"] if f["nightsOverride"] else None, "locked": []}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _city_examples():
    return [(city_id, pack[kind]) for city_id, pack in EXAMPLES.items() if city_id != "note" for kind in ("valid", "impossible")]


def test_valid_examples_are_feasible_validated_and_pin_the_hotel_difference_flag(client):
    for city_id, pack in EXAMPLES.items():
        if city_id == "note":
            continue
        ex = pack["valid"]
        assert ex["city_id"] == city_id
        p = prefs_from(ex)
        r = client.post("/optimise", json={"city_id": city_id, "preferences": p, "hotel_id": ex["hotel_id"]}).json()
        assert r["result"]["status"] == ex["expect"]["status"] and r["feasibility_report"]["overall"] != "fail"
        assert set(ex["wishlist"]) & {s["attraction_id"] for d in r["result"]["days"] for s in d["stops"]}
        c = client.post("/compare-hotels", json={"city_id": city_id, "preferences": p, "hotel_ids": ex["hotel_ids"], "include_sensitivity": True}).json()
        assert c["best_by_true_cost"]
        assert c["rate_winner_differs_from_true_winner"] is ex["expect"]["rate_winner_differs_from_true_winner"]


def test_impossible_examples_are_normal_infeasible_results_with_a_usable_alternative(client):
    for city_id, pack in EXAMPLES.items():
        if city_id == "note":
            continue
        ex = pack["impossible"]
        assert ex["city_id"] == city_id
        resp = client.post("/optimise", json={"city_id": city_id, "preferences": prefs_from(ex), "hotel_id": ex["hotel_id"]})
        assert resp.status_code == 200
        r = resp.json()["result"]
        assert r["status"] == ex["expect"]["status"] and any(c["code"] == ex["expect"]["conflict_code"] for c in r["conflicts"])
        assert any(a["kind"] == ex["expect"]["alternative"] for a in r["alternatives"])
        fixed = dict(prefs_from(ex), allow_unknown_hours=True)
        again = client.post("/optimise", json={"city_id": city_id, "preferences": fixed, "hotel_id": ex["hotel_id"]}).json()
        assert again["result"]["status"] == "feasible" and again["feasibility_report"]["overall"] != "fail"


def test_all_examples_belong_to_their_current_city():
    for city_id, ex in _city_examples():
        assert ex["city_id"] == city_id


def test_legacy_tokyo_example_is_feasible_validated_and_shows_a_real_hotel_difference(client):
    ex = EXAMPLES["tokyo"]["valid"]
    p = prefs_from(ex)
    r = client.post("/optimise", json={"city_id": "tokyo", "preferences": p, "hotel_id": ex["hotel_id"]}).json()
    assert r["result"]["status"] == ex["expect"]["status"] and r["feasibility_report"]["overall"] != "fail"
    assert {"senso_ji", "meiji_jingu"} <= {s["attraction_id"] for d in r["result"]["days"] for s in d["stops"]}
    c = client.post("/compare-hotels", json={"city_id": "tokyo", "preferences": p, "hotel_ids": ex["hotel_ids"], "include_sensitivity": True}).json()
    assert c["best_by_true_cost"] and c["rate_winner_differs_from_true_winner"] is ex["expect"]["rate_winner_differs_from_true_winner"]


def test_impossible_example_is_a_normal_infeasible_result_with_a_usable_alternative(client):
    ex = EXAMPLES["tokyo"]["impossible"]
    resp = client.post("/optimise", json={"city_id": "tokyo", "preferences": prefs_from(ex), "hotel_id": ex["hotel_id"]})
    assert resp.status_code == 200
    r = resp.json()["result"]
    assert r["status"] == ex["expect"]["status"] and any(c["code"] == ex["expect"]["conflict_code"] for c in r["conflicts"])
    assert any(a["kind"] == ex["expect"]["alternative"] for a in r["alternatives"])
    # applying the offered alternative really does make it feasible (this is what the UI button does)
    fixed = dict(prefs_from(ex), allow_unknown_hours=True)
    again = client.post("/optimise", json={"city_id": "tokyo", "preferences": fixed, "hotel_id": ex["hotel_id"]}).json()
    assert again["result"]["status"] == "feasible" and again["feasibility_report"]["overall"] != "fail"
