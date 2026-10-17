# Fitinerary

**Choose a hotel based on the trip it makes possible, then build a feasible itinerary around it.**

> **Data notice.** Four cities (Tokyo, Singapore, Seoul, Kuala Lumpur) of **sample data**: made-up demo hotels, estimated travel times and fares, not live prices, public holidays not modelled. Singapore: 7 fields source-checked, 0 rows human-verified, 75 unchecked; other cities unchecked; all data is still sample data. (Generated: `docs/data-verification/counts.md`.)

[PLACEHOLDER: live app URL] · [PLACEHOLDER: backend URL] · [PLACEHOLDER: demo video link] · Source: https://github.com/Aish710/AI-lodge

## 1. Problem Statement

Planning a city trip is not just picking attractions. The hotel changes the travel time, the transport cost and what can realistically fit into each day, and a hotel that looks cheap per night can cost more once travel time and fares are counted. Most planners treat the hotel and the itinerary as two separate decisions. Fitinerary chooses them together and shows its working.

**Who it is for and why it matters.** The target user is a traveller, often budget-conscious or a student, who plans a short city trip on their own and has to choose a hotel before knowing how the days will go. What they get: a hotel comparison by *true cost* (room, admissions, estimated transport, and the value of their travel time), a day-by-day itinerary that an independent validator has checked, and a plain statement of what could not fit and why. The honest limits: the data is sample data, the hotels are made up, no user study has been run, and on random trips the cheapest hotel is usually also the best one (see the evaluation below), so the value is in the trips where it is not. No statistics about real travellers are claimed.

## 2. Solution Overview

Fitinerary is a Vue frontend plus a FastAPI backend. The pipeline is:

```
 your words (optional)        sanitise -> LLM extracts a draft -> code validates it -> you edit the form
 your form / choices  ---->   OR-Tools CP-SAT optimiser (fixed seed) ---->  independent validator
                                                                              |
                          LLM explains the computed facts (optional) <---- computed result
                          code checks every number and name in the explanation, else a template is shown
```

- The **optimiser** (OR-Tools CP-SAT) makes every planning decision: which hotel, which sights, in what order. It is never the language model.
- An **independent validator** re-checks every rule on the finished plan (opening hours, travel gaps, overlaps, budget, locked stops, must-visits).
- The **language model** only works at the edges, only when you click: it reads your words into an editable form, proposes changes that you must apply yourself, and words short explanations of numbers the code already computed.
- Without an AI key the whole app works (form, comparison, plan, replanning, template explanations): the header says "AI off".

## 3. Key Features

- **One click from choices to plan.** "Plan my trip" compares the hotels, picks the best by true cost, plans the days and lands on "Your trip" (2 clicks from the example, measured in `docs/ux-metrics.md`; machine-dependent).
- **Hotel comparison by true cost**, with a plain verdict, the full breakdown, and a sensitivity analysis of the value of an hour of your time (runs only when you click).
- **Itinerary with a feasibility report** and a cost panel (admissions, estimated transport, rooms, unknown prices listed, never counted as zero), day cards, travel connectors labelled "estimated", and a filterable map.
- **Replanning** that queues edits, asks before removing a must-visit, and shows an explicit before/after diff.
- **Four cities**, one city per trip; switching asks first and clears everything.
- **AI that shows its working:** AI and "Calculated" markers, "What the AI understood", a "What the AI did" drawer, a header popover saying what the AI does and never does.
- **A Proof page** generated from repository files: evaluation, hardening, test results, the safety risk table, live AI evidence with its run history, a simulated red-team table, data-verification counts.
- Keyboard-accessible controls (Lighthouse accessibility 100 on all three audited pages).

## 4. AI Integration

The AI is used in three places, all optional, all on an explicit click (`docs/LLM_DESIGN.md`, "How it works" page):

1. **Ask the AI to set up your trip** (`/parse`): your words become a draft of the form. The model returns strict JSON; code then resolves place names, decides whether the request is about the selected city (another city only produces a "Switch to…" offer; nothing is planned), converts currencies (an ambiguous `$` is always confirmed with you) and fills defaults, listing every assumption.
2. **Ask the AI to change your plan** (`/parse-replan`): words become *proposed* operations that only join a pending list. Removing a must-visit needs your explicit confirmation, which the model can never set.
3. **Explain this plan** (`explain`): the model gets only computed facts (never place descriptions). A grounding checker compares every number, time and name in its text with the facts; a mismatch replaces the text with a template. Planner warnings are added by code, verbatim.

Around it: input sanitising, user text treated as data inside one delimited block, a leak guard on everything the model writes, per-call caps, a daily circuit breaker, rate limits. The key stays on the server.

**What was measured with a real model, and what was not** (all one model, `claude-haiku-4-5-20251001`, through a third-party gateway, `api.apiyi.com`; the cleaned text and computed facts pass through that gateway):

| What | Result | Read it as |
|---|---|---|
| 20-check smoke test (`docs/ai-selfcheck.md`, run history in `docs/ai-selfcheck-history.md`) | 20 of 20 in the latest run, and in every run since the last fix; earlier runs failed 4, 2 and 1 checks and stopped at the first call, and each root cause was fixed | Tuned on these checks: it shows the found problems are fixed, not accuracy on unseen requests |
| Gold set, 48 hand-written prompts, 12 per city (`docs/eval/gold-results-live-first-run.md`, then `docs/eval/gold-results-live-20261017T170803Z-final.md` and `docs/eval/gold-results-live-20261017T183746Z-final2.md`) | First run 48 of 48 exact; two later runs on later code, 48 of 48 exact each | Optimistic: the prompts were written by the builder, the pipeline had been tuned on similar checks, and many fields (the wrong-city stop, name matching) are decided by code, not the model |
| Live red team, 27 attacks, run twice (`docs/redteam-live-first-run.md`, then `docs/redteam-live.md` after the fix) | First run: the raw reply tried to comply in 3 of 27 and the final result was affected in 2 of 27 (a currency attack left a yen-scale default in the form). After the fix, same 27 attacks: the raw reply tried to comply in 3 of 27 and the final result was affected in 0 of 27 | Two runs, one model, 27 attacks: indicative. The fix was reproduced with a mock first |

**Only tested with a mocked model:** the cited-explanation idea (not built), the 744-run red team (`docs/redteam-results.md`, simulated models, not a real model), every pipeline test in `backend/tests`. Not measured at all: any second model, any user study, how the AI performs on requests it was not tuned on.

## 5. External Tools & Datasets

- Backend: Python 3.13, FastAPI, Pydantic v2 (strict), OR-Tools CP-SAT, the `anthropic` SDK, pytest.
- Frontend: Vue 3, Vue Router, Vite, Bootstrap, Leaflet with OpenStreetMap tiles (a one-tile probe falls back to a plain background if the tile server refuses), Vitest, Playwright, Lighthouse.
- **Model and gateway:** `claude-haiku-4-5-20251001` reached through the third-party gateway `api.apiyi.com` (set with `LLM_BASE_URL`). The gateway sees the cleaned request text and the computed facts (`docs/PRIVACY.md`). Without `LLM_BASE_URL` the backend calls the provider directly.
- **Data:** hand-built sample attractions and made-up hotels for four cities (`backend/app/data/cities/`), with a travel-time matrix estimated from straight-line distance (`backend/scripts/build_travel_matrix.py`). Every record is labelled `sample`. Singapore has per-field verification records (7 fields checked against official pages, with URL and date, in `docs/data-verification/singapore-findings.json`); nothing is human-verified. Three Singapore opening-hours values were corrected from official pages (`docs/data-verification/CHANGELOG.md`).
- The AI-free evaluation method is in `docs/EVALUATION.md`.

## 6. Installation & Setup

Requires Python 3.13 and Node 22.

```bash
# backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --port 8000        # sample mode: no key needed

# frontend (second terminal)
cd frontend
npm install
printf 'VITE_API_BASE_URL=http://localhost:8000\n' > .env
npm run dev                                       # http://localhost:5173
```

To turn the AI on, copy `backend/.env.example` to `backend/.env` (it is gitignored; never commit it), set `LLM_API_KEY` and `LLM_MODEL` (and `LLM_BASE_URL` only for a gateway), and restart. Leave `LLM_EFFORT` unset.

Checks:

```bash
cd backend && .venv/bin/python -m pytest              # full suite
cd frontend && npm test                               # Vitest
cd frontend && npm run e2e                            # Playwright (builds the app, starts a sample-mode backend)
cd backend && .venv/bin/python scripts/run_hardening_checks.py
cd backend && .venv/bin/python scripts/run_evaluation.py --full
cd frontend && npm run verify:clean-clone             # clone, build and test from a clean checkout
```

Opt-in live checks (each needs a key and spends model calls, capped): `RUN_LIVE_LLM_EVAL=1 .venv/bin/python scripts/ai_selfcheck.py`, `scripts/score_gold.py --live --label NAME`, `scripts/redteam_live.py`. Deployment (Render and Netlify), environment variables, smoke tests: `docs/DEPLOY.md`.

## 7. AI Safety & Limitations

**Risk, safeguard, test** (146 risks in `docs/SAFETY_LOG.md`, each with its test; the main ones):

| Risk | Safeguard | Test |
|---|---|---|
| Prompt injection via the user's text | One delimited data block that text cannot close; instructions are a fixed constant; the model has no tools and cannot set safety flags | `backend/tests/test_llm_input.py`, `test_redteam.py` |
| The model leaks the system prompt, a key or another user's data | A leak guard drops any model string that quotes the prompt or holds a key, email or phone number | `test_redteam.py` (with a mutation check) |
| The model invents a number, place or price | Strict schemas; names resolved in code; every number and name in an explanation checked against computed facts; template fallback | `test_llm_explain.py`, `test_llm_per_city.py` |
| A request about the wrong city is planned | A code-side destination check before any model call; only a switch offer, confirmed by you | `test_city_packs.py`, `test_city_isolation.py` |
| The model removes a must-visit | Only your confirmation dialog can set the flag | `test_replan.py`, `replan.spec.js` |
| Cost runaway or abuse | Per-call caps, a daily circuit breaker, rate limits (6, 30 and 120 a minute by tier), a solver slot that frees when a client leaves | `test_hardening.py`, `test_solver_disconnect.py` |
| Data looks verified when it is not | `source_status` is `sample` on every record; per-field verification records need an official URL and a date | `test_verification.py` |

**Results (all with the caveats above).** Simulated red team (`docs/redteam-results.md`, simulated models, not a real model): 48 attacks in English, Korean, Chinese and Malay, 744 runs, final result affected in 0 after 3 fixes found by the red team itself. Live red team: 2 of 27 affected before the last fix, 0 of 27 after it (section 4). Hardening: 33 of 33 in-process abuse cases pass. Tests: 642 backend, 261 Vitest, 55 Playwright (Chromium), all passing at the commit named in `docs/EVIDENCE-STATUS.md`.

**Evaluation (no language model involved, seeded synthetic trips on sample data).** Across 15 comparable trips of 60, optimised routes used a mean of 14.1% less travel time than an input-order baseline (8.4% less than nearest-neighbour on 18 trips). The independent validator passed 53 of 53 plans. The lowest-rate hotel was not the best by true cost in 4 of 52 trips at the default value of time, and in 10 of 52 when an hour of time is valued at 2,000 yen. The hotels and rates are fictional and were tuned for the demo; this measures the model's behaviour on sample data, not hotel markets (`docs/eval-results.md`).

**Limitations.** Sample data only; hotels are made up; no live prices, holidays or transit; travel times are estimates (one transport mode is never named because the data has none). Two Singapore closing days (the Buddha Tooth Relic Temple on Mondays, the ArtScience Museum on Wednesdays) are unverified and probably wrong. No user study has been run. All live AI evidence is one model through a third-party gateway and is optimistic. Interests only highlight sights; the planner uses your Must / Include / Skip choices. Rate limits and the circuit breaker are per process.

**Privacy.** Nothing is stored: no database, cookies, analytics or browser storage. Server logs hold metadata only. Place descriptions are never sent to the model. If the AI is on, your cleaned request text and the computed facts leave the server for the gateway named above and the model provider (`docs/PRIVACY.md`).

## Screenshots

`docs/screenshots/steps/` (Kuala Lumpur and Seoul, desktop and mobile). Files named `*-ai-canned-*` show the interface with canned responses only; they are not evidence of model behaviour.

## Future improvements

Cited explanations (each sentence tied to the facts that support it), an AI on/off comparison view, click counts for all four cities, a user test with the kit in `docs/user-test/`, human verification of the data sheets in `docs/data-verification/`, a second model for the live checks.

## Licence

[PLACEHOLDER: licence]
