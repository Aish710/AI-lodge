"""Field-level accuracy on the hand-written gold set (docs/eval/gold-prompts.json), PER CITY (12 prompts each; never pooled).

  Default (no key, zero model calls):   python scripts/score_gold.py
      scores a deterministic RULE-BASED STAND-IN for the model (regexes and alias scanning). It is a floor/reference that exercises the same
      validation pipeline; it says NOTHING about any language model. Writes docs/eval/gold-results-mock.md.
  Live (opt-in):  RUN_LIVE_LLM_EVAL=1 python scripts/score_gold.py --live       (needs LLM_API_KEY and LLM_MODEL; hard cap config.GOLD_MAX_CALLS)
      scores the real model through the same pipeline. Writes docs/eval/gold-results-live.md. Nothing is written if the run is aborted.
Output folder override (tests): GOLD_OUT_DIR. The key and the prompts' replies are never printed or stored.
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import live_common as lc  # noqa: E402
from app import config  # noqa: E402
from app.llm.client import LLMResponse  # noqa: E402
from app.llm.extract import extract_preferences  # noqa: E402
from app.llm.prompts import PROMPT_VERSION  # noqa: E402
from llm_mock_baseline import RuleBasedBaseline  # noqa: E402

GOLD = lc.REPO / "docs" / "eval" / "gold-prompts.json"
CITIES = ("tokyo", "singapore", "seoul", "kuala_lumpur")
KINDS = ("typical", "vague", "wrong_city", "mixed_language", "ambiguous", "adversarial")
FIELDS = ("draft", "days", "pace", "budget", "must_visit", "skip", "destination", "ambiguous", "currency_confirmation", "injection_blocked")


def load_gold() -> list[dict]:
    return json.loads(GOLD.read_text(encoding="utf-8"))["prompts"]


def observe(r, ds) -> dict:
    """The facts about a ParseResult that the gold file can talk about."""
    d = r.draft
    dest = r.destination or {}
    if dest.get("status") == "unsupported":
        destination = "unsupported"
    elif dest.get("status") in ("other_city", "mixed"):
        destination = "other_city:" + str((r.switch_offer or {}).get("city_id"))
    else:
        destination = "ok"
    return {
        "draft": d is not None,
        "days": d.days if d else None,
        "pace": d.pace if d else None,
        "budget": d.budget if d else None,
        "must_visit": sorted(d.must_visit) if d else [],
        "skip": sorted(d.skip) if d else [],
        "destination": destination,
        "ambiguous_inputs": [a.input.lower() for a in r.ambiguities],
        "currency_confirmation": bool(r.currency_confirmations),
        "injection_blocked": d is None or (d.days <= 7 and not d.allow_unknown_hours and d.nights is None
                                           and set(d.must_visit) | set(d.skip) <= set(ds.attractions)),
    }


def compare(expected: dict, seen: dict) -> dict[str, bool]:
    out = {}
    for f, want in expected.items():
        if f == "ambiguous":
            out[f] = all(any(w.lower() in got for got in seen["ambiguous_inputs"]) for w in want)
        elif f in ("must_visit", "skip"):
            out[f] = seen[f] == sorted(want)
        else:
            out[f] = seen[f] == want
    return out


def score(client, all_ds, prompts=None, report=lambda *_: None) -> dict:
    prompts = prompts or load_gold()
    res: dict = {c: {"prompts": 0, "fields": 0, "fields_ok": 0, "exact": 0, "kinds": defaultdict(lambda: [0, 0]), "failed": [], "calls": 0} for c in CITIES}
    for p in prompts:
        c, ds = p["city"], all_ds[p["city"]]
        before = getattr(client, "total_calls", 0)
        r = extract_preferences(p["text"], ds, client, max_input_chars=4000, all_datasets=all_ds)
        seen = observe(r, ds)
        cmp = compare(p["expected"], seen)
        t = res[c]
        t["prompts"] += 1
        t["calls"] += getattr(client, "total_calls", 0) - before
        t["fields"] += len(cmp)
        t["fields_ok"] += sum(cmp.values())
        t["kinds"][p["kind"]][0] += sum(cmp.values())
        t["kinds"][p["kind"]][1] += len(cmp)
        if all(cmp.values()):
            t["exact"] += 1
        else:
            t["failed"].append((p["id"], [f for f, ok in cmp.items() if not ok]))
        report(f"{'ok  ' if all(cmp.values()) else 'MISS'} {p['id']}" + ("" if all(cmp.values()) else f"  wrong: {', '.join(f for f, ok in cmp.items() if not ok)}"))
    return res


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"


def render(res: dict, all_ds, *, label: str, model: str, calls: int | None) -> str:
    live = calls is not None
    head = ["# Gold-set field accuracy, per city " + ("(LIVE model)" if live else "(MOCK rule-based baseline: not a model)"), ""]
    if live:
        head.append(f"Model: `{model}`. PROMPT_VERSION: `{PROMPT_VERSION}`. Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. Git: `{lc.git_hash()}`. "
                    f"Calls used: {calls} of a hard cap of {config.GOLD_MAX_CALLS}. Produced by `backend/scripts/score_gold.py --live`.")
    else:
        head.append(f"Scorer: `{model}`. PROMPT_VERSION: `{PROMPT_VERSION}`. Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. Git: `{lc.git_hash()}`. Zero model calls. "
                    "Produced by `backend/scripts/score_gold.py`. This baseline is a deterministic stand-in made of regexes and alias scanning. It shows that the scoring and the validation pipeline work "
                    "and gives a floor to compare a model against. It is NOT a measurement of any language model.")
    head += ["", "Gold set: `docs/eval/gold-prompts.json`, 12 hand-written prompts per city (2 each of typical, vague, wrong-city, mixed-language, ambiguous, adversarial). "
             "Small N: each cell is indicative, and cities are reported separately, never pooled. Field accuracy counts each scored field of each prompt once; "
             "a prompt is exact only if all its scored fields are right.", ""]
    rows = ["| City | Prompts (N) | Field accuracy | Exact prompts | " + " | ".join(KINDS) + " |", "|---|---|---|---|" + "---|" * len(KINDS)]
    for c in CITIES:
        t = res[c]
        rows.append(f"| {all_ds[c].city.display_name} | {t['prompts']} | {pct(t['fields_ok'], t['fields'])} | {pct(t['exact'], t['prompts'])} | "
                    + " | ".join(pct(*t["kinds"][k]) for k in KINDS) + " |")
    miss = ["", "## Prompts with at least one wrong field", "", "| Prompt | Wrong fields |", "|---|---|"]
    miss += [f"| {i} | {', '.join(f)} |" for c in CITIES for i, f in res[c]["failed"]] or ["| none | |"]
    return "\n".join(head + rows + miss) + "\n"


def main() -> int:
    live = "--live" in sys.argv
    out_dir = Path(os.environ.get("GOLD_OUT_DIR") or lc.REPO / "docs" / "eval")
    from app.data.loader import load_all_city_datasets
    all_ds = load_all_city_datasets()
    if not live:
        res = score(RuleBasedBaseline(all_ds), all_ds, report=print)
        path = out_dir / "gold-results-mock.md"
        path.write_text(render(res, all_ds, label="mock", model="rule-based baseline v1", calls=None))
        print(f"\nWrote {path}. Live scoring was not run (use --live with RUN_LIVE_LLM_EVAL=1).")
        return 0
    lc.load_env_file()
    msg = lc.gate("scripts/score_gold.py --live", config.GOLD_MAX_CALLS)
    if msg:
        print(msg)
        return 0
    from app.llm.client import AnthropicLLMClient

    client = lc.Capped(AnthropicLLMClient.from_env(), config.GOLD_MAX_CALLS)
    try:
        res = score(client, all_ds, report=print)
    except lc.RunAborted as e:
        print(f"\nStopped after {client.total_calls} call(s): {e}\nNo results were written.")
        return 2
    path = out_dir / "gold-results-live.md"
    path.write_text(render(res, all_ds, label="live", model=client.model, calls=client.total_calls))
    print(f"\nWrote {path} ({client.total_calls} model call(s) used).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
