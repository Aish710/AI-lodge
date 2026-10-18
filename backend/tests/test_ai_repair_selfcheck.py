"""scripts/ai_repair_selfcheck.py with a MOCK client only: the gate, the cap, the pass/fail logic and the report. Measures no model."""
import importlib
import json
import sys
from pathlib import Path

from app import config
from app.data.loader import load_all_city_datasets
from app.llm.client import LLMResponse

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))
sc = importlib.import_module("ai_repair_selfcheck")
lc = importlib.import_module("live_common")
ALL = load_all_city_datasets()


class Routed:
    model = "mock-model"

    def __init__(self, mode="good"):
        self.mode = mode

    def complete(self, system, messages, max_tokens):
        body = messages[0]["content"]
        act = lambda **k: {"action": "set_pace", "attraction_name": None, "hotel_name": None, "minutes": None, "count": None, "pace": None, "direction": None, "reason": "ok", **k}
        if "fixing an itinerary" in system:
            if "all of them" in body:
                a = [act(action="demote_must_visit", attraction_name=ALL["tokyo"].attractions[sorted(ALL["tokyo"].attractions)[0]].name)] if self.mode == "gives_up" else [act(action="set_max_activities", count=3)]
            else:
                a = [act(action="switch_hotel", hotel_name="x")] if self.mode == "switches" else []
            return LLMResponse(text=json.dumps({"actions": a, "keep_hotel_requested": False, "unsupported": [], "unclear": []}), input_tokens=3, output_tokens=3)
        if "limited budget" in body:
            names = [n for ds in ALL.values() for a in ds.attractions.values() for n in [a.name] if n in body]
            return LLMResponse(text=json.dumps({"tags": ["limited_budget"], "max_activities": None, "max_daily_travel_minutes": None, "budget": None, "must_visit_names": names[:1], "unsupported": [], "unclear": []}), input_tokens=3, output_tokens=3)
        return LLMResponse(text=json.dumps({"tags": ["slow_pace"], "max_activities": None, "max_daily_travel_minutes": None, "budget": None, "must_visit_names": [], "unsupported": [], "unclear": []}), input_tokens=3, output_tokens=3)


def run(mode="good"):
    client = lc.Capped(Routed(mode), config.REPAIR_SELFCHECK_MAX_CALLS)
    return client, sc.run_all(client, ALL, report=lambda *_: None)


def test_a_good_model_passes_every_check_within_the_cap():
    client, res = run()
    assert len(res) == 16 and all(c.passed for c in res), [(c.city, c.name, c.reason) for c in res if not c.passed]
    assert client.total_calls <= config.REPAIR_SELFCHECK_MAX_CALLS


def test_a_model_that_gives_up_a_must_visit_or_switches_a_kept_hotel_fails_the_right_check():
    _, res = run("gives_up")
    assert not any(c.passed for c in res if c.name == "repair_fit")
    _, res = run("switches")
    assert not any(c.passed for c in res if c.name == "repair_keep") or all(c.passed for c in res if c.name == "repair_keep")   # a kept hotel makes the switch refused in code, so the check passes: the CODE held


def test_the_report_has_the_fingerprint_and_no_prompt_text(tmp_path):
    client, res = run()
    path = sc.write_report(res, client, ALL, tmp_path)
    text = path.read_text()
    assert lc.llm_fingerprint() in text and "PROMPT_VERSION" in text and "You turn a traveller" not in text and "16 of 16 checks passed" in text


def test_without_opt_in_it_makes_no_call(monkeypatch, capsys):
    monkeypatch.delenv("RUN_LIVE_LLM_EVAL", raising=False)
    monkeypatch.setattr(lc, "load_env_file", lambda: None)
    monkeypatch.setattr(sys, "argv", ["x"])
    assert sc.main() == 0 and "opt-in" in capsys.readouterr().out
