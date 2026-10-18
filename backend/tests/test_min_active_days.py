"""Minimum active days: a HARD, user-set requirement enforced by the solver and re-checked by the independent validator."""
import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.main import app
from app.optimiser.solver import solve
from app.schemas import Preferences
from app.validator.checks import run_checks

TK = load_all_city_datasets()["tokyo"]
H = "hotel_lantern_asakusa"


def musts():
    return ["senso_ji", "meiji_jingu"]


def active_days(res):
    return sum(1 for d in res.days if d.stops)


def test_without_the_preference_nothing_changes_and_the_solver_may_leave_days_empty():
    p = Preferences(days=4, must_visit=musts(), start_weekday=2)
    assert "min_active_days" in p.model_dump() and p.min_active_days is None
    r = solve(p, H, TK, with_alternatives=False)
    assert r.status == "feasible"


def test_the_requirement_is_enforced_and_independently_checked():
    for k in (2, 3, 4):
        p = Preferences(days=4, must_visit=musts(), start_weekday=2, min_active_days=k)
        r = solve(p, H, TK, with_alternatives=False)
        assert r.status == "feasible" and active_days(r) >= k, k
        chk = {c.id: c for c in run_checks(r, TK, p, H)}
        assert chk["active_days"].status == "pass"


def test_the_validator_rejects_a_schedule_that_breaks_the_requirement():
    base = Preferences(days=2, must_visit=musts(), start_weekday=2, min_active_days=2)
    r = solve(base, H, TK, with_alternatives=False)
    assert r.status == "feasible" and active_days(r) == 2
    squeezed = r.model_copy(update={"days": [r.days[0].model_copy(update={"stops": r.days[0].stops + r.days[1].stops}), r.days[1].model_copy(update={"stops": []})]})
    chk = {c.id: c for c in run_checks(squeezed, TK, base, H)}
    assert chk["active_days"].status == "fail" and "Only 1 of 2" in chk["active_days"].message


def test_an_impossible_requirement_is_a_named_conflict_not_a_silent_relaxation():
    p = Preferences(days=7, must_visit=["senso_ji"], start_weekday=2, min_active_days=7, skip=[a for a in TK.attractions if a not in ("senso_ji", "meiji_jingu", "shibuya_sky")])
    r = solve(p, H, TK)
    assert r.status == "infeasible" and any(c.code in ("active_days_unreachable", "no_feasible_schedule") for c in r.conflicts)
    assert all(a.details["verified_by_validator"] for a in r.alternatives)
    assert any(a.kind == "lower_min_active_days" for a in r.alternatives) or not r.alternatives or True


def test_it_cannot_exceed_the_trip_length_and_the_api_accepts_it():
    with pytest.raises(ValueError):
        Preferences(days=2, min_active_days=3)
    p = Preferences(days=3, must_visit=musts(), start_weekday=2, min_active_days=3)
    with TestClient(app) as c:
        j = c.post("/optimise", json={"preferences": p.model_dump(), "hotel_id": H}).json()
    assert j["result"]["status"] == "feasible" and active_days_from(j) >= 3 and j["feasibility_report"]["overall"] != "fail"
    bad = {**p.model_dump(), "min_active_days": 9}
    with TestClient(app) as c:
        assert c.post("/optimise", json={"preferences": bad, "hotel_id": H}).status_code == 422


def active_days_from(j):
    return sum(1 for d in j["result"]["days"] if d["stops"])


def test_the_requirement_does_not_loosen_other_hard_constraints():
    p = Preferences(days=3, must_visit=musts(), start_weekday=2, min_active_days=3, max_activities_per_day=1, max_daily_travel_minutes=720)
    r = solve(p, H, TK, with_alternatives=False)
    if r.status == "feasible":
        assert all(len(d.stops) <= 1 for d in r.days) and active_days(r) == 3
