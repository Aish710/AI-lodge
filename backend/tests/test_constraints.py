"""Phase 2: a user-set maximum number of activities per day (independent of the pace presets) and a maximum ESTIMATED travel time per day, both hard constraints that the
independent validator re-checks; infeasible requests are explained, never silently relaxed."""
import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.eval import independent
from app.main import app
from app.optimiser.solver import solve
from app.schemas import Preferences
from app.validator.checks import run_checks

DS = load_all_city_datasets()["tokyo"]
H = "hotel_lantern_asakusa"


def day_minutes(res, ds=DS, hotel=H):
    """Estimated travel per day recomputed from the matrix (not from the numbers the schedule reports)."""
    out = {}
    for d in res.days:
        prev, t = hotel, 0
        for s in d.stops:
            t += ds.minutes[prev][s.attraction_id]
            prev = s.attraction_id
        out[d.day] = t + (ds.minutes[prev][hotel] if d.stops else 0)
    return out


def three_musts(**over):
    return Preferences(days=1, must_visit=["senso_ji", "meiji_jingu", "shibuya_sky"], pace="relaxed", start_weekday=2, **over)


def checks(res, prefs):
    return {c.id: c for c in run_checks(res, DS, prefs, H)}


# ---- maximum activities per day ----------------------------------------------------------------------------------
def test_the_relaxed_pace_alone_cannot_hold_three_must_visits_in_one_day_but_the_users_own_limit_can():
    r = solve(three_musts(), H, DS, with_alternatives=False)
    assert r.status == "infeasible" and [c.code for c in r.conflicts] == ["pace_cap"] and "'relaxed' pace allows 2/day" in r.conflicts[0].message
    r = solve(three_musts(max_activities_per_day=3), H, DS, with_alternatives=False)
    assert r.status == "feasible" and len(r.days[0].stops) == 3
    c = checks(r, three_musts(max_activities_per_day=3))["pace_cap"]
    assert c.status == "pass" and "your limit" in c.message and c.name == "Daily activity limit respected"


@pytest.mark.parametrize("limit", [1, 2, 3])
def test_every_day_respects_the_limit_whatever_the_pace_says(limit):
    p = Preferences(days=3, must_visit=["senso_ji"], pace="packed", start_weekday=2, max_activities_per_day=limit)
    r = solve(p, H, DS, with_alternatives=False)
    assert r.status == "feasible" and max(len(d.stops) for d in r.days) <= limit
    assert checks(r, p)["pace_cap"].status == "pass"


def test_a_limit_below_the_number_of_must_visits_is_reported_as_a_conflict_that_names_the_limit():
    p = Preferences(days=1, must_visit=["senso_ji", "meiji_jingu"], pace="packed", start_weekday=2, max_activities_per_day=1)
    r = solve(p, H, DS, with_alternatives=False)
    assert r.status == "infeasible" and r.conflicts[0].code == "pace_cap" and "your limit of 1 a day" in r.conflicts[0].message
    assert independent.confirm_conflict("pace_cap", r.conflicts[0].attraction_ids, DS, p, H, ["senso_ji", "meiji_jingu"]) is True


def test_the_independent_validator_rejects_a_schedule_that_breaks_the_users_limit():
    loose = three_musts(max_activities_per_day=3)
    r = solve(loose, H, DS, with_alternatives=False)
    strict = three_musts(max_activities_per_day=2)
    assert checks(r, strict)["pace_cap"].status == "fail" and "your limit of 2" in checks(r, strict)["pace_cap"].message


def test_without_a_user_limit_the_pace_preset_still_applies_and_nothing_changed():
    p = Preferences(days=2, must_visit=["senso_ji"], pace="relaxed", start_weekday=2)
    r = solve(p, H, DS, with_alternatives=False)
    assert max(len(d.stops) for d in r.days) <= 2 and checks(r, p)["pace_cap"].name == "Pace cap respected" and "daily_travel" not in checks(r, p)


# ---- maximum daily ESTIMATED travel time -------------------------------------------------------------------------
def test_the_travel_limit_is_enforced_from_the_same_table_the_validator_rereads():
    base = three_musts(max_activities_per_day=3)
    free = solve(base, H, DS, with_alternatives=False)
    need = day_minutes(free)[1]
    ok = solve(base.model_copy(update={"max_daily_travel_minutes": need}), H, DS, with_alternatives=False)
    assert ok.status == "feasible" and max(day_minutes(ok).values()) <= need
    p_ok = base.model_copy(update={"max_daily_travel_minutes": need})
    c = checks(ok, p_ok)["daily_travel"]
    assert c.status == "pass" and f"at most {need} min" in c.message
    tight = base.model_copy(update={"max_daily_travel_minutes": need - 1})
    bad = solve(tight, H, DS, with_alternatives=False)
    assert bad.status == "infeasible" and bad.conflicts[0].code == "no_feasible_schedule" and "daily activity and travel limits" in bad.conflicts[0].message


def test_a_limit_binds_optional_sights_without_breaking_must_visits():
    p = Preferences(days=2, must_visit=["senso_ji", "meiji_jingu"], pace="balanced", start_weekday=2)
    free = solve(p, H, DS, with_alternatives=False)
    cap = max(day_minutes(free).values()) - 1
    tight = solve(p.model_copy(update={"max_daily_travel_minutes": cap}), H, DS, with_alternatives=False)
    assert tight.status == "feasible" and max(day_minutes(tight).values()) <= cap
    placed = {s.attraction_id for d in tight.days for s in d.stops}
    assert {"senso_ji", "meiji_jingu"} <= placed


def test_a_must_visit_that_cannot_fit_the_limit_alone_gets_a_specific_conflict_the_independent_check_confirms():
    p = Preferences(days=2, must_visit=["senso_ji"], start_weekday=2, max_daily_travel_minutes=20)
    r = solve(p, H, DS, with_alternatives=False)
    round_trip = DS.minutes[H]["senso_ji"] + DS.minutes["senso_ji"][H]
    assert round_trip > 20 and r.status == "infeasible" and r.conflicts[0].code == "daily_travel_limit" and "daily limit is 20 min" in r.conflicts[0].message
    assert independent.confirm_conflict("daily_travel_limit", ["senso_ji"], DS, p, H, ["senso_ji"]) is True
    assert independent.confirm_conflict("daily_travel_limit", ["senso_ji"], DS, p.model_copy(update={"max_daily_travel_minutes": 600}), H, ["senso_ji"]) is False


def test_the_validator_rejects_a_schedule_that_breaks_the_travel_limit_and_adds_no_check_when_no_limit_is_set():
    p = Preferences(days=2, must_visit=["senso_ji", "meiji_jingu"], start_weekday=2)
    r = solve(p, H, DS, with_alternatives=False)
    worst = max(day_minutes(r).values())
    strict = p.model_copy(update={"max_daily_travel_minutes": worst - 1})
    assert checks(r, strict)["daily_travel"].status == "fail"
    assert "daily_travel" not in checks(r, p) and len(run_checks(r, DS, p, H)) == 15


def test_a_locked_hotel_context_is_unchanged_the_limits_are_per_plan_not_per_hotel():
    base = three_musts(max_activities_per_day=3, max_daily_travel_minutes=400)
    for hotel in ("hotel_kitsune_shinjuku", "hotel_harbour_odaiba"):
        r = solve(base, hotel, DS, with_alternatives=False)
        assert r.status in ("feasible", "infeasible")
        if r.status == "feasible":
            assert max(day_minutes(r, hotel=hotel).values()) <= 400


# ---- the API ----------------------------------------------------------------------------------------------------
def test_the_api_accepts_the_new_fields_validates_their_range_and_rejects_unknown_ones():
    body = {"city_id": "tokyo", "hotel_id": H, "preferences": three_musts(max_activities_per_day=3, max_daily_travel_minutes=300).model_dump(), "explain": False}
    with TestClient(app) as c:
        r = c.post("/optimise", json=body)
        assert r.status_code == 200 and r.json()["result"]["status"] == "feasible"
        assert all(ch["status"] != "fail" for ch in r.json()["feasibility_report"]["checks"])
        for field, bad in (("max_activities_per_day", 0), ("max_activities_per_day", 9), ("max_daily_travel_minutes", 5), ("max_daily_travel_minutes", 5000)):
            b = {**body, "preferences": {**body["preferences"], field: bad}}
            assert c.post("/optimise", json=b).status_code == 422, (field, bad)
        b = {**body, "preferences": {**body["preferences"], "max_walking_kilometres": 2}}
        assert c.post("/optimise", json=b).status_code == 422                 # no walking-distance constraint exists: unknown fields are refused


def test_city_payload_exposes_default_value_of_time_for_the_presets():
    # The frontend value-of-time presets are multiples of this; it must match the city data the objective uses.
    for cid, expected in {"tokyo": 1000, "seoul": 15000, "kuala_lumpur": 45}.items():
        with TestClient(app) as c:
            body = c.get("/data/cities").json()
        row = next(c for c in (body["cities"] if isinstance(body, dict) else body) if c["id"] == cid)
        assert row["default_value_of_time_per_hour"] == expected
