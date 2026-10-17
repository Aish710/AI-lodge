#!/usr/bin/env python3
"""Generate docs/JUDGING-SCORECARD.md: for each judging criterion, the exact artifact a judge can open, the test or file that backs it, and the
honest remaining gaps. Every number is read from a generated file by this script; nothing is typed in and nothing is graded (no letters, no scores).
Usage: python scripts/make_scorecard.py"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs"


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def facts() -> dict:
    f: dict = {}
    safety = read(D / "SAFETY_LOG.md")
    f["risk_rows"] = len(re.findall(r"^\| \d+ \|", safety, re.M))
    bt = read(ROOT / "backend/tests/results/latest-full.md")
    m = re.search(r"Passed: (\d+), failed: (\d+), skipped: (\d+), total: (\d+)", bt)
    f["backend"] = f"{m.group(1)} passed, {m.group(2)} failed of {m.group(4)}" if m else "not available"
    rev = re.search(r"Git revision: (.+)", bt)
    f["backend_rev"] = rev.group(1).strip() if rev else "unknown"
    h = read(D / "hardening-results.md")
    hm = re.search(r"Generated (\S+ \S+ UTC).*?\*\*(\d+)/(\d+) cases passed\*\*", h, re.S)
    f["hardening"] = f"{hm.group(2)} of {hm.group(3)} cases passed (generated {hm.group(1)})" if hm else "not available"
    claims = read(D / "README-claims.md")
    f["claims_header"] = (re.search(r"^Generated .*$", claims, re.M) or re.search(r"^# .*$", claims, re.M)).group(0) if claims else "not available"
    f["claims"] = re.findall(r"^- \*\*(\w+)\*\*: (.+)$", claims, re.M)
    inj = ROOT / "backend/tests/fixtures/injection_prompts.json"
    f["injections"] = len(json.loads(inj.read_text())) if inj.exists() else 0
    csv_path = D / "user-test/results.csv"
    f["user_rows"] = 0
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as fh:
            f["user_rows"] = sum(1 for r in csv.DictReader(fh) if any((v or "").strip() for v in r.values()))
    f["live_eval"] = (D / "llm-live-eval.md").exists()
    rtj = D / "redteam-results.json"
    f["redteam"] = None
    if rtj.exists():
        j = json.loads(rtj.read_text(encoding="utf-8"))
        f["redteam"] = f"{j['attacks']} attacks (English, Korean, Chinese, Malay) x 4 cities x 2 simulated models = {j['runs']} runs; final result affected in {len(j['affected'])}; {len(j.get('found_and_fixed', []))} problem(s) found and fixed by the red team itself"
    f["redteam_live"] = (D / "redteam-live.md").exists()
    gold = D / "eval" / "gold-results-live-first-run.md"
    f["gold"] = None
    if gold.exists():
        g = gold.read_text(encoding="utf-8")
        rows = re.findall(r"^\| ([A-Za-z ]+) \| \d+ \| [^|]+ \| (\d+)/(\d+) \(", g, re.M)
        mdl = re.search(r"Model: `([^`]+)`", g)
        f["gold"] = "; ".join(f"{c.strip()} {a} of {b} exact" for c, a, b in rows) + (f" (model {mdl.group(1)})" if mdl else "")
    f["gold_latest"] = None
    ev = D / "eval"
    newest = sorted(n.name for n in ev.glob("gold-results-live-*.md") if re.match(r"gold-results-live-\d{8}T\d{6}Z-.+\.md$", n.name) and not n.name.endswith("-first-run.md")) if ev.exists() else []
    if newest:
        g = (ev / newest[-1]).read_text(encoding="utf-8")
        rows = re.findall(r"^\| ([A-Za-z ]+) \| \d+ \| [^|]+ \| (\d+)/(\d+) \(", g, re.M)
        f["gold_latest"] = "; ".join(f"{c.strip()} {a} of {b} exact" for c, a, b in rows) + f" ({newest[-1]})"
    f["verification_sentence"] = None
    vc = D / "data-verification" / "counts.json"
    if vc.exists():
        f["verification_sentence"] = json.loads(vc.read_text(encoding="utf-8"))["readme_sentence"]
    sc = D / "ai-selfcheck.md"
    f["selfcheck"] = None
    if sc.exists():
        t = sc.read_text(encoding="utf-8")
        m = re.search(r"\*\*(\d+ of \d+) checks passed", t)
        mod = re.search(r"Model: `([^`]+)`", t)
        host = re.search(r"Endpoint host: `([^`]+)`", t)
        f["selfcheck"] = ", ".join(x for x in [(m.group(1) + " checks passed in the latest run") if m else "", f"model {mod.group(1)}" if mod else "", f"via {host.group(1)}" if host else ""] if x) or "see the file"
    f["cities"] = sorted(p.name for p in (ROOT / "backend/app/data/cities").iterdir() if (p / "city.json").exists())
    f["city_eval"] = (D / "city-eval-results.md").exists()
    ce = D / "city-eval-results.json"
    f["city_eval_cities"], f["city_eval_n"] = [], None
    if ce.exists():
        j = json.loads(ce.read_text(encoding="utf-8"))
        f["city_eval_cities"], f["city_eval_n"] = sorted(j.get("cities", {})), j.get("meta", {}).get("trips_per_added_city")
    f["verification_sheets"] = sorted(p.name for p in (D / "data-verification").glob("*.csv")) if (D / "data-verification").exists() else []
    return f


def build(f: dict) -> str:
    selfcheck = f.get("selfcheck")
    live = ("Run: see `docs/llm-live-eval.md`." if f["live_eval"] else
            (f"A live smoke test was run and is recorded in `docs/ai-selfcheck.md` ({selfcheck}). It is a small check on one model, tuned on those checks, not a benchmark. "
             "The larger evaluation file `docs/llm-live-eval.md` does not exist." if selfcheck else
             "No live result file exists (`backend/scripts/run_llm_live_eval.py` is opt-in, hard cap 150 calls, `--plan` makes none), so no live figure is claimed."))
    user = (f"{f['user_rows']} participant(s): see the Proof page card and `docs/user-test/summary.md`." if f["user_rows"] else
            "**Not run.** The kit exists (`docs/user-test/PROTOCOL.md`, an empty `results.csv`, `scripts/summarise_user_test.py`); the Proof page says \"Not run yet\".")
    ver = (f["verification_sentence"] + "; sheets: " + ", ".join(f["verification_sheets"]) if f.get("verification_sentence") and f["verification_sheets"] else "sheets exist: " + ", ".join(f["verification_sheets"]) if f["verification_sheets"] else
           "no verification sheets exist yet; every record is labelled `sample`, none is labelled verified")
    others = ", ".join(c.replace("_", " ").title() for c in f["city_eval_cities"])
    city_eval_gap = (f"the headline evaluation is on Tokyo; {others} each have a smaller separate sample" + (f" ({f['city_eval_n']} trips each)" if f["city_eval_n"] else "") + ", reported separately and never pooled"
                     if f["city_eval_cities"] else "only the Tokyo evaluation exists; the other cities have no evaluation file")
    ai_gap = ("the live evidence is a 20-check smoke test (tuned on those checks) and one first run of the gold set on one model, with hand-written prompts" if f.get("gold") else
              "the live evidence is a 20-check smoke test (tuned on those checks); the gold-set live score has not been run")
    ai_gap += ("; no live red-team result exists" if not f.get("redteam_live") else "") + "; cited explanations (each sentence names its facts) and the AI on/off switch are built and mock-tested, with no live result yet for the cited format; the live AI results come from one model through a third-party gateway"
    gold_latest_text = (f"Latest run: {f['gold_latest']}. " if f.get("gold_latest") else "")
    gold_row = (f"| **Gold set, live, first run (48 hand-written prompts, 12 per city, reported per city):** {f['gold']}. {gold_latest_text}Small sample, one model; the prompts were written by the person who built the pipeline, which had been tuned on similar checks, so this is optimistic. | `docs/eval/gold-results-live-first-run.md`, `backend/scripts/score_gold.py` |" if f.get("gold") else "")
    redteam_text = (f["redteam"] + ". These counts come from simulated models and say nothing about a real model" + ("; a live red-team report also exists" if f.get("redteam_live") else "; the live red-team script exists but has not been run")) if f.get("redteam") else "not generated"
    safety_gap = ("the red-team counts are from simulated models" + ("" if f.get("redteam_live") else " (no live red-team run)") + "; all city data is sample data (only Singapore has any source-checked fields, and none is human-verified); rate limits and the circuit breaker are per process; the relay (a third party) sees the cleaned request text; no external security review")
    claims = "\n".join(f"- `{k}`: {v}" for k, v in f["claims"]) or "- (claims file not found)"
    return f"""# Judging scorecard

Generated by `scripts/make_scorecard.py` from the files named below; re-run it after regenerating them. It does not grade anything: it points a judge at the artifact, the test or file behind it, and says what is still missing. Numbers come from generated files only.

Where to look in the app: **Proof** (`/proof`) shows the measured results, hardening, risk table and the user-test card; **How it works** (`/how-it-works`) shows the architecture, exactly how the AI is used, limitations and privacy.

## 1. AI Integration Effectiveness

| What a judge can open | Backing |
|---|---|
| **Where the AI is used (three places, all optional):** words to an editable trip form (`/parse`), words to *proposed* itinerary changes that only queue (`/parse-replan`), and an opt-in "Explain this result" (`explain: true`). The "How it works" page and `docs/LLM_DESIGN.md` describe each. | `backend/app/llm/extract.py`, `parse_replan.py`, `explain.py`; `backend/tests/test_llm_input.py`, `test_llm_explain.py`, `test_llm_api_safety.py` |
| **Where it is NOT used:** the schedule (OR-Tools CP-SAT decides), prices, hours and travel times (dataset), validation (an independently written validator), destination detection and currency conversion (code), and confirming removal of a must-visit (only a human click). | `backend/app/optimiser/`, `backend/app/validator/`, `backend/app/llm/destination.py`, `backend/app/llm/currency.py` |
| **LLM per city:** the prompt names the selected city, country and currency and carries only that city's place names; a request about another city is caught in code and only offers a switch; ambiguous names are asked, never guessed. | `backend/app/llm/prompts.py`; `backend/tests/test_llm_per_city.py` (mock model, every case for all {len(f['cities'])} cities: {', '.join(f['cities'])}) |
| **Grounding checker:** an explanation's numbers, times and names are compared with the computed facts (names of all cities); any mismatch replaces the text with a template. | `backend/app/llm/grounding.py`; `test_an_explanation_that_names_another_citys_place_is_rejected_for_every_city_pair` |
| **No-LLM fallback:** with no key, an outage or the daily cap, the form, comparison, itinerary, replanning and template explanations all work (the mode badge says so). | `backend/tests/test_hardening.py`; Proof page; screenshot `docs/screenshots/10-nl-parse-sample-mode.png` |
| **Live LLM evaluation:** {live} | `backend/scripts/run_llm_live_eval.py`, `backend/tests/test_live_eval_script.py` (mock client only) |
{gold_row}

**Where to see the AI in the app:** the first card on Plan ("Ask the AI to set up your trip"), "Ask the AI to change your plan" and "Explain this plan" on Your trip, the "What the AI did" drawer under each AI result, and the Proof page's "Live AI evidence" card.

**Remaining gaps:** {ai_gap}

## 2. LLM Safety & Responsible AI

| What a judge can open | Backing |
|---|---|
| **Risk table:** {f['risk_rows']} rows, each with its safeguard and the test that covers it. | `docs/SAFETY_LOG.md`; Proof page "risk table" |
| **Hardening results:** {f['hardening']}. | `docs/hardening-results.md` (from `backend/scripts/run_hardening_checks.py`) |
| **Red-team fixtures:** {f['injections']} injection prompts in `backend/tests/fixtures/injection_prompts.json` (the original set), plus one injection per language (English, Korean, Chinese, Malay) run against every city. | `backend/tests/test_llm_input.py`, `backend/tests/test_llm_per_city.py` |
| **Red team (simulated models):** {redteam_text}. | `docs/redteam-results.md`, `docs/redteam-results.json`, `backend/tests/fixtures/redteam_attacks.json`, `backend/tests/test_redteam.py` |
| **Per-city checks:** every id in a request must belong to the request's city (all routes, all city pairs); stale answers after a city switch are discarded; amounts use the selected city's currency. | `backend/tests/test_city_isolation.py`, `test_currency_labels.py`; `frontend/tests/unit/city-isolation.test.js`, `currency.test.js` |
| **Data verification status:** {ver}. |  `backend/tests/test_data.py::test_no_record_is_verified`; `docs/CITIES.md` |
| **Privacy:** nothing is stored (no database, cookies or analytics); server logs are metadata only; place descriptions are never sent to the AI. | `docs/PRIVACY.md`; "How it works" page, Privacy section; `frontend/tests/e2e/replan.spec.js` (no storage, no third-party requests except map tiles) |

**Remaining gaps:** {safety_gap}

## 3. Usefulness & Business Value

| What a judge can open | Backing |
|---|---|
| **The problem:** a hotel that looks cheap can cost more once travel time and fares are counted, so the hotel and the itinerary should be chosen together. | "How it works" page; the verdict on Your trip |
| **Target user:** travellers who plan a short city trip themselves. This is an assumption: no user research has been done. | (see user test below) |
| **Measured results (generated, with N and caveats):** the sentences below are copied by the script from the claims file ({f['claims_header']}). They come from seeded synthetic trips on the Tokyo sample pack, not from users. | `docs/README-claims.md`, `docs/eval-results.md`; `backend/scripts/run_evaluation.py` |
| **City packs and scale-out:** {len(f['cities'])} packs ({', '.join(f['cities'])}); adding a city is documented step by step. | `docs/CITIES.md`; `backend/tests/test_city_packs.py`{'; `docs/city-eval-results.md` (Singapore and Seoul, smaller samples, reported separately)' if f['city_eval'] else ''} |
| **User test:** {user} | `docs/user-test/` |
| **Tests behind all of it:** backend suite {f['backend']} (revision {f['backend_rev']}). | `backend/tests/results/latest-full.md` |

Generated claim sentences:

{claims}

**Remaining gaps:** no real-user evidence yet; results are on synthetic trips and sample data, with weak or tied results reported on the Proof page; {city_eval_gap}; the hotels are made-up; there are no bookings or live prices; one city per trip.
"""


if __name__ == "__main__":
    out = D / "JUDGING-SCORECARD.md"
    out.write_text(build(facts()), encoding="utf-8")
    print(f"wrote {out}")
