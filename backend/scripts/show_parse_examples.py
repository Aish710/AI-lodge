"""Print example /parse results produced by the real extraction code with a MOCK model (no network, no key), and write them as frontend test
fixtures. Run from backend/:  python scripts/show_parse_examples.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from app.data.loader import load_all_city_datasets  # noqa: E402
from app.llm.extract import extract_preferences  # noqa: E402
from llm_mock import MockLLM, extraction  # noqa: E402

ALL = load_all_city_datasets()
OUT = ROOT.parent / "frontend" / "tests" / "fixtures" / "parse-examples.json"


def run(city, text, *replies):
    return extract_preferences(text, ALL[city], MockLLM(list(replies)), all_datasets=ALL).model_dump()


examples = {
    "wrong_city_destination": {"selected_city": "seoul", "text": "3 days in Tokyo, see Senso-ji and Tokyo Skytree", "result": run("seoul", "3 days in Tokyo, see Senso-ji and Tokyo Skytree")},
    "ambiguous_cross_city_name": {"selected_city": "singapore", "text": "2 days, I want to see the market",
                                  "result": run("singapore", "2 days, I want to see the market", extraction(days=2, must_visit_names=["the market"]))},
    "ambiguous_in_selected_city": {"selected_city": "tokyo", "text": "2 days, I want to see the museum",
                                   "result": run("tokyo", "2 days, I want to see the museum", extraction(days=2, must_visit_names=["the museum"]))},
    "currency_confirmation": {"selected_city": "seoul", "text": "2 days in Seoul, budget ¥30000",
                              "result": run("seoul", "2 days in Seoul, budget ¥30000", extraction(days=2, budget={"amount": 30000, "currency": "¥", "strict": False}, destination_mentioned="Seoul"))},
    "unsupported_city": {"selected_city": "tokyo", "text": "a week in Bangkok", "result": run("tokyo", "a week in Bangkok", extraction(days=7, destination_mentioned="Bangkok"))},
}
OUT.write_text(json.dumps(examples, indent=1, ensure_ascii=False) + "\n")
for name, ex in examples.items():
    r = ex["result"]
    keep = {k: r[k] for k in ("status", "city_id", "draft", "call_count", "mode", "destination", "switch_offer", "currency_confirmations", "cross_city_hints", "unresolved_names", "ambiguities", "clarifications")}
    print(f"\n=== {name}: selected city = {ex['selected_city']}, user text = {ex['text']!r}")
    print(json.dumps(keep, indent=1, ensure_ascii=False))
