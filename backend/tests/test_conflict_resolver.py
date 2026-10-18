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
