# Replanning evaluation (SAMPLE data)

Generated 2026-10-17 17:21 UTC by `backend/scripts/run_replan_evaluation.py` (seed 20261013). Hotels fictional; attraction data approximate; travel times and fares estimated.

Scenarios: 24 (6 each of remove / lock / move / switch_hotel), 2-4 days, random 5-8 sight subsets with 2 must-visits, true-cost objective (VoT 1,000 JPY/h, missed penalty 3000). Disruption weight 1500 JPY per moved activity; moved = day change or start shift > 30 min; per-replan time limit 5 s.

## Summary

| Metric | (a) Disruption-aware | (b) Naive full re-solve |
|---|---|---|
| Activities unnecessarily moved (per applied replan) | mean 0.10, min 0, max 1, N=21 | mean 2.48, min 0, max 6, N=21 |
| True-cost change, JPY (after - before; negative = cheaper) | mean -724.10, min -9424, max 4250, N=21 | mean -942.33, min -9590, max 4250, N=21 |
| Solve time, s | mean 0.03, min 0.007, max 0.099, N=21 | mean 0.16, min 0.006, max 1.027, N=21 |
| Infeasible replans | 0 of 24 | 0 of 24 |
| Rejected before solving (conflicting operations) | 3 of 24 | 3 of 24 |
| Solves not proven OPTIMAL | 0 | 0 |

## Cost of stability

Over the 21 scenarios where both strategies produced a plan: disruption-aware moved fewer activities in 15, the same number in 6, more in 0. Its final true cost minus the naive plan's final true cost (JPY, always >= 0 when both are optimal): mean 218.24, min 0, max 1570, N=21.

## Every scenario

| # | Edit | Days | Hotel | Stops | Aware: status / moved / cost change / s | Naive: status / moved / cost change / s | Notes |
|---|---|---|---|---|---|---|---|
| 1 | remove | 4 | kitsune_shinjuku | 6 | applied / 0 / -2,090 / 0.0357 | applied / 5 / -2,090 / 0.1442 | not like-for-like |
| 2 | remove | 2 | harbour_odaiba | 4 | applied / 0 / -1,647 / 0.0066 | applied / 0 / -1,647 / 0.0075 | not like-for-like |
| 3 | remove | 4 | lantern_asakusa | 5 | applied / 0 / -1,930 / 0.0223 | applied / 1 / -2,673 / 0.049 | not like-for-like; aware costs 743 JPY more than naive |
| 4 | remove | 4 | kitsune_shinjuku | 8 | applied / 0 / -404 / 0.0301 | applied / 3 / -717 / 0.8546 | not like-for-like; aware costs 313 JPY more than naive |
| 5 | remove | 2 | kitsune_shinjuku | 6 | applied / 0 / -3,280 / 0.0297 | applied / 1 / -3,280 / 0.0633 | not like-for-like |
| 6 | remove | 4 | lantern_asakusa | 5 | applied / 0 / -1,217 / 0.0147 | applied / 0 / -1,217 / 0.023 | not like-for-like |
| 7 | lock | 4 | harbour_odaiba | 3 | applied / 0 / +0 / 0.0241 | applied / 0 / +0 / 0.0331 |  |
| 8 | lock | 2 | harbour_odaiba | 4 | applied / 0 / +0 / 0.0072 | applied / 0 / +0 / 0.0058 |  |
| 9 | lock | 3 | harbour_odaiba | 6 | applied / 0 / +0 / 0.0177 | applied / 0 / +0 / 0.0169 |  |
| 10 | lock | 4 | harbour_odaiba | 5 | applied / 0 / +0 / 0.0185 | applied / 2 / +0 / 0.0398 |  |
| 11 | lock | 2 | harbour_odaiba | 3 | applied / 0 / +0 / 0.0131 | applied / 0 / +0 / 0.0126 |  |
| 12 | lock | 2 | lantern_asakusa | 6 | applied / 0 / +0 / 0.013 | applied / 2 / +0 / 0.0155 |  |
| 13 | move | 3 | harbour_odaiba | 6 | applied / 0 / +487 / 0.0364 | applied / 4 / +154 / 0.0638 | not like-for-like; aware costs 333 JPY more than naive |
| 14 | move | 4 | lantern_asakusa | 5 | rejected (conflicting_operations) | rejected (conflicting_operations) |  |
| 15 | move | 3 | lantern_asakusa | 6 | applied / 1 / +86 / 0.0139 | applied / 2 / +0 / 0.0137 | aware costs 86 JPY more than naive |
| 16 | move | 3 | kitsune_shinjuku | 6 | rejected (conflicting_operations) | rejected (conflicting_operations) |  |
| 17 | move | 2 | harbour_odaiba | 6 | rejected (conflicting_operations) | rejected (conflicting_operations) |  |
| 18 | move | 3 | harbour_odaiba | 3 | applied / 0 / +1,570 / 0.0106 | applied / 2 / +0 / 0.0076 | not like-for-like; aware costs 1,570 JPY more than naive |
| 19 | switch_hotel | 4 | harbour_odaiba | 6 | applied / 0 / +4,250 / 0.0302 | applied / 3 / +4,250 / 0.3132 |  |
| 20 | switch_hotel | 3 | kitsune_shinjuku | 5 | applied / 0 / -6,327 / 0.0235 | applied / 4 / -7,123 / 0.0371 | aware costs 796 JPY more than naive |
| 21 | switch_hotel | 2 | lantern_asakusa | 6 | applied / 0 / +3,440 / 0.0298 | applied / 5 / +3,247 / 0.1317 | aware costs 193 JPY more than naive |
| 22 | switch_hotel | 4 | kitsune_shinjuku | 6 | applied / 0 / -9,424 / 0.0985 | applied / 6 / -9,590 / 1.027 | aware costs 166 JPY more than naive |
| 23 | switch_hotel | 2 | kitsune_shinjuku | 6 | applied / 1 / -2,350 / 0.0281 | applied / 6 / -2,646 / 0.0351 | aware costs 296 JPY more than naive |
| 24 | switch_hotel | 4 | harbour_odaiba | 6 | applied / 0 / +3,630 / 0.048 | applied / 6 / +3,543 / 0.458 | aware costs 87 JPY more than naive |

Notes: a `lock` edit here locks an activity at its CURRENT slot, so it changes nothing by itself (cost change 0) and mainly tests that other activities stay put; `move` edits that conflict with opening hours, travel time or other constraints are rejected before solving (counted separately, not as infeasible). Cost changes are not like-for-like when optional sights change (flagged per scenario). A shift of 30 minutes or less does not count as moved.
