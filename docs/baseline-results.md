# Baseline comparison (sample data)

Generated 2026-10-17 20:14 UTC by `backend/scripts/run_baseline_evaluation.py`. Code version: bf6471c + uncommitted changes. **Seeded synthetic trips on SAMPLE data with made-up hotels and estimated travel times; not user-tested; each city reported separately, never pooled.**

Three strategies, all using the same candidate hotels, constraints, estimated travel times, itinerary optimiser and objective (`app/optimiser/baselines.py`): **A** cheapest hotel first, **B** convenience-first (the hotel with the smallest total estimated travel time to the target sights, a documented rule that looks only at hotel-to-sight times), **C** joint optimisation (the hotel whose optimised itinerary has the lowest optimisation score). The score is true cost = rooms + admissions + estimated transport + monetised travel time + a charge per optional sight left out. **It is not money spent**: the known monetary spend is reported next to it.

The value of time is varied as multiples of each city's OWN default (the earlier city evaluation used the same number, 1000, in every currency, which is not like-for-like).

## Tokyo (JPY)

60 trips; own default value of time 1,000 JPY an hour; 3 hotels with nightly rates [8500, 10500, 14000] (highest is 1.65x the lowest); 12 sights.

| Value of time | Eligible trips | C differs from A (cheapest) | C differs from B (convenience) | A equals B | Median score gain vs A | Mean gain vs A (%) | Median gain vs B | Cases with no gain vs A | Median known spend, C minus A | Median minutes saved vs A |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.5x (500) | 52 of 60 | 1 | 51 | 0 | 0.0 | 0.0 | 5065.0 | 51 | 0.0 | 0.0 |
| 1x (1,000) | 52 of 60 | 4 | 50 | 0 | 0.0 | 0.2 | 4890.0 | 48 | 0.0 | 0.0 |
| 2x (2,000) | 52 of 60 | 10 | 47 | 0 | 0.0 | 0.6 | 4516.5 | 42 | 0.0 | 0.0 |
| 4x (4,000) | 52 of 60 | 12 | 47 | 0 | 0.0 | 1.2 | 5216.0 | 40 | 0.0 | 0.0 |

**Why the cheapest hotel usually wins here (at the default value of time, 52 trips where all three hotels are feasible).** In 5 of 52 the hotel with the least travel is also the cheapest. In the others the least-travel hotel costs a median of 6000 more in rooms and saves a median of 72 minutes (worth a median of 1200 at this value of time) and 0 in missed-sight charges. The value of time at which the extra rooms would pay for themselves through time alone had a median of 5593 (n = 47; the default is 1,000). In 10 of 52 trips the hotels differ by under 15 minutes of travel.

**Does the missed-sight charge matter?** (52 trips, charge 3,000 JPY per missed sight by default.) The chosen hotel changed in 4 of 52 when the charge was removed and in 2 of 52 when it was doubled. The joint choice was the cheapest-rate hotel in 48 of 52 at the default charge and 52 of 52 with no charge.

## Singapore (SGD)

20 trips; own default value of time 18 SGD an hour; 3 hotels with nightly rates [125, 185, 260] (highest is 2.08x the lowest); 10 sights.

| Value of time | Eligible trips | C differs from A (cheapest) | C differs from B (convenience) | A equals B | Median score gain vs A | Mean gain vs A (%) | Median gain vs B | Cases with no gain vs A | Median known spend, C minus A | Median minutes saved vs A |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.5x (9) | 18 of 20 | 0 | 14 | 4 | 0.0 | 0.0 | 122.0 | 18 | 0.0 | 0.0 |
| 1x (18) | 18 of 20 | 0 | 14 | 4 | 0.0 | 0.0 | 115.0 | 18 | 0.0 | 0.0 |
| 2x (36) | 18 of 20 | 0 | 14 | 4 | 0.0 | 0.0 | 101.5 | 18 | 0.0 | 0.0 |
| 4x (72) | 18 of 20 | 2 | 14 | 4 | 0.0 | 0.4 | 85.0 | 16 | 0.0 | 0.0 |

**Why the cheapest hotel usually wins here (at the default value of time, 18 trips where all three hotels are feasible).** In 1 of 18 the hotel with the least travel is also the cheapest. In the others the least-travel hotel costs a median of 135 more in rooms and saves a median of 37 minutes (worth a median of 11 at this value of time) and 0 in missed-sight charges. The value of time at which the extra rooms would pay for themselves through time alone had a median of 312 (n = 17; the default is 18). In 3 of 18 trips the hotels differ by under 15 minutes of travel.

**Does the missed-sight charge matter?** (18 trips, charge 54 SGD per missed sight by default.) The chosen hotel changed in 0 of 18 when the charge was removed and in 0 of 18 when it was doubled. The joint choice was the cheapest-rate hotel in 18 of 18 at the default charge and 18 of 18 with no charge.

## Seoul (KRW)

20 trips; own default value of time 15,000 KRW an hour; 3 hotels with nightly rates [85000, 135000, 165000] (highest is 1.94x the lowest); 10 sights.

| Value of time | Eligible trips | C differs from A (cheapest) | C differs from B (convenience) | A equals B | Median score gain vs A | Mean gain vs A (%) | Median gain vs B | Cases with no gain vs A | Median known spend, C minus A | Median minutes saved vs A |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.5x (7,500) | 15 of 20 | 0 | 15 | 0 | 0 | 0.0 | 79237 | 15 | 0 | 0 |
| 1x (15,000) | 15 of 20 | 0 | 15 | 0 | 0 | 0.0 | 65543 | 15 | 0 | 0 |
| 2x (30,000) | 15 of 20 | 3 | 13 | 0 | 0 | 1.7 | 54543 | 12 | 0 | 0 |
| 4x (60,000) | 15 of 20 | 4 | 12 | 0 | 0 | 3.4 | 43608 | 11 | 0 | 0 |

**Why the cheapest hotel usually wins here (at the default value of time, 15 trips where all three hotels are feasible).** In 0 of 15 the hotel with the least travel is also the cheapest. In the others the least-travel hotel costs a median of 100000 more in rooms and saves a median of 129 minutes (worth a median of 32250 at this value of time) and 0 in missed-sight charges. The value of time at which the extra rooms would pay for themselves through time alone had a median of 55215 (n = 15; the default is 15,000). In 0 of 15 trips the hotels differ by under 15 minutes of travel.

**Does the missed-sight charge matter?** (15 trips, charge 45,000 KRW per missed sight by default.) The chosen hotel changed in 0 of 15 when the charge was removed and in 0 of 15 when it was doubled. The joint choice was the cheapest-rate hotel in 15 of 15 at the default charge and 15 of 15 with no charge.

## Kuala Lumpur (MYR)

20 trips; own default value of time 45 MYR an hour; 3 hotels with nightly rates [140, 220, 320] (highest is 2.29x the lowest); 10 sights.

| Value of time | Eligible trips | C differs from A (cheapest) | C differs from B (convenience) | A equals B | Median score gain vs A | Mean gain vs A (%) | Median gain vs B | Cases with no gain vs A | Median known spend, C minus A | Median minutes saved vs A |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.5x (22) | 15 of 20 | 0 | 14 | 1 | 0 | 0.0 | 151 | 15 | 0 | 0 |
| 1x (45) | 15 of 20 | 0 | 14 | 1 | 0 | 0.0 | 144 | 15 | 0 | 0 |
| 2x (90) | 15 of 20 | 0 | 14 | 1 | 0 | 0.0 | 135 | 15 | 0 | 0 |
| 4x (180) | 15 of 20 | 0 | 14 | 1 | 0 | 0.0 | 113 | 15 | 0 | 0 |

**Why the cheapest hotel usually wins here (at the default value of time, 15 trips where all three hotels are feasible).** In 1 of 15 the hotel with the least travel is also the cheapest. In the others the least-travel hotel costs a median of 160.0 more in rooms and saves a median of 21.0 minutes (worth a median of 15.5 at this value of time) and 0.0 in missed-sight charges. The value of time at which the extra rooms would pay for themselves through time alone had a median of 505.0 (n = 14; the default is 45). In 4 of 15 trips the hotels differ by under 15 minutes of travel.

**Does the missed-sight charge matter?** (15 trips, charge 135 MYR per missed sight by default.) The chosen hotel changed in 0 of 15 when the charge was removed and in 0 of 15 when it was doubled. The joint choice was the cheapest-rate hotel in 15 of 15 at the default charge and 15 of 15 with no charge.

## How to read this

- A hotel change is not a success metric. The question is whether the joint choice gives a lower score, less travel or fewer omitted sights, and what it costs in known spend. Cases with no gain are counted, not hidden.
- A lower score can come with MORE known spend (a pricier hotel, more admissions because more sights fit). Read the spend and score columns together.
- Hotels, rates, sights and travel times are sample data. The result says how the optimiser behaves on this sample, not how real hotel markets behave.
