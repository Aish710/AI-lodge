"""Phase 2 scenarios 1-12 plus solver/validator safety tests. No LLM is called anywhere.

Weekdays: start_weekday 0=Mon, 2=Wed. Hotels: SHJ central, ASA mid, ODA cheap and far.
Every solver result is recorded and re-validated by the last tests in this file.
"""
import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.data.loader import load_dataset
from app.optimiser.baseline import baseline
from app.optimiser.schedule import assemble
from app.optimiser.solver import solve
from app.schemas import Preferences
from app.validator.feasibility_report import build_report

SHJ, ASA, ODA = "hotel_kitsune_shinjuku", "hotel_lantern_asakusa", "hotel_harbour_odaiba"
DS = load_dataset()
REGISTRY: list[tuple[Preferences, str, object]] = []
RESULTS_DIR = Path(__file__).parent / "results"


def run(prefs: Preferences, hotel: str = ASA):
    r = solve(prefs, hotel, DS)
    REGISTRY.append((prefs, hotel, r))
    return r


def ids(result):
    return [s.attraction_id for d in result.days for s in d.stops]


def check(report, cid):
    return next(c for c in report.checks if c.id == cid)


# ---- Scenario 1: basic ------------------------------------------------------
def test_s01_three_nearby_attractions_give_valid_route():
    p = Preferences(days=1, must_visit=["senso_ji", "tokyo_skytree", "tokyo_national_museum"], start_weekday=2)
    r = run(p)
    assert r.status == "feasible"
    assert sorted(ids(r)) == sorted(p.must_visit)
    rep = build_report(r, DS, p, ASA)
    assert rep.overall in ("pass", "pass_with_warnings")


# ---- Scenario 2: two hotels, total-trip comparison (simple precursor of Phase 3) ---------
def test_s02_two_hotels_can_be_compared_on_total_trip_cost():
    p = Preferences(days=2, must_visit=["senso_ji", "tokyo_skytree", "teamlab_planets", "shibuya_sky"], start_weekday=2)
    totals = {}
    for h in (ASA, ODA):
        r = run(p, h)
        assert r.status == "feasible"
        totals[h] = DS.hotels[h].nightly_rate * p.days + r.totals.total_jpy  # rooms + admissions + transport
    assert totals[ASA] != totals[ODA]
    assert all(v > 0 for v in totals.values())


# ---- Scenario 3: scattered attractions beat the naive baseline ---------------
def test_s03_scattered_attractions_less_travel_than_baseline():
    order = ["meiji_jingu", "tokyo_skytree", "shibuya_sky", "senso_ji", "shinjuku_gyoen", "tokyo_national_museum"]
    p = Preferences(days=2, must_visit=order, start_weekday=2)  # hand-built west/east alternating input order
    s, b = run(p), baseline(p, ASA, DS)
    assert s.status == "feasible" and b.status == "feasible"
    assert sorted(ids(s)) == sorted(ids(b))  # same attractions: fair comparison
    assert s.totals.travel_minutes < b.totals.travel_minutes
    assert build_report(b, DS, p, ASA).overall != "fail"  # baseline is a valid plan, not a strawman


# ---- Scenario 4: mandatory attraction ----------------------------------------
def test_s04_mandatory_attraction_included():
    p = Preferences(days=1, must_visit=["ghibli_museum"], start_weekday=2)
    r = run(p, SHJ)
    assert r.status == "feasible" and "ghibli_museum" in ids(r)
    assert next(s for s in r.days[0].stops if s.attraction_id == "ghibli_museum").is_must_visit


def test_s04_mandatory_attraction_impossible_is_reported():
    p = Preferences(days=1, must_visit=["ghibli_museum"], start_weekday=1)  # Tuesday: closed
    r = run(p)
    assert r.status == "infeasible"
    assert any(c.code == "closed_all_days" and "Ghibli Museum is closed on all 1 trip day" in c.message for c in r.conflicts)
    assert build_report(r, DS, p, ASA).overall == "fail"


# ---- Scenario 5: lock at 2 PM ---------------------------------------------------
def test_s05_locked_activity_at_2pm_stays_fixed():
    p = Preferences(days=1, must_visit=["senso_ji"], start_weekday=2,
                    locked=[{"attraction_id": "tokyo_skytree", "day": 1, "start_time": "14:00"}])
    r = run(p)
    sky = next(s for s in r.days[0].stops if s.attraction_id == "tokyo_skytree")
    assert sky.start == "14:00"
    assert "senso_ji" in ids(r)
    assert check(build_report(r, DS, p, ASA), "locked").status == "pass"


def test_s05_impossible_lock_is_reported():
    p = Preferences(days=1, start_weekday=0,
                    locked=[{"attraction_id": "tokyo_national_museum", "day": 1, "start_time": "14:00"}])  # Monday closed
    r = run(p)
    assert r.status == "infeasible" and r.conflicts[0].code == "locked_not_possible"


# ---- Scenario 6: hotel change recalculates -----------------------------------
def test_s06_changing_hotel_recalculates_itinerary():
    p = Preferences(days=1, must_visit=["senso_ji", "shibuya_sky"], start_weekday=2)
    a, o = run(p, ASA), run(p, ODA)
    assert a.hotel_id == ASA and o.hotel_id == ODA
    assert a.totals.travel_minutes != o.totals.travel_minutes
    assert a.days[0].stops[0].travel_minutes_from_previous != o.days[0].stops[0].travel_minutes_from_previous or \
        a.days[0].stops[0].attraction_id != o.days[0].stops[0].attraction_id


# ---- Scenario 7: closed on the chosen day -------------------------------------
def test_s07_attraction_closed_that_day_is_not_scheduled_then():
    p = Preferences(days=2, pace="packed", start_weekday=0, must_visit=["tokyo_skytree"])  # day 1 = Monday
    r = run(p)
    day1 = [s.attraction_id for s in r.days[0].stops]
    for closed_monday in ("tokyo_national_museum", "shinjuku_gyoen", "imperial_palace_east_gardens"):
        assert closed_monday not in day1
    assert check(build_report(r, DS, p, ASA), "opening_hours").status == "pass"


# ---- Scenario 8: budget too low ------------------------------------------------
def test_s08_budget_too_low_reports_infeasible_with_amount():
    p = Preferences(days=1, must_visit=["tokyo_skytree", "shibuya_sky"], budget=1000, strict_budget=True, start_weekday=2)
    r = run(p)
    assert r.status == "infeasible"
    c = next(c for c in r.conflicts if c.code == "budget_too_low")
    assert "exceeds the strict budget by at least" in c.message
    assert any(a.kind == "relax_budget" for a in r.alternatives)  # computed alternative that was actually solved


def test_s08_strict_budget_respected_when_feasible():
    p = Preferences(days=1, must_visit=["senso_ji"], budget=1500, strict_budget=True, start_weekday=2)
    r = run(p)
    assert r.status == "feasible" and r.totals.total_jpy <= 1500
    assert check(build_report(r, DS, p, ASA), "budget").status == "pass"


# ---- Scenario 9: not enough time ----------------------------------------------
def test_s09_not_enough_time_conflict_is_explained():
    p = Preferences(days=1, pace="packed", day_start="09:00", day_end="13:00", start_weekday=2,
                    must_visit=["tokyo_national_museum", "senso_ji", "tokyo_skytree"])  # each fits alone; 330+ min together
    r = run(p)
    assert r.status == "infeasible"
    c = next(c for c in r.conflicts if c.code == "not_enough_time")
    assert "only 4h are available" in c.message and "including travel" in c.message
    kinds = {a.kind for a in r.alternatives}
    assert "add_day" in kinds  # computed: a 2-day version was solved and found feasible
    assert all("attractions_scheduled" in a.details for a in r.alternatives)  # each one was actually solved


# ---- Scenario 10: travel exceeds available time ---------------------------------
def test_s10_travel_time_exceeds_day_window_is_rejected():
    p = Preferences(days=1, day_start="09:00", day_end="12:00", start_weekday=2, must_visit=["ghibli_museum"])
    r = run(p, ODA)
    assert r.status == "infeasible" and r.days == []
    c = r.conflicts[0]
    assert c.code == "does_not_fit_day" and "round trip" in c.message
    assert build_report(r, DS, p, ODA).overall == "fail"


# ---- Scenario 11: missing price -------------------------------------------------
def test_s11_unknown_price_counted_as_unknown_and_surfaced():
    p = Preferences(days=1, must_visit=["teamlab_planets"], start_weekday=2)
    r = run(p)
    stop = next(s for s in r.days[0].stops if s.attraction_id == "teamlab_planets")
    assert stop.cost_status == "unknown" and stop.cost == 0 and "price_unknown" in stop.uncertainty_flags
    assert "teamlab_planets" in r.totals.unknown_cost_items
    assert any("excluded from total (unknown)" in n for n in r.notes)
    rep = build_report(r, DS, p, ASA)
    assert check(rep, "unknown_prices").status == "warning" and rep.overall == "pass_with_warnings"


# ---- Scenario 12: missing hours -----------------------------------------------
def test_s12_unknown_hours_excluded_by_default_and_flagged_when_allowed():
    off = Preferences(days=1, pace="packed", start_weekday=2)
    assert "akihabara" not in ids(run(off))  # never assumed open

    must = Preferences(days=1, must_visit=["akihabara"], start_weekday=2)
    r = run(must)
    assert r.status == "infeasible" and r.conflicts[0].code == "unknown_hours_not_allowed"
    assert any(a.kind == "allow_unknown_hours" for a in r.alternatives)

    on = Preferences(days=1, must_visit=["akihabara"], allow_unknown_hours=True, start_weekday=2)
    r2 = run(on)
    assert r2.status == "feasible"
    aki = next(s for s in r2.days[0].stops if s.attraction_id == "akihabara")
    assert "opening_hours_unknown" in aki.uncertainty_flags
    rep = build_report(r2, DS, on, ASA)
    assert check(rep, "unknown_hours_used").status == "warning" and rep.overall == "pass_with_warnings"


# ---- Solver properties ------------------------------------------------------------
def test_determinism_same_input_same_schedule():
    p = Preferences(days=2, pace="balanced", must_visit=["senso_ji", "meiji_jingu"], start_weekday=2)
    a, b = solve(p, ASA, DS), solve(p, ASA, DS)
    assert a.days == b.days and a.totals == b.totals


def test_pace_cap_and_skip_respected():
    p = Preferences(days=2, pace="relaxed", skip=["senso_ji"], start_weekday=2)
    r = run(p)
    assert all(len(d.stops) <= 2 for d in r.days)
    assert "senso_ji" not in ids(r)


def test_must_visit_never_dropped_for_feasibility():
    # 3 musts but day only fits ~2: must report infeasible rather than silently drop one.
    p = Preferences(days=1, day_start="09:00", day_end="14:00", start_weekday=2,
                    must_visit=["tokyo_national_museum", "senso_ji", "tokyo_skytree", "shibuya_sky"])
    r = run(p)
    assert r.status == "infeasible"


def test_infeasible_when_requirements_individually_ok_but_jointly_impossible():
    p = Preferences(days=1, pace="relaxed", start_weekday=2, must_visit=["senso_ji", "tokyo_skytree", "shibuya_sky"])
    r = run(p)
    assert r.status == "infeasible" and r.conflicts[0].code == "pace_cap"


# ---- Validator catches corrupted schedules (one test per corruption) ----------------
def _good(prefs=None, plan=None, hotel=ASA):
    prefs = prefs or Preferences(days=1, must_visit=["senso_ji", "tokyo_skytree"], start_weekday=2)
    days, totals = assemble(DS, prefs, hotel, plan or [[("senso_ji", 600), ("tokyo_skytree", 720)]])
    from app.schemas import SolveResult
    return prefs, SolveResult(status="feasible", hotel_id=hotel, days=days, totals=totals)


def test_validator_accepts_a_correct_hand_built_schedule():
    prefs, s = _good()
    assert build_report(s, DS, prefs, ASA).overall != "fail"


def test_validator_catches_overlap():
    prefs, s = _good(plan=[[("senso_ji", 600), ("tokyo_skytree", 620)]])
    rep = build_report(s, DS, prefs, ASA)
    assert rep.overall == "fail" and check(rep, "overlaps").status == "fail"


def test_validator_catches_attraction_closed_that_day():
    prefs = Preferences(days=1, start_weekday=0)  # Monday
    prefs, s = _good(prefs, [[("tokyo_national_museum", 600)]])
    rep = build_report(s, DS, prefs, ASA)
    assert rep.overall == "fail" and check(rep, "opening_hours").status == "fail"


def test_validator_catches_missing_must_visit():
    prefs, s = _good()
    s.days[0].stops.pop()
    rep = build_report(s, DS, prefs, ASA)
    assert rep.overall == "fail" and check(rep, "must_visits").stop_ids == ["tokyo_skytree"]


def test_validator_catches_over_budget():
    prefs = Preferences(days=1, must_visit=["tokyo_skytree", "shibuya_sky"], budget=1000, strict_budget=True, start_weekday=2)
    prefs, s = _good(prefs, [[("tokyo_skytree", 600), ("shibuya_sky", 780)]])
    rep = build_report(s, DS, prefs, ASA)
    assert rep.overall == "fail" and check(rep, "budget").status == "fail"


def test_validator_catches_too_little_travel_time():
    prefs, s = _good(plan=[[("senso_ji", 600), ("tokyo_skytree", 691)]])  # 1 min gap, needs ~16
    s.days[0].stops[1].start = "11:31"
    rep = build_report(s, DS, prefs, ASA)
    assert check(rep, "travel_gaps").status == "fail" and rep.overall == "fail"


def test_validator_catches_moved_lock_duplicate_and_day_window():
    prefs = Preferences(days=1, start_weekday=2, locked=[{"attraction_id": "senso_ji", "day": 1, "start_time": "14:00"}])
    _, s = _good(prefs, [[("senso_ji", 600)]])
    assert check(build_report(s, DS, prefs, ASA), "locked").status == "fail"
    _, d = _good(prefs=Preferences(days=1, start_weekday=2), plan=[[("senso_ji", 600), ("senso_ji", 800)]])
    assert check(build_report(d, DS, Preferences(days=1, start_weekday=2), ASA), "duplicates").status == "fail"
    p2 = Preferences(days=1, start_weekday=2, day_end="12:00")
    _, w = _good(prefs=p2, plan=[[("tokyo_skytree", 660)]])
    assert check(build_report(w, DS, p2, ASA), "day_window").status == "fail"


def test_validator_ignores_reported_cost_and_checks_the_dataset():
    prefs = Preferences(days=1, must_visit=["tokyo_skytree"], budget=500, strict_budget=True, start_weekday=2)
    prefs, s = _good(prefs, [[("tokyo_skytree", 600)]])
    s.days[0].stops[0].cost = 0  # schedule lies about cost
    s.totals.total_jpy = 0
    assert check(build_report(s, DS, prefs, ASA), "budget").status == "fail"


# ---- Validator independence ------------------------------------------------------------
def test_validator_does_not_import_optimiser():
    for f in (Path(__file__).parents[1] / "app" / "validator").glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            assert not any("optimiser" in n for n in names), f"{f.name} imports {names}"


def test_importing_validator_does_not_load_optimiser_modules():
    code = "import sys; import app.validator.feasibility_report; print(any(m.startswith('app.optimiser') for m in sys.modules))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=Path(__file__).parents[1])
    assert out.stdout.strip() == "False", out.stderr


# ---- Property checks across everything solved above (keep LAST in the file) -----------
def test_every_result_in_suite_passes_validator_and_keeps_must_visits():
    assert len(REGISTRY) >= 20
    feasible = 0
    for prefs, hotel, r in REGISTRY:
        rep = build_report(r, DS, prefs, hotel)
        if r.status == "feasible":
            feasible += 1
            assert rep.overall != "fail", (prefs, rep.summary)
            assert set(prefs.must_visit) <= set(ids(r))  # never silently dropped
            assert len(r.days) == prefs.days
        else:
            assert rep.overall == "fail" and r.conflicts and r.days == []
    assert feasible >= 10


def test_write_measured_solve_times():
    rows = ["# Measured solve times", "", "Measured on this machine during the test run (CP-SAT, 1 worker, fixed seed).", "",
            "| Case | Days | Status | Solver status | Seconds |", "|---|---|---|---|---|"]
    for i, (prefs, hotel, r) in enumerate(REGISTRY, 1):
        rows.append(f"| {i} | {prefs.days} | {r.status} | {r.solver_meta.solver_status} | {r.solver_meta.runtime_seconds} |")
    times = [r.solver_meta.runtime_seconds for _, _, r in REGISTRY]
    rows += ["", f"Cases: {len(times)}, mean {sum(times) / len(times):.3f}s, max {max(times):.3f}s."]
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "solve_times.md").write_text("\n".join(rows) + "\n")
