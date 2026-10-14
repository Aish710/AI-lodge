# Status audit (Phase 9c, Part 0)

Read-only audit written 2026-10-14 at git `f5a5b0a` plus uncommitted work. Nothing was changed except this file. No tests were run for this audit (a partial pytest run overwrites evidence files); counts come from the generated result files and from runs earlier today, as stated per row.

Caveat on prompts A to E: their full text is not in this repository, so each is mapped to the artifacts that match its description in the brief. Where the match is a judgement, the row says so.

## 1. Phases and prompts

| Item | Status | Evidence |
|---|---|---|
| Phase 1: backend skeleton, honest data | DONE | `backend/app/data/`, `tests/test_data.py` (`test_no_record_is_verified`, `test_hotel_names_are_marked_fictional`), BUILD_NOTES Phase 1 |
| Phase 2: solver, baseline, validator | DONE | `backend/app/optimiser/`, `validator/`, `tests/test_solver.py` (31 tests), `docs/SOLVER_DESIGN.md` |
| Phase 3: hotel comparison | DONE | `tests/test_hotel_compare.py` (25), `docs/hotel-comparison-results.md` |
| Phase 4: replanning | DONE | `tests/test_replan.py` (28), `docs/replan-results.md` |
| Phase 5: LLM layer | DONE (mocked tests only) | `tests/test_llm_input.py` (32), `test_llm_explain.py` (16), `test_llm_api_safety.py` (14), `docs/LLM_DESIGN.md`. The live model has never been called. |
| Phase 6: API hardening | DONE | `tests/test_hardening.py` (36), `docs/hardening-results.md` (33/33, generated 01:52 UTC, **older than the multi-city and solver-capacity changes: re-run needed**) |
| Phase 7: reproducible evaluation | PARTIAL | `docs/eval-results.md/json`, `tests/test_evaluation.py` (31). Evidence says code version `859c357 + uncommitted changes`, which is **not HEAD**, so `validate-release.mjs` would reject it. Re-run needed. |
| Phase 8 Milestone A: frontend core | DONE | `frontend/src/`, screenshots 01 to 05, 07 to 09 |
| Phase 8 Milestone B: replan UI, NL, explain, evidence | DONE | screenshots 06, 08, 10, 11; `tests/e2e/replan.spec.js`; SAFETY_LOG rows 75 to 83 |
| Prompt A: fixes and release safety | DONE | SAFETY_LOG rows 84 to 88. `tests/test_solver_capacity.py` (3), `frontend/scripts/validate-release.mjs`, `tests/unit/release.test.js`, `build:release` script |
| Prompt B: city packs | DONE for 4 cities, data unverified | `backend/app/data/cities/`, `tests/test_city_packs.py` (8), `docs/CITIES.md`, `docs/city-eval-results.md`, SAFETY_LOG rows 90 to 95 |
| Prompt C: flow and Proof / How-it-works pages | NOT DONE (judgement) | Nav and routes still say "Evidence" and "About" (`frontend/src/router.js:10-11`, `App.vue:35-36`). No "Proof" or "How it works" page exists. |
| Prompt D: submission drafts | PARTIAL | `README.md`, `docs/submission/devpost.md`, `linkedin.md` exist; `FINAL-AUDIT.md` still has unchecked boxes (demo link, live link, personal placeholders) |
| Prompt E: live verification | NOT DONE | Nothing is deployed (`FINAL-AUDIT.md` "Working Deployed URL" all unchecked). `scripts/live-smoke.mjs` exists but has only been run against a local pair. |

## 2. Specific checks

| Question | Answer | Evidence |
|---|---|---|
| Which cities exist? | Tokyo (12 attractions), Singapore (10), Seoul (10), Kuala Lumpur (10), 3 fictional hotels each | `GET /data/cities`; `backend/app/data/cities/{tokyo,singapore,seoul,kuala_lumpur}` |
| Is Shanghai present? WGS-84 checked? | **No. Shanghai is absent** (a repo-wide search finds nothing), so there is no Shanghai data and no WGS-84/GCJ-02 check. Coordinates for existing cities are bounding-box checked only (`test_city_packs_have_required_sample_integrity`). | grep of repository |
| Busy-state concurrency | DONE | `backend/app/hardening/solver_capacity.py`, default 1 concurrent solve, `503 solver_busy` with `Retry-After`; SAFETY_LOG row 84; `tests/test_solver_capacity.py` (3) |
| Full-suite evidence guard | DONE, but not a `full-suite.json` file | The guard is `latest-full.md`: written only for an unfiltered run; `sync-evidence.mjs --strict` requires it (`test_evidence_requires_full_backend_suite`, SAFETY_LOG row 85). No file named `full-suite.json` exists. |
| `build:release` guards | DONE | `package.json` script runs strict sync, build, host config, `validate-release.mjs` (HTTPS non-local API, required evidence files, evaluation commit equals HEAD, secret patterns in `dist`). Not run end to end today; it would currently fail on the stale evaluation commit. |
| Keyboard-focusable map pins | DONE in code; PARTIAL in tests | `TripMap.vue` markers use `keyboard: true`. SAFETY_LOG row 87 cites Playwright keyboard coverage, but I found no spec that tabs to a pin itself (the keyboard test in `replan.spec.js:180` drives the timeline). Lighthouse note: Leaflet still has one target-size warning (row 87). |
| Screenshot stability | DONE | `take-screenshots.mjs --offline-tiles --repeat=3`, `docs/screenshots/screenshot-run-report.json` (3 of 3 pass). Screenshot 12 (settings strip) was taken with a one-off spec, not that script. |
| "Evidence" and "About" renamed? | **No** | see Prompt C row |
| `city_id` on every data-dependent route | PARTIAL | Accepted on `/data/summary`, `/data/places` (query) and `/optimise`, `/compare-hotels`, `/replan`, `/parse`, `/parse-replan` (body), default Tokyo (`main.py:83-248`). |
| `city_id` in every response | **NOT DONE** | `/data/places` returns a `city` object. `/optimise` returns only `result, feasibility_report, approximate, nights_used, nights_source` (checked live), so there is no echo to discard stale responses by. SAFETY_LOG row 91 says responses include city metadata; that is true for the data routes only. |
| Data-verification CSVs: rows verified | No such CSVs exist. Verified records: **0** | Only `docs/eval-travel-minutes.csv` and `eval-hotel-gaps.csv` exist (evaluation outputs). `test_no_record_is_verified` pins zero verified records. |
| Live LLM evaluation exists / covers every city? | Script exists; **never run; Tokyo-only prompts** | `backend/scripts/run_llm_live_eval.py` (opt-in via `RUN_LIVE_LLM_EVAL=1`, cap `LIVE_EVAL_MAX_CALLS = 80`); no results file in `docs/`; the script has no per-city prompts. No `LLM_API_KEY` is configured on this machine yet. |

## 3. Test counts

| Suite | Count | When and on what |
|---|---|---|
| Backend pytest | 302 passed, 0 failed | `latest-full.md`, 2026-10-14 18:13 local, `f5a5b0a` + uncommitted |
| Vitest | 128 passed | run today after the last code change; the saved `frontend/test-results/vitest.json` is **stale (119)** |
| Playwright | 17 passed | full run today after the settings-strip change; no UI code changed since. The saved `playwright.json` is **stale (16)**. |
| Hardening battery | 33 of 33 | `docs/hardening-results.md`, generated 01:52 UTC, pre-dates later backend changes |
| Evaluation | 15 of 15 scenarios; city eval 20 trips (Singapore, Seoul) | `docs/eval-results.md` is stamped `859c357 + uncommitted`; `docs/city-eval-results.md` is stamped `a1a9cb6 + uncommitted`; the city eval text names Singapore and Seoul only, so Kuala Lumpur appears not to be covered |
| Lighthouse | local numbers from 03:04 UTC | `docs/lighthouse-results.md`, before the strip and city changes |

Playwright was re-run on the latest code. The Vitest and Playwright report files, the evaluation, the hardening results and Lighthouse were not.

## 4. Other findings

- 17 files are uncommitted, including the settings strip, city-switch test, regenerated test-result files and screenshot 12.
- The destination check, currency handling and grounding checker for other cities (Part 3) do not exist yet. Today the grounding checker and extraction are not city-aware beyond the dataset passed in (`test_cross_city_name_gets_switch_city_hint_in_mock_llm_path` covers one case).
- Hotel names still contain "(fictional)" in the data and UI.
- The currency symbol ¥ is used for JPY in the UI. There is no CNY.
- There is no JUDGING-SCORECARD, user-test kit, `UI-COPY-CHANGES.md` or per-city live-eval prompts.
