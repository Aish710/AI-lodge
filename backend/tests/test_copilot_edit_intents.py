"""Natural-language editing intents. The model chooses an operation and copies a day number / name; code builds the proposal from the validated schedule; nothing is applied."""
import copy

import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_dataset
from app.evidence import verify_evidence
from app.schemas import nights_for
from app.validator.feasibility_report import build_report
from app.main import app
from app.llm.client import get_llm_client
from app.schemas import Preferences
from llm_mock import MockLLM

DS = load_dataset()
HOTEL = "hotel_lantern_asakusa"


@pytest.fixture(scope="module")
def ctx():
    app.dependency_overrides[get_llm_client] = lambda: None
    with TestClient(app) as api:
        p = Preferences(days=3, must_visit=["senso_ji"], start_weekday=2)
        plan = api.post("/optimise", json={"preferences": p.model_dump(), "hotel_id": HOTEL}).json()
        yield api, {"preferences": p.model_dump(), "current_result": plan["result"], "fingerprint": plan["fingerprint"]}, plan


def ask(ctx, text, reply):
    api, body, _ = ctx
    app.dependency_overrides[get_llm_client] = lambda: MockLLM([reply])
    return api.post("/copilot", json={**body, "text": text, "operation": None}).json()


def busiest(plan):
    return max(plan["result"]["days"], key=lambda d: len(d["stops"]))


def test_rebalance_builds_a_capped_whatif_proposal_and_changes_nothing(ctx):
    plan = ctx[2]
    d = busiest(plan)
    before = copy.deepcopy(ctx[1])
    out = ask(ctx, f"Make day {d['day']} less crowded.", {"operation": "REBALANCE_DAY", "day": d["day"]})
    assert out["status"] == "ok" and out["executed"] is False and ctx[1] == before
    if len(d["stops"]) > 1:
        assert out["proposal"]["kind"] == "whatif" and out["proposal"]["patch"] == {"maxActivities": len(d["stops"]) - 1}
        assert out["handoff"] == "scenario"
    assert "Nothing has been changed" in out["message"] or out["proposal"] is None


def test_a_day_number_the_person_did_not_write_is_discarded(ctx):
    out = ask(ctx, "Make it less crowded.", {"operation": "REBALANCE_DAY", "day": 2})
    assert out["operation"] == "CLARIFY" and out["proposal"] is None


def test_move_queues_a_replan_move_with_the_current_start_time(ctx):
    plan = ctx[2]
    d = busiest(plan)
    stop = d["stops"][0]
    name = DS.attractions[stop["attraction_id"]].name
    target = 1 if d["day"] != 1 else 2
    out = ask(ctx, f"Move {name} to day {target}.", {"operation": "MOVE_ATTRACTION", "attraction_name": name, "target_day": target})
    assert out["proposal"]["kind"] == "move" and out["handoff"] == "queue"
    assert out["proposal"]["op"] == {"op": "move", "attraction_id": stop["attraction_id"], "day": target, "start_time": stop["start"]}
    assert out["executed"] is False


def test_move_to_a_day_outside_the_trip_or_an_unnamed_sight_proposes_nothing(ctx):
    d = busiest(ctx[2])
    name = DS.attractions[d["stops"][0]["attraction_id"]].name
    assert ask(ctx, f"Move {name} to day 9.", {"operation": "MOVE_ATTRACTION", "attraction_name": name, "target_day": 9})["proposal"] is None
    assert ask(ctx, "Move something to day 2.", {"operation": "MOVE_ATTRACTION", "attraction_name": "Atlantis Tower", "target_day": 2})["proposal"] is None


def test_finish_earlier_proposes_an_earlier_day_end_or_nothing(ctx):
    out = ask(ctx, "Can I finish sightseeing earlier?", {"operation": "FINISH_EARLIER"})
    assert out["status"] == "ok" and out["executed"] is False
    if out["proposal"]:
        assert out["proposal"]["patch"]["dayEnd"] < ctx[1]["preferences"]["day_end"]


def test_omission_offers_a_preview_not_a_claimed_cause(ctx):
    plan = ctx[2]
    scheduled = {s["attraction_id"] for day in plan["result"]["days"] for s in day["stops"]}
    missing = next(a for a in DS.attractions.values() if a.id not in scheduled)
    out = ask(ctx, f"Why wasn't {missing.name} included?", {"operation": "EXPLAIN_OMISSION", "attraction_name": missing.name})
    assert out["proposal"] == {"kind": "whatif", "patch": {"addMust": [missing.id]}, "label": f"Preview {missing.name} as a must-visit"}
    assert "not establish" in str(out["evidence"]) or "Not established" in str(out["evidence"])


def test_a_forged_proposal_fails_the_evidence_check(ctx):
    from app.llm.copilot import answer
    from app.schemas import SolveResult
    prefs = Preferences(**ctx[1]["preferences"])
    res = SolveResult(**ctx[1]["current_result"])
    rep = build_report(res, DS, prefs, res.hotel_id)

    def _proposal_problems(p, *_):
        return verify_evidence({"evidence": [], "message": "", "proposal": p}, res, rep, prefs, DS, nights_for(prefs)[0])
    for bad in ({"kind": "whatif", "patch": {"budget": 1}}, {"kind": "whatif", "patch": {"maxActivities": 99}}, {"kind": "whatif", "patch": {"addMust": ["nowhere"]}},
                {"kind": "move", "op": {"op": "move", "attraction_id": "nowhere", "day": 1, "start_time": "09:00"}}, {"kind": "move", "op": {"op": "remove", "attraction_id": "senso_ji", "day": 1}},
                {"kind": "apply"}):
        assert _proposal_problems(bad), bad
    assert _proposal_problems(None) == []


def test_quick_question_without_a_day_asks_which_day(ctx):
    api, body, _ = ctx
    app.dependency_overrides[get_llm_client] = lambda: None
    out = api.post("/copilot", json={**body, "operation": "REBALANCE_DAY", "text": ""}).json()
    assert out["proposal"] is None and "Which day" in out["message"] and out["call_count"] == 0
