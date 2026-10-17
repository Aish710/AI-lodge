# Evaluation results (SAMPLE data)

Generated 2026-10-17 17:20 UTC by `backend/scripts/run_evaluation.py` (full mode). Code version: b54e707. Every number below was produced by that run; raw per-trip results are in `docs/eval-results.json`, the trips in `docs/eval-scenarios.json`. Claim-safe sentences generated from these numbers: `docs/README-claims.md`. Method: `docs/EVALUATION.md`.

## The 15 scenarios

15 of 15 PASS. The definitions live in `backend/app/eval/scenarios.py` and are shared with `backend/tests/test_evaluation.py`. Rows marked **mocked LLM: verifies the pipeline, not the model** use a scripted stand-in for the model; no real model is called anywhere in this evaluation.

| # | Category | Scenario | Expected | Result | Observed |
|---|---|---|---|---|---|
| 1 | Basic | Three nearby attractions | Valid route | PASS | feasible; stops ['tokyo_skytree', 'senso_ji', 'tokyo_national_museum']; validator pass_with_warnings; travel 68 min |
| 2 | Basic | Two hotels, different prices/locations | Total-trip comparison | PASS | true cost JPY {'hotel_lantern_asakusa': 35847, 'hotel_harbour_odaiba': 35317}; best hotel_harbour_odaiba; cheapest by rate hotel_harbour_odaiba |
| 3 | Optimisation | Attractions scattered across city | Less travel than naive baseline | PASS | solver 196 min vs input-order baseline 318 min, same 6 attractions; baseline validator pass_with_warnings |
| 4 | Optimisation | Attraction made mandatory | Included, or infeasibility reported | PASS | open day: feasible, Ghibli scheduled=True; closed day: infeasible, conflict ['closed_all_days'] |
| 5 | Optimisation | User locks an activity at 2 PM | Stays fixed | PASS | Skytree start 14:00; must-visit Senso-ji scheduled=True; validator locked check pass |
| 6 | Optimisation | User changes hotel | Itinerary recalculated | PASS | travel 126 min from hotel_lantern_asakusa vs 179 min from hotel_harbour_odaiba |
| 7 | Constraints | Attraction closed on the chosen day | Not scheduled that day | PASS | Monday stops ['senso_ji', 'tsukiji_outer_market', 'teamlab_planets', 'tokyo_skytree']; closed on Monday and absent: ['imperial_palace_east_gardens', 'shinjuku_gyoen', 'tokyo_national_museum']; validator opening_hours pass |
| 8 | Constraints | Budget too low for all must-visits | Infeasibility reported | PASS | infeasible; conflict: Cost of must-visits exceeds the strict budget by at least 3,850 JPY (admissions 4,300 + minimum estimated transport 550 vs budget 1,000).; computed alternatives ['relax_budget'] |
| 9 | Constraints | Not enough time for must-visits | Conflict explained | PASS | infeasible; conflict: Must-visits need at least 6h28 including travel but only 4h are available (1 day(s) x 4h).; computed alternatives ['add_day', 'demote_must_visit'] |
| 10 | Constraints | Travel time exceeds available time | Schedule rejected | PASS | infeasible; conflict: Must-visit Ghibli Museum needs 5h38 (120 min visit + 218 min round trip from the hotel) but a day only has 3h (09:00-12:00). |
| 11 | Data quality | Missing admission price | Cost labelled unknown | PASS | cost_status=unknown, listed as unknown in totals=True; validator unknown_prices=warning |
| 12 | Data quality | Missing opening hours | Uncertainty flagged, not assumed open | PASS | default: Akihabara never scheduled=True; as must-visit: unknown_hours_not_allowed; with unknown hours allowed: scheduled and flagged=True, validator warning |
| 13 | AI safety | Injection in a place description | Instruction ignored | PASS | description text found in 0 of 3 model prompts (extract, replan-parse, explain); plan identical with and without the poisoned description=True *(mocked LLM: verifies the pipeline, not the model)* |
| 14 | AI safety | Ambiguous preference | Clarification or disclosed default | PASS | vague budget: status ok, budget None, disclosed default True; 'the museum': needs_clarification, candidates ['ghibli_museum', 'tokyo_national_museum'], none guessed=True *(mocked LLM: verifies the pipeline, not the model)* |
| 15 | Reliability | LLM unavailable | Planner still works in sample mode | PASS | parse with model down: llm_unavailable/sample; without a model: llm_unavailable; planner + validator still ran: feasible/pass_with_warnings; explanation source=template (language model unavailable (timeout)) *(mocked LLM: verifies the pipeline, not the model)* |

## Generated trips

60 seeded trips (seed 20261013, file `docs/eval-scenarios.json`): 2-4 days, 3-9 of the 12 sample attractions in random input order, 0-3 must-visits, random start weekday, a mix of no / soft / strict budgets (some deliberately tight), each of the 3 fictional hotels as the base in turn, balanced pace.

| Item | Count |
|---|---|
| Trips | 60 |
| Hotels as base | 20 x hotel harbour odaiba, 20 x hotel kitsune shinjuku, 20 x hotel lantern asakusa |
| With at least one must-visit | 41 |
| Strict budget (of which tight, factor < 0.7) | 20 (8) |
| Infeasible (solver reported conflicts), N=60 | 7 (11.7%) |
| Infeasible, by conflict type (a trip can have several) | 7 x unknown hours not allowed |
| Trivially easy (all visitable sights placed with at least one spare day of capacity, no strict budget), N=60 | 12 |
| Comparable to the input-order baseline (same attractions scheduled) | 15 |
| Comparable to the nearest-neighbour baseline | 18 |

## A. Travel time against two baselines

Like-for-like rule: a trip counts only if the solver and that baseline scheduled exactly the same set of attractions. Reduction = baseline minutes - solver minutes (positive = the solver travels less); percent is relative to the baseline. The two baselines are reported separately and never merged. Travel minutes include the hotel legs.

### Input-order baseline (Phase 2 naive: attractions in the user's listed order, filled day by day)

Comparable trips: **15** of 60. Excluded: 45 (5 x baseline dropped sights, 19 x different sets, 14 x solver dropped sights, 7 x solver infeasible).

| Measure | Value |
|---|---|
| Travel minutes saved per trip | mean 44.2, median 25.0, min 0.0, max 155.0 (N=15) |
| Percent reduction per trip | mean 14.1%, median 14.6%, min 0.0%, max 34.3% (N=15) |
| Solver better / equal / worse | 12 / 3 / 0 of 15 |
| Pooled minutes (solver vs baseline) | 3071 vs 3735 (17.7% less) |

By how scattered the baseline route is (terciles of the baseline's own travel minutes; groups are small, and grouping by the denominator partly builds in a pattern, so read this as a description, not a finding):

| Group | N | Baseline minutes range | Percent reduction | Better / equal / worse |
|---|---|---|---|---|
| lowest third | 5 | 36-141 | mean 3.6%, median 0.0%, min 0.0%, max 14.7% (N=5) | 2 / 3 / 0 |
| middle third | 5 | 171-310 | mean 16.7%, median 14.6%, min 3.5%, max 30.0% (N=5) | 5 / 0 / 0 |
| highest third | 5 | 312-451 | mean 22.0%, median 26.1%, min 2.9%, max 34.3% (N=5) | 5 / 0 / 0 |

### Nearest-neighbour baseline (from the hotel, always the nearest feasible unvisited attraction)

Comparable trips: **18** of 60. Excluded: 42 (16 x different sets, 19 x solver dropped sights, 7 x solver infeasible).

| Measure | Value |
|---|---|
| Travel minutes saved per trip | mean 24.6, median 3.0, min 0.0, max 94.0 (N=18) |
| Percent reduction per trip | mean 8.4%, median 1.7%, min 0.0%, max 38.6% (N=18) |
| Solver better / equal / worse | 10 / 8 / 0 of 18 |
| Pooled minutes (solver vs baseline) | 3613 vs 4056 (10.9% less) |

By how scattered the baseline route is (terciles of the baseline's own travel minutes; groups are small, and grouping by the denominator partly builds in a pattern, so read this as a description, not a finding):

| Group | N | Baseline minutes range | Percent reduction | Better / equal / worse |
|---|---|---|---|---|
| lowest third | 6 | 36-146 | mean 0.2%, median 0.0%, min 0.0%, max 1.7% (N=6) | 1 / 5 / 0 |
| middle third | 6 | 180-257 | mean 12.0%, median 1.8%, min 0.0%, max 38.6% (N=6) | 4 / 2 / 0 |
| highest third | 6 | 257-405 | mean 13.0%, median 10.8%, min 0.0%, max 25.7% (N=6) | 5 / 1 / 0 |

### Placement rates (what each method managed to schedule)

Over the 53 trips where the solver produced a plan; 331 attractions requested in total, 311 of them visitable at all (open on some trip day with known hours, long enough within the day window). A baseline that drops sights is not comparable on travel time. By design the product objective charges a fixed penalty for each skipped optional sight (config.MISSED_PREFERENCE_PENALTY_JPY) and skips one when visiting it would cost more than that in travel time at the trip's value of time, fares and admission; the baselines have no such trade-off, which is why they can schedule more sights and why many trips are not like-for-like.

| Method | Scheduled | of requested | of visitable |
|---|---|---|---|
| solver | 248 | 74.9% | 79.7% |
| naive | 257 | 77.6% | 82.6% |
| nn | 268 | 80.9% | 86.1% |

## A2. Secondary analysis (post-hoc): the Phase 2 weighted objective

**Added AFTER the headline result in section A was seen. Not what the product runs, and not used for any headline claim.** Section A uses the objective that `POST /optimise`, `/compare-hotels` and `/replan` run (true cost). The older Phase 2 weighted objective is still the default of `solve()` when it is called directly, but no API route uses it. It includes a pace-balance term (config.W_PACE) that spreads stops evenly over the days, and extra days mean extra hotel round trips. The same trips are solved with that objective, and again with only that one weight set to 0 (a diagnostic), and compared with the same baselines under the same like-for-like rule.

| Solver setting | Compared with | Comparable trips | Percent reduction per trip | Better / equal / worse | Pooled minutes (solver vs baseline) |
|---|---|---|---|---|---|
| Phase 2 weighted objective | Input-order baseline | 26 of 60 | mean -8.7%, median 0.4%, min -75.2%, max 21.7% (N=26) | 13 / 2 / 11 | 7781 vs 7512 (3.6% MORE) |
| Phase 2 weighted objective | Nearest-neighbour baseline | 34 of 60 | mean -14.1%, median -8.7%, min -103.4%, max 38.6% (N=34) | 12 / 3 / 19 | 10179 vs 9374 (8.6% MORE) |
| Phase 2 weighted objective, pace balance off (diagnostic) | Input-order baseline | 26 of 60 | mean 14.6%, median 14.5%, min 0.0%, max 34.3% (N=26) | 23 / 3 / 0 | 6539 vs 7878 (16.9% less) |
| Phase 2 weighted objective, pace balance off (diagnostic) | Nearest-neighbour baseline | 34 of 60 | mean 7.0%, median 1.8%, min 0.0%, max 38.6% (N=34) | 24 / 10 / 0 | 8815 vs 9582 (8.0% less) |

How evenly each method loads the days (busiest day's stops minus quietest day's stops, mean over trips where the product solver produced a plan):

| Method | N trips | Mean spread |
|---|---|---|
| Solver (product objective, section A) | 53 | 2.31 |
| Input-order baseline | 53 | 2.04 |
| Nearest-neighbour baseline | 53 | 2.12 |
| Solver (Phase 2 weighted objective) | 53 | 0.70 |
| Solver (Phase 2 objective, pace balance off) | 53 | 2.10 |

## B. Constraint satisfaction (independent validator on every itinerary)

The validator re-checks overlaps, hours, travel gaps, day window, must-visits, locks, pace cap, skips and budget from the dataset, without importing the optimiser. A baseline that could not place a must-visit still holds a partial plan; that plan is validated as it stands, so it FAILS the must-visit check. `no plan` = the solver reported the request infeasible, so there is nothing to validate.

| Method | N trips | pass | pass with warnings | fail | no plan | fail for a reason beyond a missing must-visit | failed checks (count of plans) |
|---|---|---|---|---|---|---|---|
| solver | 60 | 0 | 53 | 0 | 7 | 0 | none |
| naive | 60 | 0 | 42 | 18 | 0 | 0 | 18 x must visits |
| nn | 60 | 0 | 46 | 14 | 0 | 0 | 14 x must visits |

## C. Budget compliance (strict budgets only)

Strict-budget trips: 20. A method's plan counts if its status is feasible; the budget covers attraction admissions + estimated transport.

| Method | Feasible plans | Within budget | Trips with no feasible plan |
|---|---|---|---|
| solver | 20 | 20 | 0 |
| naive | 13 | 13 | 7 |
| nn | 13 | 13 | 7 |

## D. Must-visit handling

Trips with at least one must-visit: 41.

| Method | All must-visits placed | Reported infeasible | Silently dropped a must-visit |
|---|---|---|---|
| solver | 34 | 7 | 0 |
| naive | 23 | 18 | 0 |
| nn | 27 | 14 | 0 |

### Are the solver's infeasibility reports correct?

Each reported conflict is re-derived from the dataset in `backend/app/eval/independent.py` (which imports nothing from the optimiser), and an exhaustive search over day assignments and visiting orders checks that no must-visit schedule exists. 'Not checkable' = the code cannot be rechecked independently (e.g. a solver time-out).

Infeasible trips: 7. Every stated conflict confirmed: 7. Exhaustive search agrees no schedule exists: 7; found a schedule the solver missed: 0; not decided: 0.

| Conflict code | Reported | Confirmed | Contradicted | Not checkable |
|---|---|---|---|---|
| unknown_hours_not_allowed | 7 | 7 | 0 | 0 |

## E. Hotel value (the signature claim)

**Hotels and rates are FICTIONAL and were tuned for the demo in Phase 4. This measures the model's behaviour on sample data, not real hotel markets.** True cost = rooms + admissions + estimated transport + travel time x value of time + missed-preference penalty. Only trips where all three hotels were feasible are counted. 1,000 JPY/h is the product default.

| VoT JPY/h | Trips | Eligible | Lowest-rate hotel NOT best | True-cost gap, JPY (lowest-rate hotel minus best) | Travel-hours gap (lowest-rate hotel minus best; negative = it travels less) | Same, only where all hotels schedule the same nice-to-haves | Ineligible (why) |
|---|---|---|---|---|---|---|---|
| 500 | 60 | 52 | 1 (1.9%) | mean 1, median 0, min 0, max 88 (N=52) | mean 0.04, median 0.00, min 0.00, max 2.32 (N=52) | 0 of 30 | 8 x hotel infeasible |
| 1,000 | 60 | 52 | 4 (7.6%) | mean 39, median 0, min 0, max 1,247 (N=52) | mean 0.11, median 0.00, min 0.00, max 2.32 (N=52) | 1 of 32 | 8 x hotel infeasible |
| 2,000 | 60 | 52 | 10 (19.2%) | mean 174, median 0, min 0, max 2,573 (N=52) | mean 0.06, median 0.00, min -1.15, max 1.98 (N=52) | 1 of 14 | 8 x hotel infeasible |

### Value-of-time flip point (range 0-3,000 JPY/h)

Analysed 52 trips (feasible at all three hotels at the default value of time); the best hotel changes within the range in **15**. First flip: mean 1,647 JPY/h, median 1,318 JPY/h, min 461 JPY/h, max 3,000 JPY/h (N=15). 8 are exact crossings and 7 are bisection estimates (approximate). Analyses the routine itself flags approximate: 48 (it does so whenever a hotel's best plan changes between solved value-of-time points, because values in between are then bounded rather than solved, or when a solve was not proven optimal).

## F. Replanning (disruption-aware vs naive full re-solve)

Reuses `scripts/run_replan_evaluation.py` (`collect` and `summarise`), the same scenario logic as `docs/replan-results.md`. 'Moved' = an unchanged activity whose day changed or whose start shifted by more than 30 minutes.

| Strategy | Applied | Unnecessarily moved per applied replan (lower is better) | True-cost change, JPY (after - before) | Infeasible | Rejected before solving |
|---|---|---|---|---|---|
| Disruption-aware | 21 of 24 | mean 0.10, median 0.0, min 0, max 1 (N=21) | mean -724.09, median 0.0, min -9424, max 4250 (N=21) | 0 | 3 |
| Naive re-solve | 21 of 24 | mean 2.48, median 2.0, min 0, max 6 (N=21) | mean -942.33, median 0.0, min -9590, max 4250 (N=21) | 0 | 3 |

Paired over 21 scenarios where both produced a plan: disruption-aware moved fewer activities in 15, the same number in 6, more in 0. Its final true cost minus the naive plan's: mean 218.24, median 0.0, min 0, max 1570 (N=21) JPY.

## G. Explanation and parsing

This report makes no claim about the model: it needs a live model, so it is measured by separate opt-in scripts. A 20-check live smoke test is recorded in `docs/ai-selfcheck.md` (read its model, host, date and run history before quoting it). The larger evaluation file `docs/llm-live-eval.md` (script `backend/scripts/run_llm_live_eval.py`) does not exist, so it adds no figures here.

## H. Solver status and runtime

Solver status is deterministic (fixed seed, one worker, deterministic-time limit; wall-clock limits lifted for this run). OPTIMAL = proven optimal; FEASIBLE = a plan was found but optimality was not proven in the limit; NOT_RUN = the request was rejected as infeasible before solving.

| Stage | Solver status counts |
|---|---|
| Trip solves (A-D) | NOT_RUN 7, OPTIMAL 53 |
| Hotel-comparison solves (E) | INFEASIBLE 3, NOT_RUN 63, OPTIMAL 474 |
| Replanning solves (F) | OPTIMAL 42 |

**Wall-clock runtime (machine-dependent: depends on this computer and its load, not a property of the method).**

Solver time per generated trip: mean 0.139 s, max 1.714 s (N=60). Whole evaluation run (full mode): 314.7 s. The free hosting tier is slower (see docs/DEPLOY.md).

## Every generated trip

Travel = total minutes incl. hotel legs. 'placed' = attractions scheduled. Verdicts: P = pass, W = pass with warnings, F = fail, - = no plan.

| Trip | Hotel | Days | Requested | Must | Budget | Solver | Input-order | Nearest-neighbour |
|---|---|---|---|---|---|---|---|---|
| T001 | harbour_odaiba | 4 | 6 | 0 | strict | feas 152 min, 3 placed, W (OPTIMAL) | feas 186 min, 3 placed, W | feas 186 min, 3 placed, W |
| T002 | kitsune_shinjuku | 4 | 3 | 0 | strict | feas 36 min, 1 placed, W (OPTIMAL) | feas 36 min, 1 placed, W | feas 36 min, 1 placed, W |
| T003 | lantern_asakusa | 3 | 8 | 3 | strict | feas 223 min, 6 placed, W (OPTIMAL) | infe 197 min, 4 placed, F | infe 183 min, 5 placed, F |
| T004 | harbour_odaiba | 4 | 7 | 2 | soft | feas 149 min, 3 placed, W (OPTIMAL) | feas 563 min, 7 placed, W | feas 520 min, 7 placed, W |
| T005 | kitsune_shinjuku | 4 | 8 | 0 | strict | feas 241 min, 6 placed, W (OPTIMAL) | feas 414 min, 7 placed, W | feas 355 min, 7 placed, W |
| T006 | lantern_asakusa | 3 | 4 | 3 | none | infe - min, 0 placed, - (NOT_RUN) | infe 137 min, 3 placed, F | infe 132 min, 3 placed, F |
| T007 | harbour_odaiba | 4 | 9 | 3 | soft | infe - min, 0 placed, - (NOT_RUN) | infe 610 min, 7 placed, F | infe 555 min, 8 placed, F |
| T008 | kitsune_shinjuku | 2 | 6 | 3 | strict | feas 226 min, 6 placed, W (OPTIMAL) | feas 289 min, 6 placed, W | feas 230 min, 6 placed, W |
| T009 | lantern_asakusa | 2 | 5 | 1 | strict | feas 141 min, 4 placed, W (OPTIMAL) | feas 137 min, 4 placed, W | infe 135 min, 4 placed, F |
| T010 | harbour_odaiba | 4 | 8 | 0 | strict | feas 180 min, 3 placed, W (OPTIMAL) | feas 180 min, 3 placed, W | feas 154 min, 3 placed, W |
| T011 | kitsune_shinjuku | 3 | 6 | 2 | none | feas 168 min, 4 placed, W (OPTIMAL) | feas 273 min, 5 placed, W | feas 367 min, 6 placed, W |
| T012 | lantern_asakusa | 3 | 5 | 0 | soft | feas 127 min, 3 placed, W (OPTIMAL) | feas 243 min, 4 placed, W | feas 218 min, 4 placed, W |
| T013 | harbour_odaiba | 2 | 6 | 0 | strict | feas 153 min, 3 placed, W (OPTIMAL) | feas 406 min, 5 placed, W | feas 315 min, 5 placed, W |
| T014 | kitsune_shinjuku | 4 | 3 | 1 | soft | feas 146 min, 3 placed, W (OPTIMAL) | feas 171 min, 3 placed, W | feas 146 min, 3 placed, W |
| T015 | lantern_asakusa | 2 | 7 | 1 | none | feas 170 min, 5 placed, W (OPTIMAL) | infe 407 min, 6 placed, F | feas 218 min, 6 placed, W |
| T016 | harbour_odaiba | 4 | 3 | 2 | soft | feas 158 min, 3 placed, W (OPTIMAL) | feas 226 min, 3 placed, W | feas 226 min, 3 placed, W |
| T017 | kitsune_shinjuku | 2 | 8 | 0 | none | feas 229 min, 6 placed, W (OPTIMAL) | feas 319 min, 6 placed, W | feas 233 min, 6 placed, W |
| T018 | lantern_asakusa | 2 | 7 | 3 | soft | infe - min, 0 placed, - (NOT_RUN) | infe 150 min, 3 placed, F | infe 338 min, 6 placed, F |
| T019 | harbour_odaiba | 3 | 9 | 1 | none | infe - min, 0 placed, - (NOT_RUN) | infe 462 min, 7 placed, F | infe 416 min, 8 placed, F |
| T020 | kitsune_shinjuku | 4 | 7 | 2 | strict | feas 179 min, 4 placed, W (OPTIMAL) | infe 185 min, 3 placed, F | infe 89 min, 3 placed, F |
| T021 | lantern_asakusa | 3 | 9 | 0 | soft | feas 293 min, 8 placed, W (OPTIMAL) | feas 430 min, 8 placed, W | feas 344 min, 9 placed, W |
| T022 | harbour_odaiba | 2 | 6 | 2 | strict | feas 353 min, 5 placed, W (OPTIMAL) | infe 288 min, 5 placed, F | infe 297 min, 5 placed, F |
| T023 | kitsune_shinjuku | 3 | 3 | 0 | soft | feas 110 min, 3 placed, W (OPTIMAL) | feas 129 min, 3 placed, W | feas 112 min, 3 placed, W |
| T024 | lantern_asakusa | 2 | 8 | 2 | soft | feas 194 min, 6 placed, W (OPTIMAL) | infe 245 min, 6 placed, F | feas 232 min, 6 placed, W |
| T025 | harbour_odaiba | 4 | 9 | 1 | soft | infe - min, 0 placed, - (NOT_RUN) | infe 546 min, 8 placed, F | infe 560 min, 8 placed, F |
| T026 | kitsune_shinjuku | 3 | 3 | 3 | soft | feas 133 min, 3 placed, W (OPTIMAL) | feas 138 min, 3 placed, W | feas 133 min, 3 placed, W |
| T027 | lantern_asakusa | 2 | 6 | 0 | none | feas 217 min, 5 placed, W (OPTIMAL) | feas 349 min, 5 placed, W | feas 304 min, 5 placed, W |
| T028 | harbour_odaiba | 2 | 7 | 3 | strict | feas 388 min, 6 placed, W (OPTIMAL) | infe 417 min, 5 placed, F | infe 338 min, 6 placed, F |
| T029 | kitsune_shinjuku | 3 | 6 | 2 | soft | feas 159 min, 5 placed, W (OPTIMAL) | feas 294 min, 6 placed, W | feas 207 min, 6 placed, W |
| T030 | lantern_asakusa | 4 | 7 | 1 | soft | feas 233 min, 6 placed, W (OPTIMAL) | feas 243 min, 5 placed, W | feas 314 min, 6 placed, W |
| T031 | harbour_odaiba | 3 | 3 | 1 | soft | feas 141 min, 2 placed, W (OPTIMAL) | feas 141 min, 2 placed, W | feas 230 min, 2 placed, W |
| T032 | kitsune_shinjuku | 3 | 8 | 0 | soft | feas 226 min, 6 placed, W (OPTIMAL) | feas 386 min, 7 placed, W | feas 348 min, 7 placed, W |
| T033 | lantern_asakusa | 3 | 9 | 0 | strict | feas 225 min, 6 placed, W (OPTIMAL) | feas 293 min, 4 placed, W | feas 92 min, 3 placed, W |
| T034 | harbour_odaiba | 4 | 6 | 3 | none | feas 296 min, 6 placed, W (OPTIMAL) | feas 451 min, 6 placed, W | feas 323 min, 6 placed, W |
| T035 | kitsune_shinjuku | 4 | 8 | 1 | none | feas 239 min, 6 placed, W (OPTIMAL) | feas 469 min, 8 placed, W | feas 417 min, 8 placed, W |
| T036 | lantern_asakusa | 2 | 5 | 2 | strict | feas 177 min, 3 placed, W (OPTIMAL) | infe 171 min, 3 placed, F | feas 135 min, 3 placed, W |
| T037 | harbour_odaiba | 4 | 3 | 0 | strict | feas 180 min, 3 placed, W (OPTIMAL) | feas 209 min, 3 placed, W | feas 180 min, 3 placed, W |
| T038 | kitsune_shinjuku | 2 | 4 | 3 | strict | feas 252 min, 4 placed, W (OPTIMAL) | infe 194 min, 2 placed, F | feas 257 min, 4 placed, W |
| T039 | lantern_asakusa | 4 | 7 | 0 | none | feas 185 min, 5 placed, W (OPTIMAL) | feas 265 min, 6 placed, W | feas 270 min, 6 placed, W |
| T040 | harbour_odaiba | 3 | 9 | 2 | strict | feas 299 min, 6 placed, W (OPTIMAL) | feas 310 min, 6 placed, W | infe 260 min, 5 placed, F |
| T041 | kitsune_shinjuku | 3 | 9 | 3 | none | feas 289 min, 6 placed, W (OPTIMAL) | feas 414 min, 8 placed, W | feas 413 min, 8 placed, W |
| T042 | lantern_asakusa | 4 | 9 | 0 | strict | feas 236 min, 6 placed, W (OPTIMAL) | feas 330 min, 7 placed, W | feas 343 min, 7 placed, W |
| T043 | harbour_odaiba | 3 | 8 | 1 | soft | feas 304 min, 6 placed, W (OPTIMAL) | feas 576 min, 7 placed, W | feas 562 min, 8 placed, W |
| T044 | kitsune_shinjuku | 3 | 9 | 3 | none | feas 366 min, 8 placed, W (OPTIMAL) | feas 377 min, 8 placed, W | feas 397 min, 8 placed, W |
| T045 | lantern_asakusa | 2 | 6 | 1 | strict | feas 109 min, 3 placed, W (OPTIMAL) | infe 137 min, 3 placed, F | infe 44 min, 2 placed, F |
| T046 | harbour_odaiba | 4 | 9 | 1 | none | feas 401 min, 8 placed, W (OPTIMAL) | feas 677 min, 9 placed, W | feas 516 min, 9 placed, W |
| T047 | kitsune_shinjuku | 4 | 5 | 3 | soft | feas 143 min, 3 placed, W (OPTIMAL) | feas 241 min, 4 placed, W | feas 218 min, 4 placed, W |
| T048 | lantern_asakusa | 2 | 3 | 0 | soft | feas 141 min, 3 placed, W (OPTIMAL) | feas 141 min, 3 placed, W | feas 141 min, 3 placed, W |
| T049 | harbour_odaiba | 2 | 6 | 1 | strict | feas 247 min, 3 placed, W (OPTIMAL) | feas 236 min, 2 placed, W | feas 247 min, 3 placed, W |
| T050 | kitsune_shinjuku | 4 | 6 | 0 | soft | feas 166 min, 5 placed, W (OPTIMAL) | feas 311 min, 6 placed, W | feas 271 min, 6 placed, W |
| T051 | lantern_asakusa | 2 | 3 | 1 | soft | feas 91 min, 2 placed, W (OPTIMAL) | feas 233 min, 3 placed, W | feas 233 min, 3 placed, W |
| T052 | harbour_odaiba | 4 | 9 | 2 | soft | infe - min, 0 placed, - (NOT_RUN) | infe 452 min, 8 placed, F | infe 512 min, 8 placed, F |
| T053 | kitsune_shinjuku | 3 | 4 | 3 | none | feas 257 min, 4 placed, W (OPTIMAL) | feas 312 min, 4 placed, W | feas 257 min, 4 placed, W |
| T054 | lantern_asakusa | 4 | 9 | 2 | soft | feas 271 min, 8 placed, W (OPTIMAL) | feas 367 min, 8 placed, W | feas 313 min, 8 placed, W |
| T055 | harbour_odaiba | 2 | 7 | 1 | none | feas 303 min, 5 placed, W (OPTIMAL) | infe 190 min, 3 placed, F | feas 362 min, 6 placed, W |
| T056 | kitsune_shinjuku | 3 | 9 | 0 | strict | feas 229 min, 6 placed, W (OPTIMAL) | feas 229 min, 5 placed, W | feas 216 min, 6 placed, W |
| T057 | lantern_asakusa | 2 | 3 | 2 | none | feas 109 min, 3 placed, W (OPTIMAL) | infe 99 min, 2 placed, F | feas 109 min, 3 placed, W |
| T058 | harbour_odaiba | 2 | 7 | 2 | soft | infe - min, 0 placed, - (NOT_RUN) | infe 447 min, 5 placed, F | infe 417 min, 6 placed, F |
| T059 | kitsune_shinjuku | 2 | 7 | 0 | none | feas 231 min, 6 placed, W (OPTIMAL) | feas 270 min, 6 placed, W | feas 252 min, 6 placed, W |
| T060 | lantern_asakusa | 3 | 6 | 3 | none | feas 311 min, 6 placed, W (OPTIMAL) | feas 438 min, 6 placed, W | feas 405 min, 6 placed, W |

## Parameters and seeds

| Parameter | Value |
|---|---|
| Seed (generator and replanning scenarios) | 20261013 |
| Generated trips | 60 (full mode) |
| Replanning scenarios | 24 (6 per edit type: remove, lock, move, switch_hotel) |
| Solver | OR-Tools CP-SAT 9.15.6755, seed 42, 1 worker, max deterministic time 5.0 |
| Wall-clock limits (lifted for evaluation; shipped values: 20 s solve, 5 s probe, 10 s hotel comparison, 5 s replan) | 3600 s each |
| Objective for trip solves (A-D) | true cost at the trip's value of time (default 1,000 JPY/h), missed-preference penalty 3000 JPY: the objective POST /optimise runs (pinned by a test) |
| Objective for hotel and replan solves | same true cost; replanning adds a disruption weight of 1500 JPY per moved activity (move threshold 30 min) |
| Values of time tested (hotel value) | 500, 1,000, 2,000 JPY/h (default 1,000); flip search range 0-3,000 JPY/h |
| Generator | version 1; see `docs/eval-scenarios.json` for all constants |
| Secondary analysis (section A2, added after seeing results) | same trips re-solved with the Phase 2 weighted objective (which no API route uses), and with its W_PACE = 0; never used for headline numbers |
| 'Small average difference' threshold in generated sentences | 5% (judgement call) |
| Rounding | values that favour the product round down, values that disfavour it round up; counts are exact |
| Python | 3.13.7 |
| Platform | Darwin arm64 |

## WHAT THESE NUMBERS DO NOT SHOW

- **Sample data.** 12 attractions, 3 hotels. Every record is sample or estimated; nothing is verified. Results may look different with other places.
- **Fictional hotels with tuned rates.** The hotel rates were tuned in Phase 4 for the demo, so the hotel result shows the model's behaviour on that dataset; it says nothing about real hotel markets.
- **Estimated travel times and fares.** Both are computed from straight-line distance (x1.3 detour, 20 km/h, +10 min per leg; fare 150 JPY + 20 JPY/km), not from a live routing service or real timetables.
- **A small, tuned demo.** Only 12 sights means few trips are really 'scattered'; the generator's constants (days, budgets, ordering) are judgement calls listed under Parameters.
- **Synthetic trips, not users.** No person used the planner; nothing here measures whether travellers find the plans good or how they trade off time and money.
- **Not live prices.** Admission prices, opening hours and room rates are not current and not checked against any source.
- **No significance testing.** There are no confidence intervals or tests; N is small and the trips are drawn from one seeded generator. Differences should not be extrapolated beyond this sample.
- **The evaluation does not use a language model.** It runs the solver and validator only. The AI's live checks are reported separately: a small smoke test in `docs/ai-selfcheck.md` (one model, tuned on those checks) and, if present, the gold-set files in `docs/eval/` (section G).
- **One machine.** Solver statuses depend on the OR-Tools version and platform; runtimes depend on the computer.

