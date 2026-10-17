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

## Phase 9b bridge: Malaysia pack and visible city picker (2026-10-14)

**Built**
- Added a Malaysia sample city pack as Kuala Lumpur (`city_id="kuala_lumpur"`), because the backend is organised by city rather than country.
- Wired the existing frontend to `GET /data/cities` and `GET /data/places?city_id=...`, so the first screen now shows city cards for Kuala Lumpur, Seoul, Singapore and Tokyo.
- City changes clear wishlist, chosen hotel, comparison and itinerary with a confirmation when needed. State remains memory-only.
- Budget/value-of-time labels now use the selected city's local currency metadata instead of assuming yen.

**Verification**
- Backend city-pack tests: 8 passed.
- Full backend suite: 301 passed, 1 warning.
- Frontend unit/component suite: 119 passed.
- Frontend production build passed.
- Local running backend now returns all four cities from `/data/cities`.

**Notable**
- This is a visual bridge, not the full Milestone 2 dynamic flow. The app still uses the old page sequence, but the data on those pages changes with the selected city.
- Kuala Lumpur facts are sample/general-knowledge placeholders and must be verified before public claims.

## Frontend UX: settings summary and memory-only clarity (2026-10-14)

**Built**
- Added a compact trip-settings strip to the Sights, Hotels and Itinerary screens with an edit link back to the Trip screen.
- Added explicit memory-only copy beside the Trip screen Next button, plus a visible Start over action guarded by confirmation.
- Added a standard browser refresh/close warning only when there is unsaved in-memory trip work.
- Added a non-blocking high-budget hint computed from the loaded sample attraction-cost data; no backend behaviour changed.

**Verification**
- Added Vitest coverage for strip formatting, Back/Next navigation, browser-style back navigation, edit-link preservation, Start over confirmation, leave-page guarding and the budget hint.
- Added Playwright coverage for settings -> Next -> Back preservation and refresh clearing the in-memory form.

**Notable**
- State is still intentionally memory-only: no localStorage, sessionStorage, cookies or analytics.
- The frontend data endpoint does not expose the travel fare matrix, so the budget hint uses the currently loaded dataset cost fields available to the frontend and stays advisory.
- Follow-up check: the budget hint's sights-per-day numbers now live in `frontend/src/lib/pacecaps.json`, pinned to `PACE_MAX_PER_DAY` by `test_pace_caps_match_the_backend` (a test only; no backend behaviour changed). The hint counts admissions only (transport is not exposed to the frontend), so it understates cost; the 20x margin absorbs that. Counts at this check: backend 302 passed, Vitest 127 passed, Playwright 17 passed. Screenshot: `docs/screenshots/12-settings-strip.png`.

## Phase 9c, Parts 1 and 2: stacked hotel list and one city per trip (2026-10-14)

**Housekeeping found first**
- The Python-template `lib/` rule in `.gitignore` had been hiding the whole `frontend/src/lib/` folder, so every earlier commit was missing `format.js`, `rules.js`, `replan.js` and the JSON mirrors and could not build from a clean clone. Fixed with `!frontend/src/lib/`; a fresh clone now installs, builds and passes Vitest (checked in a scratch clone).

**Backend (no existing test changed)**
- Every response echoes `city_id` (`/data/summary`, `/data/places`, `/optimise`, `/compare-hotels`, `/replan`, `/parse`, `/parse-replan`).
- New `app/city_guard.py`: a hotel id, locked stop or replan target that belongs to another city gets a 422 `wrong_city` naming the id and its real city. Schedules from another city keep the existing `invalid_schedule` code and now name the city.
- `tests/test_city_isolation.py` (52 tests): echo for all 4 cities, and every route x every ordered city pair (12).
- NOT done: `must_visit` / `skip` ids from another city. The existing test `test_cross_city_ids_are_rejected_by_optimise_and_replan` asserts HTTP 200 with an infeasible plan for that case, so changing it needs the owner's approval first.

**Frontend**
- Hotels are stacked rows (checkbox, name, area, local price with display approximation, "Demo hotel" tag), one slim "made-up examples" line, "n of m selected, choose 2 or 3", and a disabled Compare button with a visible reason. "(fictional)" is removed from every displayed name and server sentence (`lib/names.js`); the data field keeps it.
- The selected city is one store value. The API client refuses to build a request without a city, aborts everything in flight on a switch, and discards any response naming a different city (metadata-only console warning). A persistent city chip shows on every step and in the summary strip. Switching city after choices exist shows a confirmation listing what will be cleared.
- Found on the way: the honesty banner said "Tokyo only" for every city (now city-aware, identical text for Tokyo); selecting hotels pre-ticked all hotels even beyond the API's maximum of 3 (now capped at 3); loading the Tokyo example from another city left that city's data in place (now switches city first).
- Tests: Vitest 137 (9 new: payload ids for all 4 cities, switch leaves nothing behind, stale response, no-city refusal, name cleaning); Playwright 24 (7 new: stacked layout for each city at 320/375/768/1280 px with long, Korean, Chinese and Malay names, Compare-button reason, Seoul-to-Tokyo switch, keyboard map pin). A deliberate layout break was confirmed to fail the layout test.

**Known gap found**
- Server sentences (for example the hotel-comparison insight) print amounts labelled "JPY" for every city, so a Seoul trip says "100,000 JPY cheaper". The solver's cost lines are in the city's own units; only the label is wrong. Part 3 (currency precision) covers it. SAFETY_LOG row 91 corrected accordingly.

## Phase 9c: foreign must_visit / skip ids rejected (2026-10-14, owner-approved)

- Behaviour: a `must_visit` or `skip` id that belongs to another city is rejected with 422 `wrong_city` (naming the id and its real city) on `/optimise`, `/compare-hotels`, `/replan` and `/parse-replan`.
- **One existing assertion changed, with the owner's approval.** `tests/test_city_packs.py::test_cross_city_ids_are_rejected_by_optimise_and_replan`, first request (Tokyo city, Seoul must-visit `gyeongbokgung`):
  - before: `status_code == 200` and `result.status == "infeasible"`
  - after: `status_code == 422` and `error.code == "wrong_city"`
  - why: the old behaviour silently solved a request that mixed two cities and reported it as an infeasible trip; the one-trip-one-city rule requires an explicit error. The second half of that test (a Seoul schedule sent to Tokyo's `/replan` is `invalid_schedule`) is untouched and still passes: on the replan routes the preference-id check runs after the schedule's own structure is validated and before the validator (`after_structure` hook in `app/untrusted.py`).
- New test: `test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences` (12 city pairs x 2 fields x 4 routes).

## Phase 9c: currency labels and the clean-clone guard (2026-10-14)

**Currency label bug (found in the Seoul screenshot: "100,000 JPY cheaper" for a KRW trip)**
- New `backend/app/money.py` is the only place server sentences print amounts: the selected city's own code after the number ("1,500 JPY", "135,000 KRW"), `per_hour` ("1,000 JPY/h") and the labelled display conversion ("about S$14 at the SAMPLE rate"; "USD 99" for cities displayed in dollars). Routed through it: hotel insight, flip summary and warnings, validator budget checks, solver conflicts and notes, replan summary/diff warnings/operation descriptions, and the template explanations (`llm/explain.py`).
- Frontend: Itinerary, day timeline, diff view and not-scheduled panel were printing a hardcoded yen sign for every city; they now use `lib/money.js` (the selected city's currency). A parsed budget draft is kept in the city's currency (it was silently set to JPY). The grounding checker's unit list now includes KRW, won, MYR, ringgit, CNY, yuan, RMB, USD.
- Format decision: server sentences keep the existing "1,500 JPY" shape (code after the number) because an existing test pins "33,000 JPY"; the UI keeps the symbols (¥, ₩, S$, RM) and prints CNY as "CNY 1,500". The requested "JPY 1,500" style for the UI would change about 15 existing frontend assertions; held for the owner's decision.
- A regression introduced and caught during this work: grouping digits turned "0-1000" into "0-1,000" in the no-flip sentence (pinned by `test_no_flip_reported_when_one_hotel_dominates`); restored.
- Tests: backend `test_currency_labels.py` (14; the old code fails 10 of them), frontend `currency.test.js` (7).

**Clean-clone guard**
- `scripts/check_tracked_imports.py` + `backend/tests/test_tracked_imports.py` (2 tests), `scripts/verify_clean_clone.sh` (npm script `verify:clean-clone`). Verified to fail when the original `lib/` ignore rule is restored. The list of files it checks is `docs/import-check-files.txt` (generated).
- First real run: backend 381 passed after the fix above, Vitest and `npm run build` passed from the clean clone.

## Phase 9c, Part 3: the AI is precise about place and country (2026-10-14, mocked model only)

- **Per-city prompts** (`app/llm/prompts.py`, PROMPT_VERSION 1 -> 2): fixed templates rendered with the selected city's name, country, currency and its place/hotel NAMES and aliases; never descriptions, never another city's data. For Tokyo the rendering is exactly the constants `EXTRACT_SYSTEM`, `PARSE_REPLAN_SYSTEM`, `EXPLAIN_SYSTEM`, so the existing tests that compare against those constants pass unmodified. Judgement call: names go into the SYSTEM prompt (existing tests pin that the user turn starts with `<user_request>` / `<facts>`), as reviewed repository data inside a delimited block; names with angle brackets or line breaks are refused.
- **Destination check in code** (`app/llm/destination.py`): an index of all cities, countries, areas, attractions and hotels (English and native script) is scanned against the user's text BEFORE any model call, and against the model's new optional `destination_mentioned`. Other city -> `needs_clarification` + `switch_offer`, no draft, zero model calls for explicit cases; unknown place (e.g. Bangkok) -> "not available yet" listing the cities; never auto-switches. Single words shared by several places ("gardens", "museum", "tower", "market", "lantern") are not used as evidence of a city.
- **Names**: Hangul was being stripped by `normalise` (Korean names normalised to empty); fixed. Added native-script aliases for all four packs and city/country aliases in `city.json` (new optional `CityMeta.aliases`, `country_aliases`). These aliases are my additions on sample records, not verified. Tokyo's data exists in two identical copies (`app/data/` and `app/data/cities/tokyo/`); both were edited and a test pins them equal.
- **Currency** (`app/llm/currency.py`): accepts SGD, JPY, KRW, MYR, CNY (plus the city's display currency); converts only the city's own or display currency with the labelled SAMPLE rate; a currency with no rate for the city is refused, not converted; "¥" is read through the city's currency or confirmed; "$" is always confirmed.
- **Explanations**: the grounding checker rejects names from ALL cities (`_forms(..., all_datasets)`); every explanation states its city in code ("Destination: Seoul, South Korea.", placed after the body because existing tests pin that the text starts with the template).
- **Live evaluation script** extended per city (6 new prompts per city incl. wrong-city, mixed-language, adversarial, ambiguous; per-city and overall metrics incl. raw-complied vs final-affected; N shown; small-sample caveat). `LIVE_EVAL_MAX_CALLS` raised 80 -> 150 as requested. NOT run: `--plan` reports worst case 100 calls and makes none; tests run its mechanics with a mock client and a temp output folder (`LIVE_EVAL_OUT_DIR`), so `docs/llm-live-eval.md` still does not exist.
- **Frontend**: a "Switch to <city>" button (offer only) and a "Please confirm the currency" box in both natural-language panels; one `requestCitySwitch` path and one app-level confirmation dialog (dialogs now have unique ids). Example results: `backend/scripts/show_parse_examples.py` -> `frontend/tests/fixtures/parse-examples.json`.
- **Tests**: backend `test_llm_per_city.py` (87), `test_live_eval_script.py` (5); Vitest `nl-city.test.js` (6). Mutation checks: disabling the destination check fails 36 of the 87, disabling cross-city grounding fails 12. No existing test was changed in this part.
- **Known gaps**: nothing here measures the real model; detecting an unsupported city depends on the model reporting `destination_mentioned`; NFKD normalisation drops Japanese voiced-sound marks consistently on both sides, so a few distinct kana names could collide.

## Phase 9c, Part 4: existing assertions that changed (owner-specified wording)
- `frontend/tests/e2e/core-flow.spec.js`, banner: `'Sample data: Tokyo only, fictional hotels, estimated prices and travel times. Not live quotes.'` -> `'Sample data · Tokyo · JPY · prices are examples'` (Part 4 asks for one thin banner line with the detail in a tooltip).
- same file, itinerary totals: `'Sights scheduled'` -> `'Sights covered'` (Part 4 names the header tile "sights covered (x of y)").
- Renames (Part 4 / owner decision): Evidence -> Proof and About -> How it works in unit tests (`proof.test.js`, formerly `evidence.test.js`), the e2e spec titles and links, and `sync-evidence` -> `sync-proof`. No other assertion text was changed.

## Phase 9c, Part 4: defects found by looking at the screenshots (2026-10-14)
- **Missed-sight charge not scaled per city (backend behaviour change, found in `seoul-4-itinerary`).** `MISSED_PREFERENCE_PENALTY_JPY = 3000` was applied in every city's own currency units, so the Seoul planner skipped 9 of 10 sights on a default trip. The charge is now `3 x the city's default value of time` (`app/money.py::missed_preference_penalty`): Tokyo is exactly 3,000 as before (so the Tokyo evaluation and all 493 existing tests are unchanged), Seoul 45,000 KRW, Singapore 54 SGD, Kuala Lumpur 135 MYR. Used by `/optimise`, `/compare-hotels` (including its response field), the sensitivity sweep and `/replan`. **Consequence:** `docs/city-eval-results.md` (Singapore, Seoul) was generated with the old constant and is stale until the evaluation is re-run (planned for Checkpoint 5, with Kuala Lumpur added).
- **Default sensitivity range** was a yen-sized 0-3,000 for every city ("No flip within 0-3000 KRW/h"); it is now 0 to 3x the city's default value of time (Tokyo unchanged).
- **Layout shift (Lighthouse):** the city cards arriving after load pushed the Trip page down (CLS 0.636); placeholders now reserve their space (CLS 0.03).
- The "same winner" notice on Hotels repeated the new verdict headline and was removed.

## Phase 9c, Checkpoint 3 follow-up decisions (2026-10-15)
- **Per-city examples:** `examples.json` holds a valid and an impossible example per city. The button loads the example for the selected city without switching it. Each valid example's hotel-flip flag is pinned against the real API in `test_frontend_examples.py`; the UI sentence follows that flag (Tokyo and Seoul flip; Singapore and Kuala Lumpur do not).
- **Map pins:** the drawn pin stays large; its invisible Leaflet hit area is 24 x 24 CSS px. A Playwright test measures every pin. Lighthouse itinerary accessibility is 100 with no failed audits (one local run); SAFETY_LOG row 87 is closed.
- **Frontend test summary:** `frontend/scripts/write-test-summaries.mjs` (run by `npm run test:report`) writes `docs/test-summary-frontend.json` with the git hash; Proof shows it and warns when the hash differs. Note: a committed summary cannot contain its own commit's hash, so regenerate it after the final commit and before `build:release`.
- **Missed-sight charge:** documented in `SOLVER_DESIGN.md` and on the Proof page as a judgement-call constant tuned after seeing multi-city results; `test_default_trip_schedules_at_least_six_sights_per_city` pins that every city's default trip schedules at least six sights.
- **Stale evidence:** `scripts/evidence_status.py` writes `docs/EVIDENCE-STATUS.md`; the city evaluation carries a STALE banner.
- **Lighthouse backend on :8011:** could not be reproduced (it starts and answers /health when run by hand, and the last Lighthouse run completed). The script discarded the child servers' output, so any failure showed only as a timeout; it now logs to `frontend/test-results/lighthouse-*.log` and reports a server that exits early.
- One earlier assertion edit in `nl.test.js` (label wording) was reverted: the label keeps its original wording and the original assertions pass with only the example's data path changed.

## Phase 9d, Part 1 (Checkpoint A): live AI self-check, gold set, calm AI-off box (2026-10-15)
- `backend/scripts/ai_selfcheck.py`: 5 checks per city (typical parse, wrong city, ambiguous name, currency symbol, explanation of a real computed result) through the real pipeline; gated, capped (`SELFCHECK_MAX_CALLS` = 40), aborts on a rejected key or invalid model with a plain message; writes `docs/ai-selfcheck.md` (model, PROMPT_VERSION, date, git hash, N). It has NOT been run live. Scripts live in `backend/scripts/` (they import the backend), not the repo-root `scripts/`.
- `docs/AI-MANUAL-TEST.md`: click-through checklist per city.
- `docs/eval/gold-prompts.json` (48 hand-written prompts) and `backend/scripts/score_gold.py`: per-city field accuracy. The only result so far is the rule-based stand-in (`docs/eval/gold-results-mock.md`), which is not a model measurement. A test proves every expectation is reachable (oracle = 100%).
- `backend/scripts/run_llm_live_eval.py` still used the old flat 3,000 missed-sight charge for its explanation inputs; it now uses the per-city charge.
- The AI box shows "AI is off in this deployment; the form works the same." plus a mode chip when the backend is in sample mode or the daily limit is reached.

## Phase 9f, Checkpoint 1: two-screen flow (2026-10-16)
- **Screens.** `Plan` (city chips, Describe box, essentials, sights grid beside a live map, rough preview, sticky "Plan my trip") and `Your trip` (hotel switch, verdict, four tiles, timeline and map, compare-hotels disclosure, on-click analysis, change tray). The five-step views (`CreateTrip`, `Wishlist`, `HotelCompare`, `Itinerary`) are removed; their addresses redirect.
- **One action.** `planMyTrip()` compares hotels (no sensitivity), plans the best hotel, and commits the comparison only together with its plan. `switchHotel()` re-plans in place. `runSensitivity()` is click-only. All three refuse to start while this tab has a solver request in flight.
- **Backend (approved, small).** Solver routes now run through `run_cancellable` (`app/hardening/disconnect.py`): the work runs in a worker thread while the request is watched; on disconnect `CancelToken.cancel()` calls `CpSolver.StopSearch()` and refuses solves that have not started (`app/optimiser/cancel.py`, one hook in `_solve_core`, one `except Cancelled: raise` in the alternatives probe). The default `SOLVER_CONCURRENCY` is unchanged (1). Residual race: a stop signal that lands before a solve has started is ignored, and that solve then runs to its own time limit.
- **Test-suite change outside the app.** `tests/conftest.py` gained a `loopback` marker: a test carrying it may connect to 127.0.0.1 only (needed to test a real server); everything else still has network blocked.
- **Maps.** Tiles are added only after a one-tile probe passes; otherwise pins sit on a plain background with a note. The CSP `connect-src` now includes `https://tile.openstreetmap.org` for that probe.
- **Existing tests.** Navigation and selector changes only, except three tests that exercised features the redesign removes by specification (hotel checkboxes with a Compare button; the old When/Money/Style form groups; the hotel list layout), which were replaced by equivalents for the hotel switch, Essentials/Advanced and the switch layout. See the list in the Checkpoint 1 report.
- **Not done yet (Checkpoint 2).** Describe-first AI results, refine chips, cited "Why this plan", AI-off wording beyond the existing note.

## Final phase, Stage 0: relay support (2026-10-16)
- New optional `LLM_BASE_URL`, validated by `app/llm/endpoint.py` and passed to the Anthropic SDK as `base_url`. Unset: identical to before. https only (a plain-http, credentialed or query-carrying URL is refused and the LLM stays off, so no key or text can go to an unsafe address). A trailing `/v1` or slash is stripped with a warning that names only the host.
- `/health` adds `llm_endpoint` (host only) and `llm_relay` when the LLM is on; sample-mode output is unchanged. The full URL and the key are never logged or returned.
- `ai_selfcheck.py`, `score_gold.py --live` and `run_llm_live_eval.py` stamp the model and the endpoint host, and say "served via a third-party relay" whenever the base URL is set. A rejected key now says "the key was rejected by <host>". Their gate also refuses an unsafe base URL before any call.
- Proof page: the live section now also renders `docs/ai-selfcheck.md` and `docs/eval/gold-results-live.md` when present (copied from the generated files, never a fixed provider name). How it works says, from `/health`, whether the deployment uses a gateway.
- Docs: `docs/PRIVACY.md`, README data line, `.env.example` (placeholder only), SAFETY_LOG rows 121 to 123. No live script was run; `.env` was not opened.

## Final phase, Checkpoint 1: themes, cost panel, day/event cards, map (2026-10-16)
- **Backend (additive, approved).** `app/optimiser/cost_summary.py` adds a `cost_summary` block to `/optimise` and `/replan`: per-day admissions, transport and day total, minutes at sights and travel, unknown prices by id, and trip totals (cash, rooms, cash with rooms, average travel, hotel area), computed from the same stop fields the validator re-checks. It is a separate block (not inside `SolveResult`, which clients send back under a strict schema). `backend/tests/test_cost_summary.py` checks that day totals sum to trip totals and to the validated totals for every city. The solver, schemas, data files and evaluation numbers are unchanged.
- **Themes.** One mapping (`frontend/src/lib/themes.json`) used by the UI and pinned by `backend/tests/test_themes.py`; `docs/design/themes-inventory.md` is generated from it (`backend/scripts/make_theme_inventory.py`). Resolutions: Central Market KL and Insadong go to Shopping; Tsukiji and the other food markets to Food & drink; Jewel Changi (mall) and Akihabara (retail district) to Shopping; Dongdaemun Design Plaza stays Sightseeing.
- **Plan screen.** Theme tabs (icon, label, count, "Limited in the sample data"), interests chips that only highlight, theme mix in the rough preview, theme icons on the map pins.
- **Your trip.** Getting around card, cost panel (per day, rooms, trip total in cash, budget meter, cash vs true cost), day chips, day cards, event cards with tags, one-line connectors (no transport mode is named: the data has none), a "…" menu with Move and "Skip this", map filter chips, spread-out overlapping pins, card and pin linking.
- **Cut or not done in this checkpoint.** The optional spending-money field (first on your cut list). The three-part staged progress line stays two honest stages ("Comparing hotels…", then "Planning your days and checking the plan…") because the validator runs inside the planning request. "Saved" on the map means your Must visit picks: the app cannot tell an explicit "Include if it fits" from the default.
- **Display currency.** Approximations print as "S$" (never a bare "$"), which I read as satisfying "printed with its code"; changing it to "SGD 12.34" would alter several pinned assertions and is left for your call.

## Live self-check findings (2026-10-17, model claude-haiku-4-5-20251001 via api.apiyi.com)
Run by the user's command (`RUN_LIVE_LLM_EVAL=1 scripts/ai_selfcheck.py`), results in `docs/ai-selfcheck.md`. Progress across runs, all one model, one prompt per check, so indicative only: first attempts stopped at the first call (HTTP 400, effort parameter), then 16 of 20, 18 of 20, 19 of 20 (twice, a different check each time), then 20 of 20 on two consecutive runs.
- **Effort parameter.** Haiku rejects `output_config.effort`. The user's `.env` had `LLM_EFFORT=low`, copied from `.env.example`. Fixed in code (Haiku never receives it); `.env.example` now has the line commented out.
- **Ambiguous names.** The model puts "the museum / the bay / the temple" in `interests` (as "museums", "bay", "bay views"), not in `must_visit_names`. Fixed code-side (ambiguous interests become choose-one questions). The self-check's own matching was also too literal (the fixture phrase "the bay" against the model's "bay"); it now normalises "the" and plurals.
- **Explanation grounding.** One explanation (Seoul, one run) was rejected because the model wrote "2 hours 38 minutes" for "158 min (2:38)". The checker now accepts the parts of such a duration. Earlier, a Tokyo explanation was also rejected once; its cause was not captured (the report now lists rejected tokens).
- **Not measured.** Gold-set live accuracy (`score_gold.py --live`) has not been run. The self-check is a smoke check, not a benchmark.

## Maximum-score pass, Stage 1 Tier A and B: the AI is the first thing a visitor sees (2026-10-17)
- **Plan screen.** The Describe card is now first and primary ("Ask the AI to set up your trip"). Three fill-only example prompts per city reuse the texts pinned in `backend/tests/fixtures/live_eval_prompts_by_city.json` (a unit test compares them). "What the AI understood" is built only from the validated draft (`frontend/src/lib/understood.js`).
- **Behaviour kept.** The form is still filled as soon as the AI answers (an existing unit test pins that). "Apply to my trip" re-applies the reading after you edit, focuses the form, and never plans. I did not change that behaviour because it would have changed an existing assertion.
- **Header chip** is a button with a popover. It shows the gateway host from `/health`. **The model name is not in `/health`**, so it is not shown; adding `llm_model` to `/health` is a one-line backend change that I have not made without your say-so.
- **Your trip.** The replan box moved to the top as "Ask the AI to change your plan" (chips from the current plan, ticked checklist, "Add to my changes"); "Explain this plan" sits next to the verdict. The pending-changes tray stays where it was, with a "Review and apply" link.
- **Existing tests.** No existing test was edited in this tier (see `docs/design/test-edits.md`).

## Addenda A, B, D (2026-10-17)
- **A, user-test kit.** `PROTOCOL.md` and `TEST-CARD.md` rewritten (5 to 10 target travellers, hotel choice before and after the comparison, confidence, self-estimated manual time, five ratings). New 18-column `results.csv` (header only), `scripts/add_user_test_row.py` and a rewritten `scripts/summarise_user_test.py` that reports counts and medians only. The old schema's tests were replaced (listed in `docs/design/test-edits.md`, needs your OK).
- **B, gold set.** `score_gold.py --live --label NAME` covers all 48 prompts, stamps model, gateway host, PROMPT_VERSION, date and git hash, reports per city, and writes a NEW `gold-results-live-<UTC time>-<label>.md` every run (opened with "x", so it cannot overwrite). Worst case is 48 prompts x 2 calls = 96, under the cap of 100 (tested). The Proof card and README side-by-side view are part of Tier C and Stage 6.
- **D, doc consistency.** `scripts/check_doc_consistency.py` found real contradictions: the README, EVALUATION.md, the scorecard and the facts file said the live AI had not been run, the README described Tokyo-only coverage, and the scorecard said Kuala Lumpur was not in the city evaluation although it is. All fixed from generated files. Two lines remain in the generated `docs/eval-results.md`; the generator text was fixed and that file is regenerated in the Stage 5 evidence refresh.

## Addendum C: Singapore verification (2026-10-17, web-assisted)
- **Schema (additive, approved).** `FieldVerification` / `Verification` / `HotelVerification` in `app/schemas.py`, `app/verification.py` for the counts, `verification` block on `/data/summary`. `source_status` stays "sample" everywhere. Solver and matrix are untouched.
- **What the web check could and could not do.** Official pages were fetched for Gardens by the Bay, Botanic Gardens, National Gallery, Sultan Mosque and Jewel. The Marina Bay Sands pages (SkyPark, ArtScience Museum) timed out on every attempt, the Buddha Tooth Relic Temple pages that loaded carry no hours, and no official food-centre or Sentosa page stated the record's values, so those fields stay unchecked and say why. 7 fields moved to source_checked; 0 are human_verified.
- **Three corrections** (old, new, URL, quote in `docs/data-verification/CHANGELOG.md`): Sultan Mosque hours (Friday closed; 10:00-12:00 and 14:00-16:00 otherwise), Botanic Gardens close (23:00 to midnight, stored as 23:59), National Gallery Tuesday (the sample record had it closed; the official page says daily 10am-7pm).
- **Still unchecked, and likely wrong:** the Monday closure of the Buddha Tooth Relic Temple and the Wednesday closure of the ArtScience Museum (search summaries suggest both are open daily; no fetched official page confirmed it). Sentosa's hours stay a deliberate "unknown".
- **Not done:** FX rate (no official page with a figure could be read; 0.74 unchanged, still labelled sample), travel-time calibration (no mainstream transit estimate could be read with these tools), holiday notes (the Singapore file has none). The OneMap check is written and tested with canned responses but NOT run (needs your token); the OneMap API page could not be read, so its endpoint and header are from general knowledge and the script says so.
- **Frontend fixtures** `places-singapore.json` and `optimise-cost-singapore.json` were regenerated from the corrected data (no frontend test changed). The Singapore evaluation numbers are stale until the Stage 5 refresh.

## Tier C: AI drawer and Live AI card (2026-10-17)
- **Drawer.** `frontend/src/lib/aiDrawer.js` and `AiDrawer.vue`, on parse, change proposals and explanations, using only fields the API already returns (`extracted_json`, `defaults_applied`, unresolved and ambiguous names, `grounding.rejected_tokens`, `call_count`, `prompt_version`; model and host from `/health`). Its body is rendered only when opened (an existing test requires a rejected explanation to show quietly).
- **Proof "Live AI evidence" card.** `docs/ai-selfcheck-history.md` (hand-written from the recorded findings, no new numbers), the gold first-run and after-fix files side by side, the rule-based baseline labelled, and a staleness check against the current `PROMPT_VERSION` written at sync time (`current-version.json`).
- **Gold first run** (run by you, 2026-10-17, `docs/eval/gold-results-live-first-run.md`): 48 of 48 exact, 44 calls, one model. Optimistic: hand-written prompts, pipeline tuned on similar checks, many fields decided by code.
- **Not done in this tier:** regenerated screenshots (done with the Stage 5 refresh).

## Stage 3: red team (2026-10-17, mock models only)
- **Set.** `backend/tests/fixtures/redteam_attacks.json`: 48 attacks (15 English, 11 each Korean, Chinese, Malay), 10 categories, each with id, language, category and the rule it targets. The original 8-attack `injection_prompts.json` is untouched (its test needs every entry to be a short request the pipeline accepts; over-length and cross-city attacks cannot live there), so the extended set is a new file that includes the same kinds of attacks.
- **Harness.** `backend/scripts/redteam_lib.py` + `run_redteam.py`. Writes `docs/redteam-results.md/.json`. Two mocks: gullible (emits the forbidden output for the attack's category) and harmless. "Raw tried to comply" counts only runs where the model was called (code stops wrong-city and over-length requests first, with no model call).
- **Found and fixed (2).** (1) Model free-text notes could quote the system prompt, a key-like secret or another person's email and were shown: 228 of 744 runs affected, now 0 (`app/llm/leakguard.py`, applied in `runner.call_json`). (2) An explanation quoting the prompt without numbers passed grounding: 4 runs, now 0 (`explain()` leak check). Both reproduced by the harness first; a mutation test shows the judge catches the attack again if the guard is disabled.
- **Judge caveat.** The judge flags a number of days that is not in the request. A first version flagged my own harmless mock (it always said 3 days); that was fixed in the mock, not by weakening the judge.
- **Live.** `redteam_live.py` (opt-in, 60-call cap, 27 attacks, worst case 51 calls) is written and tested with a stand-in; NOT run. Command: `cd backend && RUN_LIVE_LLM_EVAL=1 .venv/bin/python scripts/redteam_live.py`.

## Stage 5: evidence refresh and deploy-readiness (2026-10-17)
- **Order mattered.** The evaluation and city-evaluation stamp "uncommitted changes" if the tree is dirty at the start of the run, which marks them STALE in `docs/EVIDENCE-STATUS.md`. So: commit the code, run the city evaluation, commit it, run the Tokyo evaluation on the clean tree, then run the rest at that same commit (hardening, hotel comparison, replanning, Lighthouse, Vitest, Playwright, the full backend suite). All six evidence files are CURRENT.
- **Tokyo headline numbers did not change.** Comparing `docs/eval-results.json` before and after: the only differences are runtime (machine dependent) and thousands separators in one scenario's text. The solver, matrix and Tokyo data are untouched.
- **Kuala Lumpur and Seoul numbers did change**, with no data change: the previous city evaluation was generated before the per-city missed-sight penalty (Checkpoint 1), so its true-cost figures were stale. Singapore also changed because of the corrected opening hours (Addendum C).
- **Tests.** Backend 638 passed (the new `backend/tests/results/full-suite.json` holds the counts), Vitest 260 passed, Playwright (Chromium, 2 workers) 55 passed. Playwright for Firefox and WebKit was not run (you asked for Chromium only).
- **Lighthouse (mobile preset, local, unadjusted).** Plan 94 / 100 / 100, Proof 92 / 100 / 100 (performance, accessibility, best practices); "Your trip" is a snapshot, so 100 / 100 with performance not measured.
- **Release gate.** `npm run build:release` passes at this commit with a placeholder HTTPS API URL (nothing deployed).
- **Deploy files** re-read against the current code and fixed (service name, `LLM_BASE_URL`, `SOLVER_CONCURRENCY`, `LLM_EFFORT` unset, an ordered checklist at the top of `docs/DEPLOY.md`). `scripts/live-smoke.mjs` and `scripts/run-lighthouse.mjs` followed the new two-screen flow. Both smoke commands pass against a local pair (10 of 10 and 18 of 18).
