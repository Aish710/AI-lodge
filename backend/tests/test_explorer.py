"""Trip Trade-off Explorer: the interface only reruns the real endpoints. These tests pin the contract it relies on."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.optimiser.baselines import BaselineEntry
from app.schemas import LockedActivity
from test_baselines import prefs_for

FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _compare(c, city, prefs, hotels):
    return c.post("/compare-hotels", json={"city_id": city, "preferences": prefs.model_dump(), "hotel_ids": hotels, "include_sensitivity": False, "explain": False}).json()


def test_every_baseline_field_the_explorer_reads_exists_in_the_backend_model():
    src = (FRONT / "lib" / "tradeoff.js").read_text()
    read = set(re.findall(r"\be\.([a-z_]+)", src))
    assert read, "the explorer reads no baseline fields?"
    assert read <= set(BaselineEntry.model_fields), read - set(BaselineEntry.model_fields)


def test_the_explorer_value_of_time_options_are_real_reruns_and_ranking_can_change_with_the_value_of_time():
    prefs, hotels = prefs_for("tokyo")
    seen = {}
    with TestClient(app) as c:
        for k in (0.5, 1, 4, 20):
            vot = round(prefs.value_of_time_per_hour * k)
            r = _compare(c, "tokyo", prefs.model_copy(update={"value_of_time_per_hour": vot}), hotels)
            seen[k] = r
            joint = next(e for e in r["baselines"]["entries"] if e["key"] == "joint")
            assert joint["hotel_id"] == r["best_by_true_cost"]                    # the Explorer's headline is the optimiser's own ranking
            assert joint["known_spend_jpy"] == joint["accommodation_jpy"] + joint["admissions_jpy"] + joint["transport_jpy"]
    # Scores must rise with the value of time for the same hotel (time is priced higher); the explorer never fabricates this.
    j = {k: next(e for e in r["baselines"]["entries"] if e["key"] == "joint")["score_jpy"] for k, r in seen.items()}
    assert j[0.5] <= j[1] <= j[4] <= j[20]


def test_locks_and_user_limits_survive_a_compare_rerun():
    prefs, hotels = prefs_for("tokyo")
    with TestClient(app) as c:
        base = c.post("/optimise", json={"city_id": "tokyo", "preferences": prefs.model_dump(), "hotel_id": hotels[0], "explain": False}).json()
        first = next(s for d in base["result"]["days"] for s in d["stops"])
        locked = prefs.model_copy(update={"locked": [LockedActivity(attraction_id=first["attraction_id"], day=1, start_time=first["start"])], "max_activities_per_day": 3,
                                          "value_of_time_per_hour": prefs.value_of_time_per_hour * 4})
        r = _compare(c, "tokyo", locked, hotels)
        o = c.post("/optimise", json={"city_id": "tokyo", "preferences": locked.model_dump(), "hotel_id": r["best_by_true_cost"], "explain": False}).json()
    stops = [s for d in o["result"]["days"] for s in d["stops"]]
    kept = next(s for s in stops if s["attraction_id"] == first["attraction_id"])
    assert kept["start"] == first["start"]
    assert max(len(d["stops"]) for d in o["result"]["days"]) <= 3
    assert all(ch["status"] != "fail" for ch in o["feasibility_report"]["checks"])
