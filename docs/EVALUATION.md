# Evaluation method

How the numbers in `docs/eval-results.md` and `docs/README-claims.md` are produced, and what they can and cannot show. Run it yourself:

```
cd backend
python scripts/run_evaluation.py --quick     # 10 trips, about 25 s
python scripts/run_evaluation.py             # --full: 60 trips, about 5 minutes on the development machine
```

Outputs (in `docs/`): `eval-results.md` (report), `eval-results.json` (raw per-trip data), `eval-scenarios.json` (the exact trips, so anyone can re-run them), `README-claims.md` (sentences generated from the measured numbers), `eval-travel-minutes.csv` and `eval-hotel-gaps.csv` (chart data). Nothing in these files is typed by hand.

## What is run

- **The 15 named scenarios** from the brief, defined once in `backend/app/eval/scenarios.py`. The pytest file (`tests/test_evaluation.py`) and the script both import that module, so the report and the test results cannot disagree. Scenarios 13-15 use a scripted mock in place of the model and are labelled "mocked LLM: verifies the pipeline, not the model".
- **The solver under test** is the objective `POST /optimise` runs (true cost at the trip's value of time, default 1,000 JPY/h). A test compares the evaluation's plans with what the real route returns. The older Phase 2 weighted objective (still the default of `solve()` when called directly, used by no API route) appears only in a labelled secondary analysis (A2).
- **Generated trips** (`app/eval/generator.py`, seeded): 2-4 days, 3-9 of the 12 sample attractions in random input order, 0-3 must-visits, random start weekday, a mix of no, soft and strict budgets (some deliberately tight), each of the 3 fictional hotels as the base in turn, balanced pace. The generator's constants are judgement calls and are written into the scenario file.
- **Replanning**: the existing `scripts/run_replan_evaluation.py` is imported (`collect`, `summarise`), not re-implemented.
- **No language model is used**: explanations and natural-language parsing need a live model, so they are checked by separate opt-in scripts (`docs/ai-selfcheck.md` is a small live smoke test; `docs/llm-live-eval.md` does not exist). The evaluation never imports the real client or reads an API key (enforced by tests).

## Determinism

The solver, validator and hotel comparison are called directly, not over HTTP. CP-SAT runs with a fixed seed, one worker and its deterministic-time limit. The shipped wall-clock safety limits (20 s per solve, 5 s probes and replans, 10 s per comparison) are lifted for the evaluation (`app/eval/limits.py`) so a slower machine cannot change a plan. The same seed gives byte-identical scenarios and identical metrics; only fields named `runtime_seconds` and the `machine_dependent` block vary and are labelled as such. Solver status (OPTIMAL vs FEASIBLE) is reported for every stage.

## Baselines and the like-for-like rule

Two baselines, always reported separately and never merged:

1. **Input order** (the Phase 2 naive baseline): attractions in the user's listed order, filled day by day.
2. **Nearest neighbour** (`optimiser/baseline.py: nearest_neighbour`): from the hotel, always go to the nearest feasible unvisited attraction (open on arrival, fits the day window with the trip back, within the pace cap and any strict budget), day by day, on the same travel matrix. It has no lookahead and no must-visit priority, so a must-visit it cannot reach is reported as not placed.

A trip contributes to a travel-time comparison only if the solver and that baseline scheduled exactly the same set of attractions. Every exclusion is counted with its reason (baseline dropped sights, solver dropped sights, different sets, solver infeasible, zero baseline travel). Placement rates (what fraction of requested attractions each method scheduled) are reported alongside, because a baseline that drops sights is not comparable.

## Fair hotel baselines (Phase 1 of the improvement pass)

`backend/scripts/run_baseline_evaluation.py` writes `docs/baseline-results.md/.json`: **A** cheapest hotel first, **B** convenience first (smallest total estimated travel time to the target sights; a documented rule that ignores the day-by-day route), **C** joint optimisation. All three are read off one `/compare-hotels` call, so they share candidate hotels, constraints, estimated travel times, itinerary optimiser and objective. Each city is reported separately, at 0.5, 1, 2 and 4 times that city's OWN default value of time (the earlier city evaluation used one number in every currency, which is not like-for-like). Components are kept separate: rooms, admissions, estimated transport (their sum is the known spend), estimated travel minutes and their monetised value, optional sights left out and their charge, and the optimisation score, which is not spending. The run reproduces the historical Tokyo result (4 of 52 at the default value of time). Cities where the joint choice never differs from the cheapest are reported as such.

## Checks that do not rely on the solver's own logic

- The **independent validator** runs on every itinerary from the solver and from both baselines.
- Every infeasibility the solver reports is re-derived from the dataset in `app/eval/independent.py` (which imports nothing from the optimiser or validator), and an exhaustive search over day assignments and visiting orders confirms that no must-visit schedule exists. A schedule found by the search for a trip the solver called infeasible would be reported as a solver error.

## Reporting rules

N is given for every figure. Statistics are mean, median, min and max, plus the number of trips better / equal / worse. Rounding never favours the product: improvements and rates that favour it are rounded down, failure rates and costs are rounded up, counts are exact. No result is called significant (no test is run) and nothing is extrapolated beyond the sample. Weak, null and negative results get generated sentences that say so. Analyses added after seeing a headline result (section A2) are labelled post-hoc everywhere they appear and are not used for headline claims.

## What this does not show

Sample data with 12 attractions and 3 fictional hotels whose rates were tuned for the demo; travel times and fares estimated from straight-line distance, not routing data; synthetic trips from one seeded generator, not users; no live prices or opening hours; one machine and one OR-Tools version. The hotel result measures the model's behaviour on a demo dataset, not real hotel markets.
