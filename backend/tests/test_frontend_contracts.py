"""Constants the frontend mirrors from the backend. If either side changes, this test fails so they cannot drift silently."""
import json
from pathlib import Path

from app import config

LIB = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib"


def test_day_part_mapping_matches_the_api():
    ui = {k: v for k, v in json.loads((LIB / "daypart.json").read_text()).items() if k != "note"}
    assert ui == config.DAY_PART_START_TIMES


def test_input_limit_and_operation_cap_match_the_backend_defaults(monkeypatch):
    monkeypatch.delenv("MAX_INPUT_CHARS", raising=False)
    ui = json.loads((LIB / "limits.json").read_text())
    assert ui["max_input_chars"] == config.get_settings().max_input_chars
    assert ui["max_replan_operations"] == config.MAX_REPLAN_OPERATIONS


def test_pace_caps_match_the_backend():
    ui = {k: v for k, v in json.loads((LIB / "pacecaps.json").read_text()).items() if k != "note"}
    assert ui == config.PACE_MAX_PER_DAY
