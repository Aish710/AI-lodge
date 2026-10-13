"""Phase 4: replanning. No LLM involved.

BASE case: Asakusa hotel, 2 days starting Wednesday, must-visits Senso-ji + Shibuya Sky, teamLab skipped,
initial plan solved with the true-cost objective (VoT 1000, penalty 3000) so a no-op replan has nothing to improve.
Hand-computed hotel switch (ASA -> Odaiba, 2 days so nights = days - 1 = 1):
  rooms before = 10,500 x 1 = 10,500;  rooms after = 8,500 x 1 = 8,500;  room-cost delta = -2,000 JPY.
"""
import ast
import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.data.loader import load_dataset
from app.main import ReplanRequest, app
from app.optimiser.replan import (
    ChangeBudgetOp, LockOp, MoveOp, RemoveOp, ReplanError, SwitchHotelOp, UnlockOp, replan,
)
from app.optimiser.solver import ObjectiveSpec, solve
from app.schemas import LockedActivity, Preferences
from app.validator.feasibility_report import build_report

DS = load_dataset()
SHJ, ASA, ODA = "hotel_kitsune_shinjuku", "hotel_lantern_asakusa", "hotel_harbour_odaiba"
SPEC = ObjectiveSpec("true_cost", 1000, config.MISSED_PREFERENCE_PENALTY_JPY)
SEEN: list[tuple] = []  # (prefs, hotel, result) for the validator property test at the end


def base():
    p = Preferences(days=2, must_visit=["senso_ji", "shibuya_sky"], start_weekday=2, skip=["teamlab_planets"])
    return p, solve(p, ASA, DS, with_alternatives=False, objective=SPEC)


def run(p, cur, ops, **kw):
    r = replan(p, cur, ops, DS, **kw)
    if r.status == "applied":
        SEEN.append((r.new_preferences, r.hotel_id, r.schedule))
    return r


def stops(res):
    return {s.attraction_id: (d.day, s.start) for d in res.days for s in d.stops}


def optional_in(res, p):
    return [a for a in stops(res) if a not in p.must_visit]


# ---- scenario 5: locks ---------------------------------------------------------
def test_s05_locked_activity_keeps_exact_day_and_time():
    p, cur = base()
    r = run(p, cur, [LockOp(op="lock", attraction_id="senso_ji", day=1, start_time="14:00")])
    assert r.status == "applied" and stops(r.schedule)["senso_ji"] == (1, "14:00")
    assert any(c.id == "locked" and c.status == "pass" for c in r.feasibility_report.checks)
    # the lock is carried in the returned preferences, so a stateless client keeps it next time
    r2 = run(r.new_preferences, r.schedule, [])
    assert stops(r2.schedule)["senso_ji"] == (1, "14:00") and r2.diff.disruption_count == 0


def test_move_is_a_lock_at_the_new_slot_and_is_not_counted_as_disruption():
    p, cur = base()
    r = run(p, cur, [MoveOp(op="move", attraction_id="shibuya_sky", day=2, start_time="10:00")])
    assert stops(r.schedule)["shibuya_sky"] == (2, "10:00")
    mv = [m for m in r.diff.moved if m.attraction_id == "shibuya_sky"]
    assert not mv or mv[0].reason == "user"


def test_unlock_releases_a_lock():
    p, cur = base()
    r = run(p, cur, [LockOp(op="lock", attraction_id="senso_ji", day=1, start_time="14:00")])
    r2 = run(r.new_preferences, r.schedule, [UnlockOp(op="unlock", attraction_id="senso_ji")])
    assert r2.new_preferences.locked == []
    with pytest.raises(ReplanError, match="not locked"):
        replan(p, cur, [UnlockOp(op="unlock", attraction_id="senso_ji")], DS)


# ---- no-op and disruption --------------------------------------------------------
def test_replan_with_no_changes_returns_identical_schedule_and_zero_disruption():
    p, cur = base()
    r = run(p, cur, [])
    assert r.status == "applied" and r.schedule.days == cur.days
    assert r.diff.disruption_count == 0 and not r.diff.moved and not r.diff.removed and not r.diff.added
    assert r.diff.true_cost_jpy.delta == 0


def test_removing_one_nice_to_have_moves_few_other_activities():
    p, cur = base()
    victim = optional_in(cur, p)[0]
    r = run(p, cur, [RemoveOp(op="remove", attraction_id=victim)])
    remaining = len(stops(cur)) - 1
    assert r.diff.disruption_count <= 1  # stated bound: at most 1 of the remaining activities is unnecessarily moved
    assert any(x.attraction_id == victim and x.reason == "removed_by_user" for x in r.diff.removed)
    assert victim not in stops(r.schedule) and remaining >= 4


def test_disruption_aware_replan_moves_fewer_activities_than_a_naive_resolve():
    p, cur = base()
    ops = [RemoveOp(op="remove", attraction_id="shinjuku_gyoen")]
    assert "shinjuku_gyoen" in stops(cur)
    aware, naive = replan(p, cur, ops, DS), replan(p, cur, ops, DS, strategy="naive")
    assert aware.diff.disruption_count < naive.diff.disruption_count
    # honesty: the stable plan cannot be cheaper than the unconstrained optimum
    assert aware.diff.true_cost_jpy.after >= naive.diff.true_cost_jpy.after


# ---- must-visit removal ---------------------------------------------------------------
def test_removing_a_must_visit_without_confirmation_is_rejected():
    p, cur = base()
    with pytest.raises(ReplanError) as e:
        replan(p, cur, [RemoveOp(op="remove", attraction_id="senso_ji")], DS)
    assert e.value.code == "must_visit_removal_not_confirmed"
    assert "Senso-ji" in e.value.message and "confirm_remove_must_visit" in e.value.message


def test_removing_a_must_visit_with_confirmation_is_recorded_everywhere():
    p, cur = base()
    r = run(p, cur, [RemoveOp(op="remove", attraction_id="senso_ji")], confirm_remove_must_visit=True)
    assert r.status == "applied" and "senso_ji" not in stops(r.schedule)
    assert "senso_ji" not in r.new_preferences.must_visit
    rem = next(x for x in r.diff.removed if x.attraction_id == "senso_ji")
    assert rem.was_must_visit and rem.reason == "removed_by_user"
    assert any("Must-visit removed by user: Senso-ji" in w for w in r.diff.warnings)
    chk = next(c for c in r.feasibility_report.checks if c.id == "must_visit_removed_by_user")
    assert chk.status == "warning" and r.feasibility_report.overall == "pass_with_warnings"
    assert "must-visit removed by user" in chk.message.lower()


# ---- hotel switch (scenario 6) ----------------------------------------------------------
def test_s06_hotel_switch_recomputes_rooms_and_itinerary():
    p, cur = base()
    r = run(p, cur, [SwitchHotelOp(op="switch_hotel", hotel_id=ODA)])
    assert r.status == "applied" and r.hotel_id == ODA and r.previous_hotel_id == ASA
    assert r.nights_used == 1 and r.nights_source == "default (days - 1)"
    d = r.diff.rooms_jpy
    assert (d.before, d.after, d.delta) == (10500, 8500, -2000)  # hand-computed in the module docstring
    assert r.schedule.hotel_id == ODA
    assert r.diff.travel_minutes.before != r.diff.travel_minutes.after  # itinerary really recalculated
    first = r.schedule.days[0].stops[0]
    assert first.travel_minutes_from_previous == DS.minutes[ODA][first.attraction_id]


# ---- budget change / infeasible replans ------------------------------------------------------
def test_tightening_a_strict_budget_below_feasibility_is_infeasible_and_keeps_the_original():
    p, cur = base()
    before = copy.deepcopy(cur)
    r = replan(p, cur, [ChangeBudgetOp(op="change_budget", budget=1000, strict=True)], DS)
    assert r.status == "infeasible" and not r.schedule_changed
    assert any(c.code == "budget_too_low" and "Shibuya" not in c.message and "exceeds the strict budget" in c.message for c in r.conflicts)
    assert r.schedule == before and r.new_preferences is None and r.diff is None  # original plan, nothing partial
    assert r.feasibility_report.overall == "fail"  # failing report is visible
    assert "original plan is unchanged" in r.summary


def test_relaxing_the_budget_applies_cleanly():
    p, cur = base()
    r = run(p, cur, [ChangeBudgetOp(op="change_budget", budget=20000, strict=True)])
    assert r.status == "applied" and r.schedule.totals.total_jpy <= 20000


def test_infeasible_replan_never_returns_a_partial_plan():
    p, cur = base()
    r = replan(p, cur, [LockOp(op="lock", attraction_id="senso_ji", day=1, start_time="14:00"),
                        ChangeBudgetOp(op="change_budget", budget=500, strict=True)], DS)
    assert r.status == "infeasible"
    assert r.schedule.days == cur.days and r.schedule.totals == cur.totals


# ---- conflicting operations (rejected before solving) ----------------------------------------------
def test_lock_and_remove_same_item_is_rejected():
    p, cur = base()
    ops = [LockOp(op="lock", attraction_id="shinjuku_gyoen", day=1, start_time="10:00"), RemoveOp(op="remove", attraction_id="shinjuku_gyoen")]
    with pytest.raises(ReplanError, match="lock/move and remove") as e:
        replan(p, cur, ops, DS)
    assert e.value.code == "conflicting_operations"


def test_lock_outside_opening_hours_is_rejected():
    p, cur = base()
    with pytest.raises(ReplanError) as e:
        replan(p, cur, [LockOp(op="lock", attraction_id="tokyo_national_museum", day=1, start_time="08:00")], DS)  # opens 09:30
    assert e.value.code == "conflicting_operations" and "Tokyo National Museum" in e.value.message


def test_overlapping_locks_are_rejected():
    p, cur = base()
    ops = [LockOp(op="lock", attraction_id="senso_ji", day=1, start_time="10:00"), LockOp(op="lock", attraction_id="tokyo_skytree", day=1, start_time="10:30")]
    with pytest.raises(ReplanError) as e:
        replan(p, cur, ops, DS)
    assert e.value.code == "conflicting_operations" and "cannot both happen" in e.value.message


def test_other_invalid_operations_are_rejected_with_clear_codes():
    p, cur = base()
    with pytest.raises(ReplanError) as e:
        replan(p, cur, [RemoveOp(op="remove", attraction_id="atlantis")], DS)
    assert e.value.code == "unknown_attraction"
    with pytest.raises(ReplanError) as e:
        replan(p, cur, [SwitchHotelOp(op="switch_hotel", hotel_id="nope")], DS)
    assert e.value.code == "unknown_hotel"
    with pytest.raises(ReplanError) as e:
        replan(p, cur, [SwitchHotelOp(op="switch_hotel", hotel_id=ASA)], DS)
    assert e.value.code == "invalid_operation"
    with pytest.raises(ReplanError) as e:
        replan(p, cur, [ChangeBudgetOp(op="change_budget", budget=None, strict=True)], DS)
    assert e.value.code == "invalid_operation"
    locked_p = p.model_copy(update={"locked": [LockedActivity(attraction_id="senso_ji", day=1, start_time="14:00")]})
    with pytest.raises(ReplanError, match="unlock it before removing"):
        replan(locked_p, cur, [RemoveOp(op="remove", attraction_id="senso_ji")], DS, confirm_remove_must_visit=True)


# ---- diff warnings ---------------------------------------------------------------------------------
def test_not_like_for_like_warning_fires_when_optional_sights_change():
    p, cur = base()
    r = run(p, cur, [RemoveOp(op="remove", attraction_id=optional_in(cur, p)[0])])
    w = [x for x in r.diff.warnings if x.startswith("Not like-for-like")]
    assert w and "no longer scheduled" in w[0]


def test_no_like_for_like_warning_when_optional_sights_unchanged():
    p, cur = base()
    r = run(p, cur, [ChangeBudgetOp(op="change_budget", budget=50000, strict=False)])
    assert not any("Not like-for-like" in w for w in r.diff.warnings)


def unknown_price_case():
    p = Preferences(days=1, must_visit=["teamlab_planets", "senso_ji"], start_weekday=2, skip=[a for a in DS.attractions if a not in ("teamlab_planets", "senso_ji")])
    return p, solve(p, ASA, DS, with_alternatives=False, objective=SPEC)


def test_unknown_price_warning_fires_and_placeholder_does_not_leak_into_totals():
    p, cur = unknown_price_case()
    r = run(p, cur, [MoveOp(op="move", attraction_id="teamlab_planets", day=1, start_time="15:30")])
    assert r.status == "applied"
    assert any("unknown-price" in w and "TeamLab".lower() in w.lower() for w in r.diff.warnings)
    placeholder = r.diff.optimisation_placeholder_jpy
    assert placeholder == 500  # median of the known admission prices (see test below)
    known_sum = sum(DS.attractions[a].admission_cost or 0 for a in stops(r.schedule))
    assert r.schedule.totals.admissions_jpy == known_sum  # placeholder not added
    assert r.schedule.totals.unknown_cost_items == ["teamlab_planets"]
    assert r.new_breakdown.admissions_jpy == known_sum and r.new_breakdown.optimisation_placeholder_total_jpy == 500


def test_placeholder_is_the_median_of_known_prices():
    from app.data.loader import unknown_price_placeholder
    known = sorted(a.admission_cost for a in DS.attractions.values() if a.admission_cost is not None)
    assert known == [0, 0, 0, 0, 0, 500, 1000, 1000, 1500, 2100, 2200] and unknown_price_placeholder(DS) == 500


def test_unknown_price_attractions_are_no_longer_favoured_for_being_free(monkeypatch):
    # Only teamLab is a candidate. Visiting costs fares + the unknown price; visiting is rewarded by the 1000 JPY penalty it avoids.
    p = Preferences(days=1, start_weekday=2, skip=[a for a in DS.attractions if a != "teamlab_planets"])
    spec = ObjectiveSpec("true_cost", 0, 1000)
    round_trip = DS.fare_jpy[ASA]["teamlab_planets"] * 2
    assert 500 < round_trip < 1000  # precondition: worth visiting at price 0, not at the 500 placeholder
    monkeypatch.setattr(config, "UNKNOWN_PRICE_PLACEHOLDER_OVERRIDE_JPY", 0)  # the old behaviour: unknown == free
    assert "teamlab_planets" in [s.attraction_id for d in solve(p, ASA, DS, with_alternatives=False, objective=spec).days for s in d.stops]
    monkeypatch.setattr(config, "UNKNOWN_PRICE_PLACEHOLDER_OVERRIDE_JPY", None)  # new behaviour: median placeholder
    r = solve(p, ASA, DS, with_alternatives=False, objective=spec)
    assert r.status == "feasible" and r.totals.attractions_scheduled == 0 and r.missed_preferences == ["teamlab_planets"]


def test_placeholder_does_not_enter_strict_budget_or_displayed_totals():
    p = Preferences(days=1, must_visit=["teamlab_planets"], start_weekday=2, budget=700, strict_budget=True,
                    skip=[a for a in DS.attractions if a != "teamlab_planets"])
    r = solve(p, ASA, DS, with_alternatives=False, objective=SPEC)
    assert r.status == "feasible" and r.totals.admissions_jpy == 0 and r.totals.unknown_cost_items == ["teamlab_planets"]


def test_solver_not_optimal_labels_replan_approximate(monkeypatch):
    p = Preferences(days=4, pace="packed", start_weekday=2, must_visit=["senso_ji"])
    cur = solve(p, ASA, DS, with_alternatives=False, objective=SPEC)
    monkeypatch.setattr(config, "SOLVER_MAX_DETERMINISTIC_TIME", 0.05)  # forces a time-limited (FEASIBLE) replan solve
    r = replan(p, cur, [SwitchHotelOp(op="switch_hotel", hotel_id=SHJ)], DS, max_seconds=20)
    assert r.status == "applied" and r.solver_status == "FEASIBLE"
    assert r.proven_optimal is False and r.approximate
    assert any(w.startswith("Approximate") for w in r.diff.warnings)


# ---- determinism -----------------------------------------------------------------------------------------
def test_replan_is_deterministic():
    p, cur = base()
    ops = [RemoveOp(op="remove", attraction_id="shinjuku_gyoen"), LockOp(op="lock", attraction_id="senso_ji", day=1, start_time="14:00")]
    a, b = replan(p, cur, ops, DS), replan(p, cur, ops, DS)
    da, db = a.model_dump(), b.model_dump()
    for d in (da, db):
        d["runtime_seconds"] = 0
        d["schedule"]["solver_meta"]["runtime_seconds"] = 0
    assert da == db


# ---- API ---------------------------------------------------------------------------------------------------
def _body(p, cur, ops, **kw):
    return {"preferences": p.model_dump(), "current_result": cur.model_dump(), "operations": ops, **kw}


def test_api_replan_success_and_statelessness():
    p, cur = base()
    with TestClient(app) as client:
        r = client.post("/replan", json=_body(p, cur, [{"op": "lock", "attraction_id": "senso_ji", "day": 1, "start_time": "14:00"}]))
        assert r.status_code == 200
        j = r.json()
        assert j["status"] == "applied" and j["diff"]["disruption_jpy_per_move"] == config.W_DISRUPTION and j["summary"]
        assert set(vars(app.state)) <= {"dataset", "_state"}  # nothing from the request is stored on the server


def test_api_must_visit_removal_needs_explicit_flag_and_server_never_sets_it():
    p, cur = base()
    ops = [{"op": "remove", "attraction_id": "senso_ji"}]
    with TestClient(app) as client:
        r = client.post("/replan", json=_body(p, cur, ops))
        assert r.status_code == 422 and r.json()["error"]["code"] == "must_visit_removal_not_confirmed" and "Senso-ji" in r.json()["error"]["message"]
        ok = client.post("/replan", json=_body(p, cur, ops, confirm_remove_must_visit=True))
        assert ok.status_code == 200 and ok.json()["diff"]["removed"][0]["was_must_visit"]
    assert ReplanRequest.model_fields["confirm_remove_must_visit"].default is False
    for f in (Path(__file__).parents[1] / "app").rglob("*.py"):  # the server never passes True itself
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.keyword) and node.arg == "confirm_remove_must_visit":
                assert not (isinstance(node.value, ast.Constant) and node.value.value is True), f


def test_api_clear_json_errors():
    p, cur = base()
    with TestClient(app) as client:
        r = client.post("/replan", json=_body(p, cur, [{"op": "explode"}]))
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
        r = client.post("/replan", json=_body(p, cur, [{"op": "lock", "attraction_id": "senso_ji", "day": 1, "start_time": "99:99"}]))
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
        r = client.post("/replan", json=_body(p, cur, [{"op": "remove", "attraction_id": "atlantis"}]))
        assert r.status_code == 422 and r.json()["error"]["code"] == "unknown_attraction"
        r = client.post("/replan", json=_body(p, cur, [{"op": "change_budget", "budget": 1000, "strict": True}]))
        assert r.status_code == 200 and r.json()["status"] == "infeasible" and r.json()["schedule_changed"] is False


# ---- property: keep LAST -----------------------------------------------------------------------------------------
def test_every_replanned_schedule_passes_the_independent_validator():
    assert len(SEEN) >= 8
    for prefs, hotel, res in SEEN:
        assert build_report(res, DS, prefs, hotel).overall != "fail"
        assert set(prefs.must_visit) <= set(stops(res))  # a must-visit is only ever dropped by explicit confirmation
