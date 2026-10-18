# Submission facts (generated)

Generated 2026-10-18 08:25 UTC by `frontend/scripts/make-submission-facts.mjs`. Each line is copied from a generated file (named beside it); anything not available says "not measured". Re-run the full backend suite, frontend tests, evaluation and Lighthouse before release; do not edit by hand.

## Tests

- Backend full suite: 1126 passed, 2 failed, 0 skipped, 1128 total (pytest), revision ac314251c96794f74277cee5c8d73b0b0fad9f65 + uncommitted changes.  
  *Source: backend/tests/results/latest-full.md*
- Frontend unit and component tests: 395 passed, 0 failed, 395 total (Vitest).  
  *Source: frontend/test-results/vitest.json (npm run test:report)*
- End-to-end tests against the real backend in sample mode: 78 passed, 0 failed (Playwright).  
  *Source: frontend/test-results/playwright.json (npm run test:report)*

## Evaluation

- Evaluation run 2026-10-18 07:26 UTC, code version ac31425 + uncommitted changes (this hash does not identify the exact code), mode full, 60 seeded synthetic trips on sample data (12 attractions, 3 fictional hotels).  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- 15 of 15 named scenarios pass (3 of them use a scripted stand-in for the AI: they verify the pipeline, not the model).  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Travel time vs the input-order baseline, on the 15 of 60 trips where both scheduled the same sights: mean 14.1% less (median 14.6%, range 0.0% to 34.3%); better on 12, equal on 3, worse on 0. Sample data; not a claim about real trips.  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Travel time vs the nearest-neighbour baseline, on the 18 of 60 trips where both scheduled the same sights: mean 8.4% less (median 1.7%, range 0.0% to 38.6%); better on 10, equal on 8, worse on 0. Sample data; not a claim about real trips.  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Independent validator: 53 of 53 optimiser plans passed, 0 failed (7 trips had no plan because the request was infeasible). Input-order baseline: 18 of 60 plans failed, 0 for a reason beyond a missing must-visit. Nearest-neighbour: 14 of 60, 0 beyond a missing must-visit.  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Strict budgets (20 trips): 20 of 20 optimiser plans within budget.  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Of 7 infeasibility reports, every stated conflict matched an independent recomputation in 7; exhaustive search found a schedule the optimiser missed in 0. All 7 were one conflict type (unknown_hours_not_allowed).  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Hotel value at 500 JPY/h: the lowest-rate hotel was not the best by true cost in 1 of 52 trips (1.9%). Hotels and rates are fictional and were tuned for the demo.  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Hotel value at 1,000 JPY/h: the lowest-rate hotel was not the best by true cost in 4 of 52 trips (7.6%). Hotels and rates are fictional and were tuned for the demo.  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Hotel value at 2,000 JPY/h: the lowest-rate hotel was not the best by true cost in 10 of 52 trips (19.2%). Hotels and rates are fictional and were tuned for the demo.  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Replanning (21 paired scenarios): disruption-aware moved fewer activities in 15, the same in 6, more in 0; mean moved 0.1 (aware) vs 2.4 (naive).  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*
- Solver status on trip solves: OPTIMAL 53, NOT_RUN 7.  
  *Source: docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)*

## Lighthouse

- Plan (home) (navigation): performance 91, accessibility 100, best practices 100. Measured with lighthouse 13.5.0, mobile (default), simulated throttling, on a local machine.  
  *Source: docs/lighthouse-summary.json (docs/lighthouse-results.md)*
- Proof (navigation): performance 89, accessibility 100, best practices 100. Measured with lighthouse 13.5.0, mobile (default), simulated throttling, on a local machine.  
  *Source: docs/lighthouse-summary.json (docs/lighthouse-results.md)*
- Your trip (after the example flow) (snapshot): performance not measured, accessibility 100, best practices 100. Measured with lighthouse 13.5.0, mobile (default), simulated throttling, on a local machine.  
  *Source: docs/lighthouse-summary.json (docs/lighthouse-results.md)*

## Safety

- 172 risks are tracked in the safety log, each with a safeguard, the test names that check it, and a status.  
  *Source: docs/SAFETY_LOG.md*
- API hardening: 33 of 33 in-process abuse cases passed.  
  *Source: docs/hardening-results.md*
- Red team (SIMULATED models, not a real model): 60 attacks in 4 languages x 4 cities x 2 mock models = 840 runs; final result affected in 0 after 4 fixes found by the red team itself.  
  *Source: docs/redteam-results.json*
- A live red-team report exists; read its model, date and N before quoting it.  
  *Source: docs/redteam-live.md*

## Product

- 4 sample city packs: kuala_lumpur, seoul, singapore, tokyo. One city per trip; all records are labelled sample data and none is labelled verified.  
  *Source: backend/app/data/cities/*
- In-app pages: Plan, Your trip, Proof (measured results, hardening, risk table, live AI checks, user-test card) and How it works (architecture, how the AI is used, limitations, privacy).  
  *Source: frontend/src/router.js*
- 36 step screenshots (two cities, desktop and mobile, plus the Proof and How it works pages) in docs/screenshots/steps/.  
  *Source: docs/screenshots/steps/*

## Not measured

- Any user study or real-user outcome: the user-test kit exists but no result has been collected (the Proof page says "Not run yet").  
  *Source: docs/user-test/ (results.csv has no rows)*
- Real hotel markets; live prices or opening hours.
- Backend cold-start time on the free host and the Docker image build (neither has been run).  
  *Source: docs/DEPLOY.md*

## AI evaluation

- A live smoke test is recorded in docs/ai-selfcheck.md: 19 of 20 checks passed in the latest run, model claude-haiku-4-5-20251001, via api.apiyi.com. It is a small check on one model, tuned on those checks, not a benchmark. The larger evaluation file docs/llm-live-eval.md does not exist.  
  *Source: docs/ai-selfcheck.md*
- Gold-set live run (first run, hand-written prompts, one model claude-haiku-4-5-20251001 via api.apiyi.com, 44 model calls): Tokyo 12 of 12 exact; Singapore 12 of 12 exact; Seoul 12 of 12 exact; Kuala Lumpur 12 of 12 exact. Small sample per city; the pipeline had been tuned on similar checks, so treat it as optimistic.  
  *Source: docs/eval/gold-results-live-first-run.md*
- Gold-set live run (latest run, same model and prompts, a later code version): Tokyo 12 of 12 exact; Singapore 12 of 12 exact; Seoul 12 of 12 exact; Kuala Lumpur 11 of 12 exact.  
  *Source: docs/eval/gold-results-live-20261018T043721Z-final4.md*

## Data

- Singapore: 7 fields source-checked, 0 rows human-verified, 75 unchecked; other cities unchecked; all data is still sample data.  
  *Source: docs/data-verification/counts.json*
