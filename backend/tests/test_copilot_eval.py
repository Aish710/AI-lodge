"""The copilot evaluation suite: frozen cases, integration metrics (mock oracle), a clearly labelled non-model baseline, and the evidence verifier that fails closed."""
import importlib
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data.loader import load_all_city_datasets
from app.evidence import verify_evidence
from app.llm.client import get_llm_client
from app.main import app
from app.schemas import Preferences
from app.validator.feasibility_report import build_report

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))
ev = importlib.import_module("run_copilot_eval")
DATA = json.loads(ev.CASES.read_text())
ALL = load_all_city_datasets()


def test_the_case_file_is_large_diverse_frozen_and_not_called_independent():
    cases = DATA["cases"]
    assert len(cases) >= 50 and {c["city"] for c in cases} == {"tokyo", "singapore", "seoul", "kuala_lumpur"}
    cats = {c["category"] for c in cases}
    assert {"simple_question", "multi_constraint", "ambiguous_preference", "conflicting_preference", "cost_explanation", "alternative_comparison", "repair_request", "unsupported", "missing_data", "ai_off"} <= cats
    assert DATA["independent"] is False and "developer" in DATA["authored_by"] and len({c["id"] for c in cases}) == len(cases)
    for city in ("tokyo", "singapore", "seoul", "kuala_lumpur"):
        assert sum(1 for c in cases if c["city"] == city) >= 12
    assert all(c["expected_operation"] in ("EXPLAIN_PLAN", "EXPLAIN_CONSTRAINT", "EXPLAIN_COST_BREAKDOWN", "COMPARE_ALTERNATIVES", "ANALYSE_TRADEOFF", "PROPOSE_REPAIR", "PREVIEW_SCENARIO",
                                              "EXPLAIN_OMISSION", "IDENTIFY_UNCERTAINTY", "CLARIFY", "UNSUPPORTED") for c in cases)


@pytest.fixture(scope="module")
def oracle_rows():
    return ev.run("oracle", lambda c, name: ev.Oracle(c["expected_operation"], name))


def test_mock_oracle_integration_is_complete_and_never_executes_anything(oracle_rows):
    s = ev.summarise(oracle_rows)
    assert s["routing"]["pct"] == 100 and s["grounding"]["pct"] == 100 and s["task_success"]["pct"] == 100 and s["executed_anything"] == 0
    assert s["ai_off"]["correct"] == s["ai_off"]["of"] > 0                      # quick questions work with no model at all


def test_the_keyword_baseline_is_a_non_model_and_is_labelled_so():
    rows = ev.run("keyword", lambda c, name: ev.Keyword())
    s = ev.summarise(rows)
    assert 0 <= s["intent_accuracy"]["pct"] <= 100 and s["executed_anything"] == 0
    text = ev.render("keyword", s, rows)
    assert "NOT a language model" in text and "not independent" in text and "A live run has not been made unless a live file exists" in text


def test_the_oracle_report_says_it_is_a_mock():
    rows = ev.run("oracle", lambda c, name: ev.Oracle(c["expected_operation"], name))
    assert "MOCK ORACLE" in ev.render("oracle", ev.summarise(rows), rows) and "says nothing about any model" in ev.render("oracle", ev.summarise(rows), rows)


def test_a_live_run_needs_opt_in_and_the_plan_makes_no_call(monkeypatch, capsys):
    assert ev.main(["--plan"]) == 0 and "nothing was run" in capsys.readouterr().out
    lc = importlib.import_module("live_common")
    monkeypatch.delenv("RUN_LIVE_LLM_EVAL", raising=False)
    monkeypatch.setattr(lc, "load_env_file", lambda: None)
    assert ev.main(["--live"]) == 0 and "opt-in" in capsys.readouterr().out


# ---- the evidence verifier -----------------------------------------------------------------------------------------------------------------------
def ctx():
    ds = ALL["tokyo"]
    prefs, hotel = ev.build_prefs(ds, "feasible", "tokyo")
    app.dependency_overrides[get_llm_client] = lambda: None
    with TestClient(app) as api:
        plan = api.post("/optimise", json={"preferences": prefs.model_dump(), "hotel_id": hotel}).json()
    return ds, prefs, plan


def ask(op, **over):
    ds, prefs, plan = ctx()
    body = {"preferences": prefs.model_dump(), "current_result": plan["result"], "fingerprint": plan["fingerprint"], "text": "", "operation": op, **over}
    app.dependency_overrides[get_llm_client] = lambda: None
    with TestClient(app) as api:
        return api.post("/copilot", json=body).json()


def test_a_wrong_cost_in_the_evidence_is_rejected_and_nothing_is_shown(monkeypatch):
    import app.llm.copilot as cp
    real = cp.summarise_costs

    def wrong(*a, **k):
        out = real(*a, **k)
        out["trip"]["rooms"] += 1000                       # a bug, or tampering, that makes the shown rooms cost wrong
        out["trip"]["cash_total_with_rooms"] += 1000
        return out
    monkeypatch.setattr(cp, "summarise_costs", wrong)
    out = ask("EXPLAIN_COST_BREAKDOWN")
    assert out["status"] == "evidence_rejected" and out["evidence"] == [] and "could not be verified" in out["message"] and out["handoff"] is None and out["executed"] is False


def test_the_verifier_catches_each_kind_of_bad_evidence():
    ds, prefs, plan = ctx()
    from app.schemas import SolveResult
    res = SolveResult.model_validate(plan["result"])
    rep = build_report(res, ds, prefs, res.hotel_id)
    good = {"message": "ok", "evidence": [{"kind": "calculated", "reference": "result.totals.travel_minutes", "label": "x", "value": res.totals.travel_minutes}]}
    assert verify_evidence(good, res, rep, prefs, ds, prefs.days - 1) == []
    cases = {
        "travel": {"message": "ok", "evidence": [{"kind": "calculated", "reference": "result.totals.travel_minutes", "label": "x", "value": res.totals.travel_minutes + 1}]},
        "kind": {"message": "ok", "evidence": [{"kind": "model_says", "reference": "x", "label": "x", "value": 1}]},
        "verdict": {"message": "ok", "evidence": [{"kind": "calculated", "reference": "feasibility_report.overall", "label": "x", "value": "pass" if rep.overall != "pass" else "fail"}]},
        "number": {"message": "This saves 4,321 yen.", "evidence": []},
        "must": {"message": "ok", "evidence": [{"kind": "preference", "reference": "preferences.must_visit", "label": "x", "value": ["Invented Place"]}]},
    }
    for name, c in cases.items():
        assert verify_evidence(c, res, rep, prefs, ds, prefs.days - 1), name


def test_every_answer_carries_structured_feasibility_and_solver_evidence():
    out = ask("EXPLAIN_PLAN")
    refs = {e["reference"] for e in out["evidence"]}
    assert {"feasibility_report.overall", "feasibility_report.checks", "feasibility_report.counts", "result.solver_meta.solver_status"} <= refs
    assert out["status"] in ("ok", "fallback") and out["status"] != "evidence_rejected"
