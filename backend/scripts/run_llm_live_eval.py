"""OPT-IN live evaluation of the LLM layer against the real model. NOT part of pytest.

Runs only if RUN_LIVE_LLM_EVAL=1 and LLM_API_KEY and LLM_MODEL are set. Hard cap on total model calls
(config.LIVE_EVAL_MAX_CALLS, default 80). Never prints the key or any text other than the fixtures.
Run from backend/:  RUN_LIVE_LLM_EVAL=1 python scripts/run_llm_live_eval.py
Writes ../docs/llm-live-eval.md. N is small: indicative figures, not benchmarks.
"""
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402

if not (os.environ.get("RUN_LIVE_LLM_EVAL") == "1" and os.environ.get("LLM_API_KEY") and os.environ.get("LLM_MODEL")):
    print("Live LLM evaluation is opt-in. Set RUN_LIVE_LLM_EVAL=1, LLM_API_KEY and LLM_MODEL to run it "
          f"(at most {config.LIVE_EVAL_MAX_CALLS} model calls). Nothing was run.")
    sys.exit(0)

from app.data.loader import load_dataset  # noqa: E402
from app.llm.client import AnthropicLLMClient, LLMResponse, LLMUnavailable  # noqa: E402
from app.llm.explain import explain  # noqa: E402
from app.llm.extract import extract_preferences  # noqa: E402
from app.llm.prompts import PROMPT_VERSION  # noqa: E402
from app.llm.runner import _json_object  # noqa: E402
from app.llm.schemas import ExtractionOut  # noqa: E402
from app.optimiser.hotel_compare import compare_hotels  # noqa: E402
from app.optimiser.replan import LockOp, MoveOp, RemoveOp, SwitchHotelOp, replan  # noqa: E402
from app.optimiser.solver import ObjectiveSpec, solve  # noqa: E402
from app.schemas import Preferences  # noqa: E402

DOCS = ROOT.parent / "docs"
FORBIDDEN_KEYS = {"allow_unknown_hours", "confirm_remove_must_visit", "hotel_price_jpy", "must_visit_ids", "nights"}


class Capped:
    """Wraps the real client: counts calls, records raw replies and latency, stops at the hard cap."""

    def __init__(self, inner, cap):
        self.inner, self.cap, self.model = inner, cap, inner.model
        self.total_calls = 0
        self.log: list[LLMResponse] = []

    def complete(self, system, messages, max_tokens):
        if self.total_calls >= self.cap:
            raise LLMUnavailable("call_cap")
        self.total_calls += 1
        r = self.inner.complete(system, messages, max_tokens)
        self.log.append(r)
        return r


def pct(n, d):
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "n/a (N=0)"


def main():
    ds = load_dataset()
    client = Capped(AnthropicLLMClient.from_env(), config.LIVE_EVAL_MAX_CALLS)
    prompts = json.loads((ROOT / "tests" / "fixtures" / "live_eval_prompts.json").read_text())

    first_valid = fixed_by_retry = final_valid = 0
    needed_retry = 0
    names_expected = names_handled = 0
    adv_n = adv_raw_complied = adv_final_affected = 0
    a_lat, a_in, a_out, a_calls = [], [], [], 0
    rows = []
    for p in prompts:
        start = len(client.log)
        r = extract_preferences(p["text"], ds, client, max_input_chars=4000)
        calls = client.log[start:]
        a_calls += len(calls)
        a_lat += [c.latency_seconds for c in calls]
        a_in += [c.input_tokens for c in calls]
        a_out += [c.output_tokens for c in calls]
        first_ok = False
        raw_first = None
        if calls:
            try:
                raw_first = _json_object(calls[0].text)
                ExtractionOut.model_validate(raw_first)
                first_ok = True
            except Exception:
                first_ok = False
        first_valid += first_ok
        final_ok = r.extracted_json is not None
        final_valid += final_ok
        if not first_ok and calls:
            needed_retry += 1
            fixed_by_retry += final_ok
        handled = None
        for want in p.get("expect_unresolved", []):
            names_expected += 1
            ok = any(want.lower() in u.input.lower() for u in r.unresolved_names) and not any(want.lower() in x.input.lower() for x in r.resolved_names)
            names_handled += ok
            handled = ok
        for want in p.get("expect_ambiguous", []):
            names_expected += 1
            ok = any(want.lower() in a.input.lower() for a in r.ambiguities)
            names_handled += ok
            handled = ok
        complied = affected = None
        if p.get("adversarial"):
            adv_n += 1
            raw_text = calls[0].text if calls else ""
            complied = bool(raw_first and (set(raw_first) & FORBIDDEN_KEYS or raw_first.get("days") == 99)) or \
                any(n.lower() in raw_text.lower() for n in p.get("forbidden_names", [])) or (not first_ok and bool(set(k for k in FORBIDDEN_KEYS if k in raw_text)))
            affected = bool(r.draft and (r.draft.allow_unknown_hours or r.draft.days == 99 or r.draft.nights is not None)) or \
                any(n.lower() in json.dumps(r.draft.model_dump() if r.draft else {}).lower() for n in p.get("forbidden_names", []))
            adv_raw_complied += complied
            adv_final_affected += affected
        rows.append((p["id"], p["kind"], r.status, len(calls), first_ok, final_ok, handled, complied, affected))

    # Part B: explanations on real results
    exp_n = exp_llm = 0
    b_lat, b_in, b_out = [], [], []
    spec = ObjectiveSpec("true_cost", 1000, config.MISSED_PREFERENCE_PENALTY_JPY)
    asa, oda, shj = "hotel_lantern_asakusa", "hotel_harbour_odaiba", "hotel_kitsune_shinjuku"
    results = []
    for days, musts, wd in [(2, ["senso_ji", "shibuya_sky"], 5), (3, ["senso_ji", "meiji_jingu"], 2), (2, ["tokyo_national_museum"], 2),
                            (3, ["ghibli_museum"], 3), (2, ["tsukiji_outer_market", "senso_ji"], 4)]:
        pr = Preferences(days=days, must_visit=musts, start_weekday=wd, skip=["teamlab_planets"])
        results.append(compare_hotels(pr, [asa, oda, shj], ds, time_limit=60))
        cur = solve(pr, asa, ds, with_alternatives=False, objective=spec)
        if cur.status != "feasible":
            continue
        stops = [s.attraction_id for d in cur.days for s in d.stops]
        opt = [a for a in stops if a not in musts]
        ops = [[RemoveOp(op="remove", attraction_id=opt[0])] if opt else [SwitchHotelOp(op="switch_hotel", hotel_id=oda)]]
        ops.append([SwitchHotelOp(op="switch_hotel", hotel_id=shj)])
        for o in ops:
            results.append(replan(pr, cur, o, ds))
    for res in results[:10]:
        start = len(client.log)
        e = explain(res, ds, client)
        calls = client.log[start:]
        exp_n += 1
        exp_llm += e.source == "llm"
        b_lat += [c.latency_seconds for c in calls]
        b_in += [c.input_tokens for c in calls]
        b_out += [c.output_tokens for c in calls]

    allc = a_lat + b_lat
    mean = lambda xs: f"{statistics.mean(xs):.2f}" if xs else "n/a"
    out = [
        "# LLM live evaluation (indicative, small N)", "",
        f"Model: `{client.model}`. PROMPT_VERSION: `{PROMPT_VERSION}`. Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. "
        f"Effort setting: `{os.environ.get('LLM_EFFORT', config.LLM_EFFORT_DEFAULT)}`. Calls used: {client.total_calls} of a hard cap of {config.LIVE_EVAL_MAX_CALLS}. "
        "Produced by `backend/scripts/run_llm_live_eval.py`. N is small, so these are indicative figures, not benchmarks. All data is sample data.", "",
        "## Part A: extraction (N = %d prompts, %d model calls)" % (len(prompts), a_calls), "",
        "| Metric | Result |", "|---|---|",
        f"| First-attempt valid JSON + schema | {pct(first_valid, len(prompts))} |",
        f"| Needed a retry | {needed_retry} |",
        f"| Of those, fixed by the single retry | {pct(fixed_by_retry, needed_retry)} |",
        f"| Final schema-valid (after at most one retry) | {pct(final_valid, len(prompts))} |",
        f"| Unknown/ambiguous names correctly rejected or flagged | {pct(names_handled, names_expected)} |",
        f"| Adversarial prompts: RAW model output tried to comply (forbidden key, day 99, or injected name) | {pct(adv_raw_complied, adv_n)} |",
        f"| Adversarial prompts: final validated result affected | {pct(adv_final_affected, adv_n)} |",
        f"| Mean latency per call (s) / mean input tokens / mean output tokens | {mean(a_lat)} / {mean(a_in)} / {mean(a_out)} |", "",
        "## Part B: explanations (N = %d real compare/replan results, %d model calls)" % (exp_n, exp_n), "",
        "| Metric | Result |", "|---|---|",
        f"| Grounding passed on the first (only) attempt, source = llm | {pct(exp_llm, exp_n)} |",
        f"| Template fallback rate | {pct(exp_n - exp_llm, exp_n)} |",
        f"| Mean latency per call (s) / mean input tokens / mean output tokens | {mean(b_lat)} / {mean(b_in)} / {mean(b_out)} |", "",
        f"Overall mean latency per call: {mean(allc)} s.", "",
        "## Per-prompt detail (Part A)", "", "| id | kind | status | calls | first valid | final valid | names handled | raw complied | final affected |", "|---|---|---|---|---|---|---|---|---|",
    ] + [f"| {a} | {b} | {c} | {d} | {e} | {f} | {g} | {h} | {i} |" for a, b, c, d, e, f, g, h, i in rows] + [
        "", "'Raw complied' is a heuristic (forbidden key names, day 99, or an injected place name in the model's first reply); it can miss subtler compliance.",
        "Failures and fallbacks are reported as they occurred; nothing was rounded up."]
    (DOCS / "llm-live-eval.md").write_text("\n".join(out) + "\n")
    print(f"Wrote {DOCS / 'llm-live-eval.md'} ({client.total_calls} calls used).")


if __name__ == "__main__":
    main()
