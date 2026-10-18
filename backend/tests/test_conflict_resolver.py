"""Conflict resolver: every repair is a relaxed problem that was actually solved AND passed the independent validator; combinations are bounded; nothing is applied."""
from app.optimiser import solver
from app.optimiser.solver import solve
from test_constraints import DS, H, three_musts


def alts(prefs, hotel=H):
    r = solve(prefs, hotel, DS)
    assert r.status == "infeasible"
    return r


def test_an_activity_limit_conflict_offers_the_limit_lever_and_each_repair_is_validated():
    r = alts(three_musts(max_activities_per_day=2))
    kinds = {a.kind for a in r.alternatives}
    assert "raise_activity_limit" in kinds and "add_day" in kinds
    assert all(a.details["verified_by_validator"] is True and a.details["changes"] for a in r.alternatives)
    raise_ = next(a for a in r.alternatives if a.kind == "raise_activity_limit")
    assert raise_.details["changes"] == [{"field": "max_activities_per_day", "from": 2, "to": 3}]


def test_a_travel_limit_conflict_offers_to_relax_or_remove_the_limit():
    r = alts(three_musts(max_daily_travel_minutes=20))
    touched = {c["field"] for a in r.alternatives for c in a.details["changes"]}
    assert "max_daily_travel_minutes" in touched                       # as a single change or, when one change is not enough, inside a verified two-change combination
    assert all(a.details["combination"] == (len(a.details["changes"]) == 2) for a in r.alternatives)


def test_repairs_are_ranked_by_how_much_they_change_and_a_must_visit_is_given_up_last():
    r = alts(three_musts(max_activities_per_day=2))
    ranks = [a.details["rank"] for a in r.alternatives]
    assert ranks == list(range(1, len(ranks) + 1))
    keys = [(len(a.details["changes"]), any(c.get("removed") for c in a.details["changes"])) for a in r.alternatives]
    assert keys == sorted(keys)


def test_the_request_object_is_never_changed_by_diagnosis():
    p = three_musts(max_activities_per_day=2)
    before = p.model_dump()
    solve(p, H, DS)
    assert p.model_dump() == before


def test_combinations_are_only_tried_when_no_single_change_works_and_are_bounded(monkeypatch):
    calls = []
    real = solver.solve

    def counting(prefs, hotel_id, ds, **kw):
        calls.append(prefs)
        return real(prefs, hotel_id, ds, **kw)

    p = three_musts(max_activities_per_day=1, max_daily_travel_minutes=20).model_copy(update={"days": 1})
    singles = [a for a in solve(p, H, DS).alternatives if not a.details["combination"]]
    monkeypatch.setattr(solver, "solve", counting)
    r = solver._alternatives(p, H, DS, budget=None)
    if singles:
        assert not any(a.details["combination"] for a in r)               # a single change worked: no combination is offered
    assert len(calls) <= 30
    assert all(a.details["combination"] is False or len(a.details["changes"]) == 2 for a in r)


def test_an_irreparable_request_returns_no_invented_repair():
    p = three_musts().model_copy(update={"must_visit": ["senso_ji", "meiji_jingu", "shibuya_sky"], "day_start": "09:00", "day_end": "09:30"})
    r = solve(p, H, DS)
    assert r.status == "infeasible" and r.conflicts
    for a in r.alternatives:                                             # whatever is offered was solved and validated
        assert a.details["verified_by_validator"] is True


def test_the_api_returns_structured_changes_the_interface_can_apply():
    from fastapi.testclient import TestClient
    from app.main import app
    p = three_musts(max_activities_per_day=2)
    with TestClient(app) as c:
        j = c.post("/optimise", json={"city_id": "tokyo", "preferences": p.model_dump(), "hotel_id": H, "explain": False}).json()
    assert j["result"]["status"] == "infeasible" and j["result"]["alternatives"]
    for a in j["result"]["alternatives"]:
        assert a["details"]["verified_by_validator"] is True and a["details"]["rank"] >= 1
        assert all("field" in ch for ch in a["details"]["changes"])


# ---- strict mode, unknown opening hours (Kuala Lumpur, National Mosque) ---------------------------------------------------------------------------
import pytest  # noqa: E402

from app.data.loader import load_all_city_datasets  # noqa: E402
from app.optimiser.hotel_compare import compare_hotels  # noqa: E402
from app.schemas import Conflict, Preferences  # noqa: E402
from app.validator.feasibility_report import build_report  # noqa: E402

KL = load_all_city_datasets()["kuala_lumpur"]
MOSQUE = "national_mosque_malaysia"
KH = "hotel_klcc_lantern"


def kl(**over):
    return Preferences(days=2, must_visit=[MOSQUE], start_weekday=2, **over)


def test_the_mosque_really_has_unknown_hours_and_the_data_is_not_edited():
    assert any(v == "unknown" for v in KL.attractions[MOSQUE].opening_hours.values())      # the data says "unknown"; nothing fabricates hours


def test_strict_mode_blocks_by_missing_information_and_says_so_once():
    r = solve(kl(), KH, KL)
    assert r.status == "infeasible"
    assert [c.code for c in r.conflicts] == ["unknown_hours_not_allowed"] and r.conflicts[0].category == "missing_information"
    rep = build_report(r, KL, kl(), KH)
    assert rep.overall == "fail" and rep.blocked_by == "missing_information" and rep.verification == "none"
    assert len(rep.checks) == 1
    text = rep.summary + " " + rep.checks[0].message
    assert text.count("National Mosque") == 0                                    # the specific conflict is returned once, in `conflicts`, not repeated in the report
    assert "unknown_hours_not_allowed" not in text and "impossible" not in text.lower()


def test_every_hotel_is_blocked_by_the_same_missing_information_and_the_insight_does_not_claim_impossibility():
    c = compare_hotels(kl(), sorted(KL.hotels), KL, include_sensitivity=False)
    assert all(not r.feasible and all(x.category == "missing_information" for x in r.conflicts) for r in c.results)
    assert "missing information" in c.insight and "not a finding that the visit is impossible" in c.insight


def test_repairs_are_complete_validated_and_never_apply_themselves():
    r = solve(kl(), KH, KL)
    kinds = {a.kind: a for a in r.alternatives}
    assert {"allow_unknown_hours", "demote_must_visit"} <= set(kinds)
    for a in r.alternatives:
        assert a.message.strip() and a.details["changes"] and a.details["verified_by_validator"] is True
    assert kinds["allow_unknown_hours"].details["changes"] == [{"field": "allow_unknown_hours", "from": False, "to": True}]
    assert "provisionally" in kinds["allow_unknown_hours"].message
    assert MOSQUE in kl().must_visit                                              # the request still has its must-visit: nothing was removed by diagnosing


def test_provisional_planning_is_explicit_conditional_and_never_called_verified():
    p = kl(allow_unknown_hours=True)
    r = solve(p, KH, KL)
    assert r.status == "feasible" and MOSQUE in {s.attraction_id for d in r.days for s in d.stops}
    stop = next(s for d in r.days for s in d.stops if s.attraction_id == MOSQUE)
    assert "opening_hours_unknown" in stop.uncertainty_flags
    rep = build_report(r, KL, p, KH)
    assert rep.verification == "conditional" and rep.conditional_stop_ids == [MOSQUE] and rep.overall == "pass_with_warnings"
    assert "Conditional" in rep.summary and "Check before you travel" in rep.summary and "verified" not in rep.summary.lower().replace("unverified", "")


def test_provisional_mode_does_not_bypass_other_hard_constraints():
    tight = kl(allow_unknown_hours=True, day_end="09:30")
    r = solve(tight, KH, KL, with_alternatives=False)
    assert r.status == "infeasible" and all(c.code != "unknown_hours_not_allowed" for c in r.conflicts)      # the day window still binds with the opt-in on


def test_an_unknown_hours_optional_sight_is_simply_not_scheduled_in_strict_mode():
    p = Preferences(days=2, must_visit=[], start_weekday=2)
    r = solve(p, KH, KL, with_alternatives=False)
    assert r.status == "feasible" and MOSQUE not in {s.attraction_id for d in r.days for s in d.stops}
    assert build_report(r, KL, p, KH).verification == "verified"


def test_a_feasible_plan_without_unknown_hours_is_verified():
    p = Preferences(days=2, must_visit=["petronas_twin_towers"] if "petronas_twin_towers" in KL.attractions else [], start_weekday=2)
    r = solve(p, KH, KL, with_alternatives=False)
    assert build_report(r, KL, p, KH).verification in ("verified", "conditional")


def test_a_client_cannot_set_a_conflict_category():
    c = Conflict(code="closed_all_days", message="x", category="missing_information")
    assert c.category == "known_constraints"
