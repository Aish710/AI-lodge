# Build notes

Running log, appended after every phase. Feeds the LinkedIn reflection.

## Phase 1: Backend skeleton and honest data layer (2026-10-13)

**Built**
- Strict Pydantic v2 schemas (`schemas.py`): provenance on every record, per-field provenance for hours and cost, hours as `[[open, close]]` / `null` (closed) / `"unknown"`.
- 12 real Tokyo attractions and 3 FICTIONAL hotels, every record `source_status="sample"`.
- `scripts/build_travel_matrix.py`: deterministic estimated matrix (minutes and fare), constants documented in the script header and in `_meta`.
- `loader.py`: validation at startup with errors naming the bad record; `is_open` returns `True | False | "unknown"`.
- `/health` and `/data/summary`; localhost-only CORS; `conftest.py` writes `tests/results/latest.md`.

**Problems and solutions**
- Strict mode rejects `str -> date` and `list -> tuple` in Python mode, which would break FastAPI request bodies later. Fix: times and dates are plain validated strings, and `[open, close]` is a length-2 list.
- Loader initially expected a list for the poisoned fixture, which was a single object. Fixed the fixture to match the real file format.
- `sed -i` on macOS needs `-i ''`; first attempt to tweak hotel rates failed silently, caught by listing the file.

**Notable**
- Hotel rates tuned (Shinjuku 14,000 / Asakusa 10,500 / Odaiba 8,000 JPY) so the cheapest hotel is also the one farthest from the sights. Whether its transport really erases the saving is computed in Phase 3, not assumed.
- `last_checked` is `null` everywhere: nothing has been checked against a source.

## Facts I was unsure about (please verify)

| Item | Value used | Doubt |
|---|---|---|
| Senso-ji hours | 06:00-17:00 daily | Main hall hours shift by season; grounds are open much longer |
| Meiji Jingu hours | 06:00-17:00 daily | Really sunrise to sunset, varies by month |
| Skytree hours / price | 10:00-21:00 / JPY 2,100 | Price varies by deck, day and demand |
| teamLab Planets | 09:00-22:00; price UNKNOWN | Hours and ticket price vary by date; advance booking believed required |
| Tsukiji Outer Market | 05:00-14:00, closed Wed and Sun | Closures vary per shop |
| Shibuya Sky | 10:00-22:00 / JPY 2,200 | Price may have changed; sunset slots cost more |
| Tokyo National Museum | 09:30-17:00, closed Mon / JPY 1,000 | Opens daily in some seasons; Monday closure when not a holiday |
| Akihabara | hours UNKNOWN (deliberate) | No single official schedule |
| Imperial Palace East Gardens | 09:00-16:30, closed Mon and Fri / free | Closing time is seasonal |
| Shinjuku Gyoen | 09:00-16:00, closed Mon / JPY 500 | Last entry earlier; seasonal; Monday rule |
| Tokyo Tower | 09:00-23:00 / JPY 1,500 | Main deck price uncertain |
| Ghibli Museum | 10:00-18:00, closed Tue / JPY 1,000, advance booking | Closing days differ by month; tickets are timed |
| Durations (all) | 75-150 min | Pure estimates |
| Holiday rule | Not modelled | "Closed Monday" usually becomes "closed Tuesday" after a Monday holiday |

Also: the spec asked for one advance-booking attraction; I marked two (teamLab Planets, Ghibli Museum) because both genuinely need advance tickets.

## Phase 2: Solver, baseline and validator (2026-10-13)

**Schema additions** (to `Preferences`): `start_weekday` is now an int 0-6 (0 = Mon; it was a weekday string in Phase 1), `allow_unknown_hours` (default False), `locked` (list of `{attraction_id, day, start_time}`), and `skip` (attraction ids the user does not want). New shared result models in `schemas.py`: `Stop`, `DayPlan`, `Totals`, `Conflict`, `Alternative`, `SolverMeta`, `SolveResult`. They live in `schemas.py` so the validator can read a schedule without importing `optimiser/`.
- Dataset `priority` values changed from `must_visit` to `nice_to_have` (Senso-ji was the only one). Priority is now decided by the user's preferences: `must_visit` list, `skip` list; a dataset-level `skip` is also honoured unless the user lists the place as a must-visit.

**Budget scope (Phase 2):** strict budget = attraction admissions + estimated transport fares, hotel legs included. Accommodation is Phase 3. Unknown prices count as 0 and are listed in `totals.unknown_cost_items`, with a note ("excluded from total (unknown)") and a validator warning. A non-strict budget is a soft target: overshoot is penalised and reported as a note.

**Built**
- `optimiser/solver.py`: pre-check producing human-readable conflicts from data, CP-SAT model (see `SOLVER_DESIGN.md`), alternatives found by re-solving relaxed versions.
- `optimiser/baseline.py`: sequential fill in input order; respects opening hours, day window, pace cap and strict budget so it is a fair comparison.
- `optimiser/schedule.py`: shared assembly of stops/costs/flags.
- `validator/checks.py` + `feasibility_report.py`: independent re-check written from scratch (imports only schemas and loader data; a test verifies via AST and a fresh-interpreter `sys.modules` check).
- 49 tests pass (`tests/results/latest.md`); measured solve times in `tests/results/solve_times.md`.

**Problems and solutions**
- Day ordering with travel times: used `AddCircuit` over optional nodes with the hotel as depot; absent nodes take self-loops. Needed an implication so that an "empty day" depot self-loop cannot coexist with a visited node.
- First scenario-9 and scenario-10 tests hit the wrong conflict message (a combined-time conflict instead of "does not fit one day"). Reordered the pre-check so the single-attraction round-trip check runs first. Scenario 9's musts were also changed so each fits alone and only the total is too much.
- Tests that looked at `stops[0]` broke because the solver (correctly) adds nice-to-have stops; tests now look up the stop by id.
- Baseline initially failed to place an attraction in a 2-day test because it only moves forward. That is the intended naive behaviour, but it makes comparisons unfair when it drops places, so scenario 3 uses a set the baseline can fully place and the test asserts both schedule the same attractions.

**Notable (honest) findings**
- The baseline is not a strawman: on a simple 2-day, 4-attraction trip it used 231 min of travel vs 223 for the solver. Gains show up only when the input order is scattered (scenario 3: 196 vs 318 min, hand-built alternating west/east order). Phase 7 will report the real averages, including unflattering ones.
- 1-3 day solves are proven OPTIMAL in under 2 s. For 5-7 days with all 12 attractions open as candidates, the solver stops at its deterministic-time limit (status FEASIBLE, about 6 s): a good plan, not a proven optimum. Results repeat exactly across runs.

**Not done / simplified:** `max_walking_minutes_per_day` is not enforced (documented); `interests` is not used by the solver; public holidays not modelled; the alternatives list only offers add-a-day, relax-strict-budget, allow-unknown-hours, extend-day-by-2h and demote-a-must-visit.

## Phase 3: Hotel comparison (2026-10-13)

**Decisions implemented**
- `Preferences.nights` (None means `days - 1`, user-overridable). Every comparison states `nights_used` and `nights_source`.
- Value-of-time is in the objective for the comparison path only. `solve(..., objective=ObjectiveSpec("true_cost", vot, penalty))` minimises `admissions + fares + travel_hours x VoT + penalty x missed`, as integers in 1/60 JPY units. The default objective is untouched; the 49 Phase 2 tests pass unmodified. Rooms are constant per hotel so they change the ranking, not the itinerary.
- Missed-preference penalty: 3,000 JPY per visitable nice-to-have not scheduled (`config.py`). This is a **judgement call, not data**; without some penalty the true-cost objective would schedule nothing. It is a visible line in every breakdown.
- Cache rule: true cost is linear in VoT, so a plan optimal at two VoT values is optimal between them. Sensitivity solves the range ends, halves only intervals where a hotel's plan changed (depth 3, max 36 solves), and computes everything else analytically. Flip points are exact crossings where both segments are exact, otherwise a bisection estimate flagged approximate.
- Honest status: each hotel shows OPTIMAL/FEASIBLE; any non-OPTIMAL solve, partial run, unrefined interval or bisection estimate sets `approximate` and adds a warning.
- Time limit: 10 s for the whole comparison (`HOTEL_COMPARE_TIME_LIMIT_SECONDS`); skipped hotels and unsolved sensitivity are labelled, never hung.

**Built:** `optimiser/hotel_compare.py` (`compare_hotels`, `sensitivity`, `SolveCache`), `POST /compare-hotels` (SGD only added in the route), `scripts/run_hotel_comparison.py`, `scripts/propose_hotel_adjustments.py`, `docs/hotel-comparison-results.md`, `docs/hotel-comparison-sample.json`, `tests/test_hotel_compare.py`. 76 tests pass in total.

**Problems and solutions**
- **Bug caught by a test:** in `solve()` the `objective` parameter was shadowed by the `objective` result variable, so the true-cost spec was silently ignored and the default objective ran. My first hand-computed tests still passed because their plan was forced (only two sights). The test comparing the solver's objective value with `60*(adm+fares+penalty*missed)+VoT*minutes` exposed it. Fixed by copying the parameter to `spec` first; parametrised tests with optional sights now guard it.
- Gap-in-hours was computed from rounded hours (-1.19 vs -1.18); now computed from minutes.
- Sensitivity marks `approximate` whenever some interval is not refined to identical plans. On the real trips this is nearly always true (plans keep changing with VoT), so most real results are labelled approximate. This is honest, but it will look cautious in the UI.

**Notable (honest) findings** (full tables: `docs/hotel-comparison-results.md`)
- **The cheap, far Odaiba hotel wins by true cost in all three real trips (2, 3, 4 days) at every value of time from 0 to 3,000 JPY/h.** No flip exists in range. At 1,000 JPY/h it beats Asakusa by 2,097 / 4,027 / 6,197 JPY and Shinjuku by about 5,400 / 11,100 / 16,100 JPY. The 2,500 JPY nightly gap to Asakusa outweighs the extra 17-56 minutes of total travel in these plans, because Odaiba's estimated travel is only about 40-50 min each way.
- That means the signature "cheaper hotel costs more" story does not appear in the current data. Hard-coded demo claims would be untrue; the app must show whatever it computes.
- Asakusa vs Shinjuku does behave as expected for trip lengths: Shinjuku is never best at these rates.
- Trip B with sensitivity exceeds the 10 s default limit (10.0 s, partial); it completes in about 23 s with a 120 s limit.
- teamLab Planets (unknown price) is attractive to the solver because an unknown price counts as 0. Its price is excluded from totals with a warning on every hotel, but this does bias plans toward it. Worth fixing in Phase 4 or by assuming a conservative placeholder.

**Proposed hotel adjustments (NOT applied; for your approval)** from `scripts/propose_hotel_adjustments.py` (in-memory copies only):
1. P1 rate only, Odaiba 8,000 to 9,500: still wins A and C at all VoT; flips only in Trip B at about 2,700 JPY/h. Weak.
2. P2 location only, move Odaiba to the Wakasu/Shin-Kiba shore (35.6130, 139.8310): flips in Trip A at about 1,731 JPY/h and Trip B at about 2,729; none in C.
3. **P3 (recommended)**: that location plus rate 8,500: flips in Trip A at about 1,303 JPY/h, Trip B at about 1,610 (bisection estimate) and Trip C at about 1,913 (estimate; later flips back at about 2,136, so treat as approximate). Odaiba still wins at 1,000 JPY/h, so a budget student keeps the cheap hotel, while a higher-value-of-time traveller flips to Asakusa. This is an honest "it depends on your time value" story and also a defensible location (further out) and rate (about 20% below Asakusa).

**Simplified / not met:** only 2-3 hotels; sensitivity is for one preference set per call (no global cache across requests, so the slider recomputes from scratch, 0.1-25 s depending on trip length); the SGD display is a per-hotel pair only; `approximate` is conservative.

## Phase 4: Replanning (2026-10-13)

**Decisions implemented**
1. **Hotel proposal 3 applied.** Odaiba Harbour Stay (fictional) moved to lat 35.6130, lon 139.8310 (Wakasu/Shin-Kiba shore), rate 8,000 to 8,500 JPY, provenance note "Fictional hotel; rate and location adjusted to illustrate the trade-off." Matrix regenerated with `scripts/build_travel_matrix.py` (never hand-edited). Id, name and area label stay "Odaiba" to limit churn; the coordinates are the real change.
   Tests whose expected values changed (only values, no logic): in `tests/test_hotel_compare.py`: `test_reference_matrix_values_are_what_the_hand_calculation_assumes` (Odaiba legs 56 min/460 JPY and 53/430; rate 8,500), `test_hand_computed_true_cost_breakdown` (Odaiba 125 min, fares 1,080, time cost 2,083, true cost 13,763; ranking gap 110 JPY; hours gap -1.35), `test_nights_default_is_days_minus_one_and_override_works` (3 x 8,500), `test_flip_point_matches_the_analytic_value_and_cache_saves_solves` (analytic flip 60 x 1460 / 81 = 1,081.5 JPY/h), `test_sensitivity_grid_costs_match_a_direct_solve` (13,763). The module docstring's paper arithmetic was rewritten to match.
2. **Unknown-price placeholder** (optimiser only): median of known admissions (500 JPY on this data). It never enters the strict-budget constraint, displayed totals or the validator; breakdowns show `optimisation_placeholder_jpy` separately, and warnings say so. A test turns the placeholder off (override 0) to prove the old "unknown means free" bias existed and is gone.
3. **Replan objective:** Phase 3 true cost plus `W_DISRUPTION` (1,500 JPY-equivalent, judgement call) per unnecessarily moved activity. Hotel fixed unless `switch_hotel`.
4. **"Moved":** day changes, or start shifts by more than 30 minutes (config). Activities the user locked or moved are labelled `reason: user` and not counted. Activities the optimiser drops are listed as `dropped_by_optimiser` (priced by the missed-preference penalty, not double-counted as disruption).
5. **Must-visit removal** needs `confirm_remove_must_visit: true` (default false, never set by the server; a test scans the code for it). Otherwise HTTP 422 naming the sight and the consequence. With it, the removal appears in the diff (`was_must_visit`), a diff warning and a "must-visit removed by user" warning check in the feasibility report.
6. **Stateless:** the API takes preferences, current schedule and operations, and returns the new schedule, new preferences and diff. Nothing is stored server-side; the test checks the app state holds only the dataset.

**Built:** `optimiser/replan.py` (operations lock/unlock/remove/move/change_budget/switch_hotel, up to 20 per call, applied in one solve), disruption term, warm-start hints and start-drift tie-break in `solver.py`, public `precheck()`, `POST /replan`, `scripts/run_replan_evaluation.py`, `scripts/make_replan_samples.py`, `docs/replan-results.md`, `docs/replan-samples.json`. 104 tests pass.

**Problems and solutions**
- Conflicting lock operations (outside opening hours, overlapping locks) must be rejected before solving, but infeasibility (budget, time) must return the original plan. Solution: reuse the solver pre-check and split its conflict codes into "lock conflicts" (HTTP 422, rejected) and everything else (status `infeasible`, original plan returned unchanged).
- A no-op replan must return the identical schedule, but equal-cost alternatives exist. Added a tiny tie-break (1/60 JPY per minute of start-time drift) and CP-SAT hints; the test asserts exact equality.
- A validator-only concept ("must-visit removed by user") needed to appear in the Trip Feasibility Report without touching the validator's independence; `build_report` gained an optional list and appends one warning check (the checks themselves still import nothing from `optimiser/`).
- The first attempt to force a non-optimal solve (tiny deterministic-time limit) did not trigger because the warm start made the solve instant; the test now uses a 4-day packed trip.

**Notable (honest) findings** (details: `docs/replan-results.md`, 24 seeded scenarios)
- Disruption-aware replanning moved a mean of 0.10 activities unnecessarily (max 1) against 2.48 (max 6) for a naive full re-solve. It moved fewer in 15 of 21 comparable scenarios, equal in 6, more in none.
- Stability costs money: the final plan was a mean of 218 JPY more expensive than the naive optimum (max 1,570 JPY). In move scenario 18 the stable plan is 1,570 JPY dearer than the naive one.
- 3 of 24 random `move` edits were rejected before solving (conflicts with opening hours or travel time); 0 replans were infeasible. Random `lock` edits lock an activity at its current slot, so cost change is 0 by construction; they mainly test stability.
- The naive re-solve often "moves" things only because equivalent plans are interchangeable (e.g. which day an equal-cost sight falls on). That inflates its count, but a user still sees a different itinerary.
- After the hotel move, the cheap hotel wins at 1,000 JPY/h in all three trips but flips to Asakusa at about 1,535 JPY/h (Trip A, exact), 1,610 (B, bisection estimate) and 1,912 (C, estimate; flips back at about 2,136; approximate). `docs/hotel-comparison-results.md` has the tables.
- The placeholder changed the Asakusa result for Trip A from 33,757 to 34,090 JPY (it no longer treats teamLab Planets as free).

**Not modelled / simplified:** public holidays, `max_walking_minutes_per_day` and `interests` remain unmodelled. Infeasible replans return conflicts but no computed alternatives (to keep latency low). The disruption weight and the 30 min threshold are judgement calls. `before` missed preferences are read from the current result.

## Phase 5: LLM layer (2026-10-13)

**Model used.** Looked up via the Anthropic SDK reference bundled with this environment (Python SDK `anthropic==1.13.0`, which is built on `httpx2`). The `.env.example` suggests `claude-opus-5-5` (current default Opus per that reference); the app only reads `LLM_MODEL` and never hard-codes a model. Cheaper tiers (`claude-sonnet-5-5`, `claude-haiku-5-5`) are your cost decision. Tests never call it.
**Parameter surprise:** the current models reject `temperature`/`top_p` (the SDK signature no longer has `temperature`), so your "low temperature" is implemented as `output_config.effort="low"` (env `LLM_EFFORT`, empty disables), strict schemas and validation. Thinking is always on for these models and thinking tokens count toward `max_tokens`, so the caps have headroom (2000/1200). If `LLM_MODEL` is an older model that rejects `effort`, set `LLM_EFFORT=` (empty).

**Built**
- `llm/prompts.py` (fixed, `PROMPT_VERSION="1"`), `sanitize.py`, `client.py` (Protocol + Anthropic wrapper, `LLMUnavailable`, DI function `get_llm_client`), `names.py`, `schemas.py`, `runner.py`, `extract.py`, `parse_replan.py`, `grounding.py`, `explain.py`.
- `POST /parse`, `POST /parse-replan`, `explain` flag on `/compare-hotels` and `/replan`, `/health` now has `llm_configured` and `llm_mode`.
- `Attraction.aliases` (sample-labelled): Senso-ji: Sensoji, Senso ji, Asakusa Temple; Meiji Jingu: Meiji Shrine, Meiji Jingu Shrine; Tokyo Skytree: Skytree, Sky Tree; teamLab Planets: team Lab Planets, teamLab Planets Tokyo; Tsukiji Outer Market: Tsukiji Market, Tsukiji Fish Market, Tsukiji; Shibuya Sky: Shibuya Sky Deck; Akihabara: Akiba, Akihabara Electric Town; Imperial Palace East Gardens: Imperial Palace Gardens, Imperial Palace East Garden, Kokyo Higashi Gyoen; Shinjuku Gyoen: Shinjuku Gyoen National Garden; Ghibli Museum: Ghibli, Studio Ghibli Museum, Mitaka Ghibli Museum. Please verify. I deliberately gave teamLab Planets no bare "teamLab" alias (teamLab Borderless is a different venue).
- Tests: `tests/llm_mock.py` (scripted mock that records prompts and counts calls), network-blocking and key-clearing autouse fixture in `conftest.py`, `fixtures/injection_prompts.json`, `fixtures/live_eval_prompts.json`. 203 tests pass in total (99 new).
- `scripts/run_llm_live_eval.py` (opt-in, call-capped at 80, writes `docs/llm-live-eval.md`); it was NOT run. Without the environment variables it exits with a message (verified).

**Problems and solutions**
- "teamLab Borderless -> unresolved with a suggestion" conflicts with the strict 0.92 difflib rule (the ratio is far lower). Added a third, weaker suggestion tier (a shared distinctive first word, labelled "different place?"). It is still only a suggestion and never accepted. This goes beyond your spec; say if you want it removed.
- A single-partial match (e.g. "the museum" when only one museum is in the plan) is also only a suggestion, because the dataset has another museum: no guessing, at the cost of an extra question.
- The grounding check on names first used ids from the facts; replaced with "any place whose name or alias appears in the facts text is allowed", so missed-sight names listed in the facts are not falsely rejected.
- Retry messages echo only schema paths and messages, never offending values (avoids replaying injected text as an error string).

**Notable (honest)**
- The mocked suite proves the pipeline, not model behaviour; real-model figures need your live-eval run.
- Strict grounding means some valid explanations will fall back to the template (safe by design).
- `/parse` always returns the sanitised echo of the user text in the response (not stored).

**Simplified / not done:** natural-language replan proposals are not pre-validated against the optimiser (the later `/replan` call will reject conflicts); no Docs-level SGD figures in `/parse` beyond the stated interpretation; `interests` are extracted but unused by the solver; alias list is small.

## Phase 6: API hardening and deployment readiness (2026-10-13)

**Built**
- `app/hardening/`: `config.py` (validated env config, fails fast), `errors.py` (one error format), `limiter.py` (sliding window + proxy-aware client IP), `llm_scope.py` (rolling-24h circuit breaker, per-request deadline and usage stats, `llm_for_request` dependency), `logging_setup.py` (record-factory redaction, JSON metadata formatter), `middleware.py` (pure ASGI: request id, body cap while reading, 415, depth/NaN checks, tiered rate limit, security headers, access log, generic 500). `app/runtime.py` is the single injectable clock.
- `app/main.py` is now `create_app(config)` (module-level `app = create_app()` for uvicorn): per-app limiter and budget, exact-origin CORS (outermost, so 429/413 carry CORS headers), docs/OpenAPI off by default, unified exception handlers.
- `POST /optimise` (true-cost objective, same as the hotel comparison, so the plan matches the comparison; independent validator always runs and a failing report is returned; infeasible results carry conflicts and alternatives within an 8 s budget; `approximate` label when only FEASIBLE; optional explanation).
- `app/untrusted.py`: client schedules are rebuilt from ids and start times and validated; used by `/replan` and `/parse-replan`.
- Schema caps in `schemas.py`, `extra="forbid"` on all request models, LLM timeout lowered to 10 s, new `missed_preferences_for()` helper and an alternatives time budget in the solver, `unavailable_note` / `sample_reason` so users see WHY sample mode is active (no key, daily cap, deadline).
- Deployment: `backend/Dockerfile` (slim, non-root, pinned, healthcheck, uvicorn with `--no-access-log --no-proxy-headers`), `.dockerignore`, `render.yaml`, `requirements-dev.txt` (test deps split from runtime), `scripts/smoke_test.py`, `scripts/run_hardening_checks.py`, docs `API_HARDENING.md`, `PRIVACY.md`, `DEPLOY.md`, `hardening-results.md`.
- 239 tests pass (203 existing + 36 new).

**Existing tests changed (genuinely required)**
- `tests/conftest.py`: new autouse fixture resets the shared app's limiter and LLM budget per test (otherwise the module-level app's rate limiter would 429 later tests) and clears dependency overrides afterwards.
- The unified error format `{"error": {"code", ...}}` changed assertions in `test_hotel_compare.py::test_api_returns_clear_json_errors`, `test_replan.py::test_api_must_visit_removal_needs_explicit_flag_and_server_never_sets_it`, `test_replan.py::test_api_clear_json_errors`, `test_llm_api_safety.py::test_parse_end_to_end_with_a_mock_client_and_oversize_is_rejected_not_truncated` (error code and message paths only).
- `test_llm_api_safety.py::test_health_reports_sample_mode_and_never_echoes_a_key`: expected dict gains `llm_limit_reached: false`.
No other test was touched.

**Decisions**
- Rate limiting happens in the middleware, not per route, so it also covers bodies that fail validation; rejected requests consume a token. `explain=true` is detected by peeking at the (already size-capped, already parsed) body.
- The circuit breaker wraps whatever client the dependency yields, so mocks are counted exactly like the real SDK and the same code path is tested.
- A client schedule's costs and totals are ignored rather than rejected (they cannot influence results); altered stop times and anything the validator fails are rejected.
- Whether to run the true-cost objective for `/optimise` was a choice (consistency with comparison and replanning over the Phase 2 weighted objective).

**Problems and solutions**
- Pydantic accepts `NaN`/`Infinity` from Python's JSON parser; they are rejected in the middleware with `parse_constant` before FastAPI sees the body. Python recursion on deeply nested JSON is avoided by a byte-level depth scan first.
- The module-level app shared one rate limiter across the whole test session: fixed with the autouse reset and a factory so hardening tests use their own app instances and fake clock.
- The marker-in-logs test first failed because the TestClient's own HTTP library logs the request URL client-side; the assertion now looks only at server-side loggers (the server logs no query strings).
- uvicorn's default proxy-header handling would rewrite the client address using `X-Forwarded-For` for peers it trusts, bypassing our trusted-hop logic: disabled (`--no-proxy-headers`).

**Measured** (this machine, not Render): `import app.main` 0.8 s; lifespan plus first request 0.02 s; uvicorn process start to first `/health` 200 about 1.4 s; resident memory about 120 MB after the smoke test and after a 7-day solve; in-process p50/p95 latencies are in `docs/hardening-results.md` (33/33 abuse cases passed).

**Not done / simplified:** Docker image not built (no Docker here), so OR-Tools inside the image is untested; the free host's `X-Forwarded-For` hop count could not be confirmed from its docs (a verification procedure is in DEPLOY.md); no CSP header (pure JSON API); no per-endpoint concurrency limit for solver work (rate limits only); no automatic cleanup of rate-limit keys beyond a size-triggered purge; JSON depth/NaN checks run on POST bodies only.

## Phase 7: Reproducible evaluation (2026-10-13)

**Built**
- `app/eval/`: `scenarios.py` (the 15 named scenarios, defined once and shared by pytest and the script), `generator.py` (seeded trips), `independent.py` (recomputes the solver's conflict claims and brute-forces the must-visit schedule, importing nothing from the optimiser), `metrics.py` (per-trip runs and all aggregates), `claims.py` (claim-safe sentences generated from the metrics), `report.py` (markdown), `limits.py` (deterministic limits and the post-hoc diagnostic switch), `mock_llm.py`.
- `optimiser/baseline.py: nearest_neighbour` (second baseline; the Phase 2 naive function is untouched).
- `scripts/run_evaluation.py` (`--quick`, `--full`, `--seed`, `--out-dir`) and a small refactor of `scripts/run_replan_evaluation.py` so it exposes `collect` and `summarise` (its own report regenerates identically apart from wall-clock times; checked by diffing).
- Outputs in `docs/`: `eval-results.md`, `eval-results.json`, `eval-scenarios.json`, `README-claims.md`, two CSVs; `docs/EVALUATION.md` is the method note. `tests/results/evaluation-scenarios.md` is the scenario table.
- 283 tests pass (239 existing, unmodified, plus 44 new in `tests/test_evaluation.py`). Full run took 293 s here; `--quick` about 26 s.

**Decisions**
- Wall-clock solver limits are lifted for the evaluation so only the deterministic limit decides when a solve stops; the shipped limits are unchanged.
- Trips are solved with the objective `POST /optimise` runs (true cost at the trip's value of time), pinned by a test against the real route. The Phase 2 weighted objective is a labelled secondary analysis only.
- Pace is fixed at balanced (the default) rather than varied; every other generator constant is listed in the scenario file.
- Nearest neighbour follows the brief literally (no must-visit priority), so must-visits it cannot reach are reported, not hidden.
- Rounding never favours the product (down for improvements, up for failures and costs).

**Problems and solutions**
- **I first evaluated the wrong objective.** My first full run solved the trips with the Phase 2 weighted objective (the default of `solve()`), and my report text wrongly said that was what `/optimise` runs. Its result looked bad (more travel than both baselines on average); I tested the pace-balance term as the cause by re-solving with that weight at 0. Re-reading `app/main.py` showed `/optimise` actually uses the true-cost objective, so that first run measured a path no API route uses. Fix: the headline solver is now the true-cost objective exactly as `/optimise` runs it (new test `test_headline_solver_runs_the_same_objective_as_post_optimise` compares against the real route), and the Phase 2 objective plus the pace-balance-off variant moved to a labelled post-hoc secondary section (A2). No number from the first run is published anywhere: every output file was regenerated.
- The existing replan script printed and wrote its report from `main()`, so there was nothing to import: split into `collect`/`summarise`, verified by regenerating and diffing against the Phase 4 report.
- The test that checks scenarios are defined once first flagged my own throwaway scenarios (used to test failure reporting): the detector now matches only scenario numbers 1-15.

**Notable (honest)**
- The generated trips produced only one kind of infeasibility (a must-visit with unknown hours), so the independent audit of other conflict codes is covered by hand-built tests only.
- Every solver plan carries data-quality warnings (estimated transport is always flagged), so "pass" is 0 and "pass with warnings" is the best verdict.
- Baselines never broke an hours, overlap or window rule; their only validator failures are must-visits they could not place and self-report.

**Simplified / not done:** no confidence intervals or significance tests (stated everywhere); explanation and parsing quality not measured (live evaluation not run); the free-tier CPU may change solver statuses; hotel result only describes the fictional demo dataset.


## Phase 8, Milestone A: frontend core (2026-10-14)

**Built** (`frontend/`: Vue 3, Vue Router, Vite, Bootstrap, Leaflet; state is a plain reactive module, no Pinia): API client (`src/api`: one error normaliser, abort-by-key, timeouts above the server deadline, cold-start probe, 429 countdown), screens Create trip, Wishlist, Hotel comparison, Itinerary (map + timeline + feasibility report + not-scheduled panel + conflict panel), honesty banner, mode indicator, source badges, demo helpers. Types are hand-maintained JSDoc (`src/api/types.js`), because the backend keeps OpenAPI off by default and a build step that needs a running server would be fragile.
**Backend change (one):** `GET /data/places` (cheap rate tier): coordinates, price, hours, indoor/booking flags and provenance for attractions and hotels; no `description`. Needed because no response carried coordinates. It is wider than the minimal spec because the Wishlist cards need those fields too.
**Tests:** 60 Vitest, 6 Playwright (real backend, sample mode), backend 288 pass (284 existing unmodified + 4 new: places, demo examples).
**Problems and solutions:** (1) `/compare-hotels` with sensitivity takes about 10 s (the server's whole comparison budget) and comes back flagged approximate: the UI now fetches the fast comparison first and the sensitivity second, and shows the table immediately. (2) Leaflet drew tiles for only part of the map; fixed with a ResizeObserver calling `invalidateSize`, and screenshots now wait for tiles. (3) `Retry-After` cannot be read cross-origin (CORS does not expose it), so the client uses `details.retry_after_seconds` from the error body. (4) The first screenshot run picked the first "Use this hotel" button, not the best-overall one.
**Demo input disclosure:** the example trip sets value of time to 3,000 JPY/h because at the default 1,000 the cheapest hotel is also the best for that trip; at 3,000 the real API result says they differ. A backend test pins this. It is an input, visible and editable, not a hardcoded story.

## Phase 8, Milestone B: replanning UI, natural language, explanations, evidence (2026-10-14)

**Built** (`frontend/`): per-stop Lock / Unlock / Remove / Move (with the API's day-part shortcuts), a pending-changes tray (one `/replan` call, 20 operation cap, plain-language list, remove-before-apply), a must-visit confirmation dialog on a native `<dialog>`, the Diff view (every cost line, kept/moved/removed/added, missed sights, disruption weights, new feasibility report, every warning verbatim, "Not like-for-like" beside a saving), restore-previous-plan, and a rejected-replan state that says the original plan is unchanged. Natural language in two places (`/parse` fills the editable form with raw input beside the extracted JSON, defaults, assumptions and click-to-choose suggestions; `/parse-replan` shows a proposal card that only queues). Opt-in explanations with the llm/template badge and verbatim warnings. Evidence page (from `scripts/sync-evidence.mjs`), About page with an SVG architecture diagram, 404, Reset, progress/elapsed/cancel for the slow comparison call, skeleton loaders, social meta tags and favicon, Netlify config (`_headers` with a generated CSP, SPA rewrite), `scripts/live-smoke.mjs`, `scripts/run-lighthouse.mjs`, `scripts/make-submission-facts.mjs`, screenshot script (11 shots plus a recording).
**Backend change:** none to behaviour. Two additive contract tests (`tests/test_frontend_contracts.py`) pin the day-part mapping and input limits that the frontend mirrors. Backend suite: 290 pass (284 existing, unmodified, plus the Milestone A and contract tests).
**Evaluation re-run on the committed code** (`fbe6e3d`): 154 s; every generated headline sentence identical to the previous run.
**Empty day, investigated (decision 2):** not a bug. With the optimiser's own objective, the plan with an empty Day 1 and the best plan that uses Day 1 have the same cost (both OPTIMAL, 29,100 JPY at 3,000 JPY/h): fewer days out of the hotel is as cheap or cheaper, and which day stays free is a tie. The UI now says so in plain language on a free day. (My first comparison looked wrong because the objective prices an unknown admission at a 500 JPY placeholder while the breakdown excludes it.)
**Problems and solutions:** (1) the `#hotel-value` link did not scroll because Evidence content loads after navigation: the page now scrolls once its data arrives. (2) The synced evidence folder was named `/evidence/`, colliding with the `/evidence` page route on a static host: renamed `evidence-data`. (3) A partial pytest run overwrote `tests/results/latest.md`, so the evidence page briefly showed "2 tests": a unit test caught it; the rule is to run the full suite last (logged as a gap). (4) Lighthouse found real issues (Bootstrap link colour contrast, wordmark and stop-button accessible names, heading order, overlapping map markers as touch targets, layout shift from late content): fixed, and the initial JavaScript dropped by lazy-loading routes. (5) Adding the natural-language box made an older end-to-end selector ambiguous: the test now matches exactly.
**Notable (for the LinkedIn reflection):** the proudest engineering moment was making the safety rules testable at the request-building layer (the must-visit flag cannot be set from natural language, asserted in code, not just in the UI); the most useful surprise was Lighthouse pointing at accessibility issues that a keyboard-only test had not.
**Simplified / not done:** no live deployment (cannot be done from here); Lighthouse is a local run; no live AI evaluation.

## Final hardening and submission prep (2026-10-14)

**Built**
- Solver capacity gate for `/optimise`, `/compare-hotels` and `/replan`: defaults to one in-flight solve per process, returns structured `503 solver_busy` with `Retry-After`, and leaves `/health` responsive.
- Configurable solver time budgets for optimisation, hotel comparison, replanning and alternatives; frontend e2e/Lighthouse runs raise local concurrency so tests do not interfere with each other.
- Full-suite evidence hygiene: pytest now writes detailed run metadata and a separate `latest-full.md`; strict evidence sync and `build:release` require full backend evidence instead of whatever partial pytest last wrote.
- Release validation: HTTPS non-local API origin, generated host config, required `dist` artifacts, evidence revision match and built-asset secret scan.
- Map accessibility hardening: keyboard-focusable map markers with stop-specific names and Enter/Space popup handling that scrolls/focuses the matching timeline item.
- Screenshot automation hardening: concrete readiness waits, bounded retries, diagnostics and `screenshot-run-report.json`; a three-repeat local screenshot run passed.
- Fitinerary branding and submission material: README, Devpost draft, LinkedIn draft, deployment notes, final audit, refreshed screenshots/evidence/Lighthouse summaries.

**Verification**
- Backend: 293 passed, 1 warning.
- Frontend unit tests: 119 passed.
- Frontend Playwright: 16 passed.
- Hardening script: 33/33 abuse cases passed.
- Full evaluation: 15/15 scenarios, 60 trips, all generated headline claims retained.
- Release build: `VITE_API_BASE_URL=https://api.example.com npm run build:release` passed with a placeholder HTTPS API origin.
- Lighthouse local: home 99/100/100, evidence 98/100/100, itinerary accessibility 97 and best practices 100.

**Notable**
- Local live-smoke against a running backend was not run because the server-start approval was rejected.
- Secret scans found only fake/test key fixtures and env-var names, including historical fake-key patterns in the existing commit; no real secret was found.
- The remaining Lighthouse itinerary warning is Leaflet marker target spacing. The timeline/list is still the accessible equivalent, and markers themselves now expose keyboard labels.

**Simplified / not done:** no live deployment; no live AI evaluation; Docker image still untested here; solver capacity is per process rather than cross-replica; cancelling a browser request does not stop a solve that has already started.

## Phase 9b, Milestone 1: multi-city backend packs (2026-10-14)

**Built**
- City packs under `backend/app/data/cities/<id>/` with `city.json`, attractions, fictional hotels and generated travel matrices for Tokyo, Singapore and Seoul. The original root Tokyo files remain in place for legacy tests and compatibility; `cities/tokyo` is a copied pack with identical records and matrix.
- Context-aware coordinate validation: direct `Attraction` / `Hotel` validation still defaults to the original Tokyo bounds, while city-pack loading validates against each pack's own bounds.
- `load_all_city_datasets()`, `GET /data/cities`, and `city_id` support on data-dependent routes. Existing clients default to `tokyo`.
- Per-city display FX metadata. The optimiser still works in local integer currency units; display conversion uses the labelled sample rate from `city.json`.
- Per-city name resolution for `/parse`; cross-city names are unresolved with a "switch city" hint, never silently mapped. Descriptions still do not enter prompts.
- `scripts/build_travel_matrix.py --city <id>` so new matrices are generated from each city's transit constants, not hand-edited.
- `scripts/run_city_evaluation.py` for smaller Singapore/Seoul samples plus per-city data-integrity outputs in `docs/city-eval-results.*`.
- `docs/CITIES.md`, a six-step scale-out guide.

**Verification**
- Full backend suite: 301 passed, 1 warning. Existing test source files were not changed; new coverage is in `tests/test_city_packs.py`.
- Tokyo full evaluation: 15/15 scenarios PASS, 60 trips. Claim-safe headline sentences are identical to the committed baseline; only generated timestamp/hash changed.
- Added-city evaluation: Singapore and Seoul, 20 seeded trips each, written separately and labelled smaller sample.

**Notable**
- The non-Tokyo data is intentionally small and sample-labelled. It is useful for scale-out and grounded behaviour testing, not real travel advice.
- Existing Tokyo route behaviour is preserved for old clients because every new request field defaults to `city_id="tokyo"`.
- The old result field names still say `*_jpy` for compatibility, even when a non-Tokyo city uses SGD or KRW internally. New responses include city/currency metadata so the frontend can label values honestly in Milestone 2.

**Simplified / not done:** frontend flow is unchanged until Milestone 2; Singapore/Seoul evaluation is smaller and not pooled into any headline; live LLM evaluation was not run; non-Tokyo sample facts, prices, hours and durations still need human verification before public claims.
