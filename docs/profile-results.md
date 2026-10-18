# Do travel profiles change plans? (sample data)

Generated 2026-10-18 03:25 UTC by `backend/scripts/run_profile_evaluation.py`. Code version: 719e4ab + uncommitted changes. **Seeded synthetic trips on SAMPLE data with estimated travel times, the trip's own (fictional) hotel; not user-tested; per city, never pooled.**

Each profile (`frontend/src/lib/profiles.json`) is applied to a trip that is feasible with no profile and re-solved by the shipped optimiser. *Same plan* means identical days, stops and start times. *Infeasible* means the profile's limits cannot be met for that trip (reported, not hidden). Differences are profile minus no-profile (negative = less).

## Tokyo

60 trips; comparable = feasible with no profile.

| Profile | Comparable | Infeasible with profile | Same plan as no profile | Median change in est. travel (min) | Median change in sight + transport spend | Median change in sights |
|---|---|---|---|---|---|---|
| Budget-conscious | 53 | 0 | 16 of 53 | 0 | 0 | 0 |
| Relaxed | 53 | 8 | 2 of 45 | 0 | -470 | -1 |
| Sightseeing enthusiast | 53 | 0 | 13 of 53 | 0 | 0 | 0 |
| Convenience-focused | 53 | 4 | 3 of 49 | -78 | -1860 | -2 |

## Singapore

20 trips; comparable = feasible with no profile.

| Profile | Comparable | Infeasible with profile | Same plan as no profile | Median change in est. travel (min) | Median change in sight + transport spend | Median change in sights |
|---|---|---|---|---|---|---|
| Budget-conscious | 18 | 0 | 0 of 18 | 85.0 | 45.0 | 3.0 |
| Relaxed | 18 | 4 | 0 of 14 | 93.0 | 18.5 | 2.5 |
| Sightseeing enthusiast | 18 | 0 | 0 of 18 | 80.0 | 43.5 | 3.0 |
| Convenience-focused | 18 | 0 | 2 of 18 | 30.5 | 31.5 | 1.5 |

## Seoul

20 trips; comparable = feasible with no profile.

| Profile | Comparable | Infeasible with profile | Same plan as no profile | Median change in est. travel (min) | Median change in sight + transport spend | Median change in sights |
|---|---|---|---|---|---|---|
| Budget-conscious | 15 | 0 | 4 of 15 | 0 | 0 | 0 |
| Relaxed | 15 | 1 | 0 of 14 | 2.0 | 76.5 | 0.0 |
| Sightseeing enthusiast | 15 | 0 | 2 of 15 | -11 | -943 | 0 |
| Convenience-focused | 15 | 0 | 0 of 15 | -27 | -7441 | -1 |

## Kuala Lumpur

20 trips; comparable = feasible with no profile.

| Profile | Comparable | Infeasible with profile | Same plan as no profile | Median change in est. travel (min) | Median change in sight + transport spend | Median change in sights |
|---|---|---|---|---|---|---|
| Budget-conscious | 15 | 0 | 0 of 15 | 122 | 78 | 4 |
| Relaxed | 15 | 0 | 0 of 15 | 110 | 41 | 3 |
| Sightseeing enthusiast | 15 | 0 | 0 of 15 | 120 | 78 | 4 |
| Convenience-focused | 15 | 0 | 2 of 15 | 60 | 25 | 3 |

## Reading this honestly

- Where a profile gives the same plan for most trips, it changes the settings but not the outcome for those trips.
- Profile values are proposals; they were not tuned to produce these numbers.
