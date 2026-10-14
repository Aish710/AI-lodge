# Submission facts (generated)

Generated 2026-10-14 07:17 UTC by `frontend/scripts/make-submission-facts.mjs`. Each line is copied from a generated file (named beside it); anything not available says "not measured". Re-run the full backend suite, frontend tests, evaluation and Lighthouse before release; do not edit by hand.

## Tests

- Backend full suite: 301 passed, 0 failed, 0 skipped, 301 total (pytest), revision a1a9cb6a72d3140c8983e570fadf366c0a38df3c + uncommitted changes.
  *Source: backend/tests/results/latest-full.md*
- Frontend unit and component tests: 119 passed, 0 failed, 119 total (Vitest).
  *Source: frontend/test-results/vitest.json (npm run test:report)*
- End-to-end tests against the real backend in sample mode: 16 passed, 0 failed (Playwright).
  *Source: frontend/test-results/playwright.json (npm run test:report)*

## Evaluation

- Evaluation run 2026-10-14 06:57 UTC, code version 859c357 + uncommitted changes (this hash does not identify the exact code), mode full, 60 seeded synthetic trips on sample data (12 attractions, 3 fictional hotels).
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

- Home (create trip) (navigation): performance 99, accessibility 100, best practices 100. Measured with lighthouse 13.5.0, mobile (default), simulated throttling, on a local machine.
  *Source: docs/lighthouse-summary.json (docs/lighthouse-results.md)*
- Evidence (navigation): performance 98, accessibility 100, best practices 100. Measured with lighthouse 13.5.0, mobile (default), simulated throttling, on a local machine.
  *Source: docs/lighthouse-summary.json (docs/lighthouse-results.md)*
- Itinerary (after the example flow) (snapshot): performance not measured, accessibility 97, best practices 100. Measured with lighthouse 13.5.0, mobile (default), simulated throttling, on a local machine.
  *Source: docs/lighthouse-summary.json (docs/lighthouse-results.md)*

## Safety

- 95 risks are tracked in the safety log, each with a safeguard, the test names that check it, and a status.
  *Source: docs/SAFETY_LOG.md*
- API hardening: 33 of 33 in-process abuse cases passed.
  *Source: docs/hardening-results.md*

## Not measured

- AI parsing and explanation quality with a live model (the opt-in live evaluation has not been run).
  *Source: docs/llm-live-eval.md (absent)*
- Any user study or real-user outcome; real hotel markets; live prices or opening hours.
- Backend cold-start time on the free host and the Docker image build (neither has been run).
  *Source: docs/DEPLOY.md*
