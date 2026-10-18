# Itinerary-planning value, separate from hotel choice (sample data)

Generated 2026-10-18 08:32 UTC by `backend/scripts/run_itinerary_study.py`. Code version: e1c1826 + uncommitted changes. **Seeded synthetic trips on SAMPLE data, estimated straight-line travel times, the trip's own (fictional) hotel fixed; not user-tested; each city reported separately, never pooled.**

Every arm uses the same data, constraints, travel matrix and scoring. *Feasible* means every must-visit is placed and the independent validator reports no failed check. *Optional coverage* is the share of the requested optional sights an arm placed. *Known spend* is admissions plus estimated transport; the *score* is the optimisation score (spending + monetised travel time + a charge per optional sight left out) and **is not money spent**. Denominators are all trips; trips where an arm has no plan are counted, not dropped.

## Tokyo

60 trips at the city's default value of time (1,000 an hour).

| Arm | Feasible | No plan | of which optimiser found a plan | Failed a check | Optional coverage (median %, N) | Median est. travel min | Median known spend ex rooms | Median score |
|---|---|---|---|---|---|---|---|---|
| Input order | 42 of 60 | 18 | 11 | 0 | 85.7 (N=41) | 291.0 | 5885.0 | 40825.0 |
| Nearest feasible | 46 of 60 | 14 | 7 | 0 | 85.7 (N=45) | 249.5 | 6115.0 | 36633.0 |
| Optimiser | 53 of 60 | 7 | 0 | 0 | 73.2 (N=52) | 217 | 4170 | 33627 |

Trips where all three arms are feasible: 40. Trips where the optimiser has no plan but a baseline does (would indicate a problem): 0.

**Optimiser vs input order, full plans** (score gain, N=40): better in 37, equal in 3, worse in 0; median gain 1974.5.
**Matched routing vs input order** (optimiser forced to the same sights; 42 of 42 feasible baseline plans): estimated travel minutes saved better/equal/worse = 37/5/0 (median 43.0, max 164); score gain better/equal/worse = 40/2/0.

**Optimiser vs nearest feasible, full plans** (score gain, N=40): better in 33, equal in 7, worse in 0; median gain 1001.5.
**Matched routing vs nearest feasible** (optimiser forced to the same sights; 46 of 46 feasible baseline plans): estimated travel minutes saved better/equal/worse = 31/15/0 (median 4.0, max 94); score gain better/equal/worse = 39/7/0.

Optimiser runtime per trip (s): median 0.05, max 1.6 (machine-dependent).

## Singapore

20 trips at the city's default value of time (18 an hour).

| Arm | Feasible | No plan | of which optimiser found a plan | Failed a check | Optional coverage (median %, N) | Median est. travel min | Median known spend ex rooms | Median score |
|---|---|---|---|---|---|---|---|---|
| Input order | 16 of 20 | 4 | 2 | 0 | 80.0 (N=16) | 198.5 | 67.5 | 456.0 |
| Nearest feasible | 17 of 20 | 3 | 1 | 0 | 80.0 (N=17) | 208 | 64 | 424 |
| Optimiser | 18 of 20 | 2 | 0 | 0 | 81.7 (N=18) | 198.0 | 65.0 | 410.0 |

Trips where all three arms are feasible: 16. Trips where the optimiser has no plan but a baseline does (would indicate a problem): 0.

**Optimiser vs input order, full plans** (score gain, N=16): better in 13, equal in 3, worse in 0; median gain 4.5.
**Matched routing vs input order** (optimiser forced to the same sights; 16 of 16 feasible baseline plans): estimated travel minutes saved better/equal/worse = 14/2/0 (median 11.5, max 87); score gain better/equal/worse = 13/3/0.

**Optimiser vs nearest feasible, full plans** (score gain, N=16): better in 11, equal in 5, worse in 0; median gain 3.0.
**Matched routing vs nearest feasible** (optimiser forced to the same sights; 17 of 17 feasible baseline plans): estimated travel minutes saved better/equal/worse = 12/5/0 (median 7, max 46); score gain better/equal/worse = 12/5/0.

Optimiser runtime per trip (s): median 0.02, max 0.12 (machine-dependent).

## Seoul

20 trips at the city's default value of time (15,000 an hour).

| Arm | Feasible | No plan | of which optimiser found a plan | Failed a check | Optional coverage (median %, N) | Median est. travel min | Median known spend ex rooms | Median score |
|---|---|---|---|---|---|---|---|---|
| Input order | 14 of 20 | 6 | 1 | 0 | 80.0 (N=14) | 161.0 | 34130.0 | 348380.5 |
| Nearest feasible | 13 of 20 | 7 | 2 | 0 | 80.0 (N=13) | 176 | 33553 | 327553 |
| Optimiser | 15 of 20 | 5 | 0 | 0 | 66.7 (N=15) | 125 | 28432 | 359682 |

Trips where all three arms are feasible: 13. Trips where the optimiser has no plan but a baseline does (would indicate a problem): 0.

**Optimiser vs input order, full plans** (score gain, N=13): better in 12, equal in 1, worse in 0; median gain 7394.
**Matched routing vs input order** (optimiser forced to the same sights; 14 of 14 feasible baseline plans): estimated travel minutes saved better/equal/worse = 12/2/0 (median 15.0, max 35); score gain better/equal/worse = 12/2/0.

**Optimiser vs nearest feasible, full plans** (score gain, N=13): better in 12, equal in 1, worse in 0; median gain 1682.
**Matched routing vs nearest feasible** (optimiser forced to the same sights; 13 of 13 feasible baseline plans): estimated travel minutes saved better/equal/worse = 10/3/0 (median 4, max 61); score gain better/equal/worse = 13/0/0.

Optimiser runtime per trip (s): median 0.01, max 0.1 (machine-dependent).

## Kuala Lumpur

20 trips at the city's default value of time (45 an hour).

| Arm | Feasible | No plan | of which optimiser found a plan | Failed a check | Optional coverage (median %, N) | Median est. travel min | Median known spend ex rooms | Median score |
|---|---|---|---|---|---|---|---|---|
| Input order | 14 of 20 | 6 | 1 | 0 | 100.0 (N=14) | 156.5 | 99.0 | 629.0 |
| Nearest feasible | 14 of 20 | 6 | 1 | 0 | 91.7 (N=14) | 152.0 | 96.5 | 649.5 |
| Optimiser | 15 of 20 | 5 | 0 | 0 | 100.0 (N=15) | 154 | 104 | 621 |

Trips where all three arms are feasible: 13. Trips where the optimiser has no plan but a baseline does (would indicate a problem): 0.

**Optimiser vs input order, full plans** (score gain, N=13): better in 9, equal in 4, worse in 0; median gain 4.
**Matched routing vs input order** (optimiser forced to the same sights; 14 of 14 feasible baseline plans): estimated travel minutes saved better/equal/worse = 11/3/0 (median 3.5, max 28); score gain better/equal/worse = 10/4/0.

**Optimiser vs nearest feasible, full plans** (score gain, N=13): better in 11, equal in 2, worse in 0; median gain 11.
**Matched routing vs nearest feasible** (optimiser forced to the same sights; 14 of 14 feasible baseline plans): estimated travel minutes saved better/equal/worse = 12/2/0 (median 10.0, max 33); score gain better/equal/worse = 12/2/0.

Optimiser runtime per trip (s): median 0.02, max 0.06 (machine-dependent).

## Reading this honestly

- A baseline that places every must-visit and passes the validator is a legitimate plan; where the optimiser ties it, that is reported as a tie.
- *Matched routing* isolates ordering and day assignment. *Full plans* also reflect which optional sights the optimiser chose to leave out, so lower travel there is not a pure saving.
- The scenarios, data and baselines were not modified to produce these numbers.
