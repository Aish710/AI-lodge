# UX metrics (measured)

Generated 2026-10-17T18:17:57.492Z by `frontend/tests/e2e/flow.spec.js` at git `0b60fd9` (the code may have uncommitted changes). Chromium, production build, real backend in sample mode, local machine.

Clicks are counted from the first interaction on the Plan screen (the city was already chosen) to the plan showing on "Your trip". Time runs from the first of those clicks until the day-by-day timeline is visible.
**The times are machine-dependent** (this machine, its load at that moment, one run): treat them as a rough indication, not a benchmark. Nothing here is a user-test result.

| City | Clicks to first plan (target: at most 3) | Time to first plan |
|---|---|---|
| Tokyo | 2 | 3.0 s |
| Seoul | 2 | 1.5 s |

Path measured: "Try an example" (fills the form and sights) then "Plan my trip" (compares the hotels, then plans the best one).
