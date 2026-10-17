# Replanning evaluation (SAMPLE data)

Generated 2026-10-17 18:16 UTC by `backend/scripts/run_replan_evaluation.py` (seed 20261013). Hotels fictional; attraction data approximate; travel times and fares estimated.

Scenarios: 24 (6 each of remove / lock / move / switch_hotel), 2-4 days, random 5-8 sight subsets with 2 must-visits, true-cost objective (VoT 1,000 JPY/h, missed penalty 3000). Disruption weight 1500 JPY per moved activity; moved = day change or start shift > 30 min; per-replan time limit 5 s.

## Summary

| Metric | (a) Disruption-aware | (b) Naive full re-solve |
|---|---|---|
| Activities unnecessarily moved (per applied replan) | mean 0.10, min 0, max 1, N=21 | mean 2.48, min 0, max 6, N=21 |
| True-cost change, JPY (after - before; negative = cheaper) | mean -724.10, min -9424, max 4250, N=21 | mean -942.33, min -9590, max 4250, N=21 |
| Solve time, s | mean 0.02, min 0.006, max 0.095, N=21 | mean 0.13, min 0.006, max 0.954, N=21 |
| Infeasible replans | 0 of 24 | 0 of 24 |
| Rejected before solving (conflicting operations) | 3 of 24 | 3 of 24 |
| Solves not proven OPTIMAL | 0 | 0 |

## Cost of stability

Over the 21 scenarios where both strategies produced a plan: disruption-aware moved fewer activities in 15, the same number in 6, more in 0. Its final true cost minus the naive plan's final true cost (JPY, always >= 0 when both are optimal): mean 218.24, min 0, max 1570, N=21.

## Every scenario

| # | Edit | Days | Hotel | Stops | Aware: status / moved / cost change / s | Naive: status / moved / cost change / s | Notes |
|---|---|---|---|---|---|---|---|
| 1 | remove | 4 | kitsune_shinjuku | 6 | applied / 0 / -2,090 / 0.0347 | applied / 5 / -2,090 / 0.1456 | not like-for-like |
| 2 | remove | 2 | harbour_odaiba | 4 | applied / 0 / -1,647 / 0.0073 | applied / 0 / -1,647 / 0.0076 | not like-for-like |
| 3 | remove | 4 | lantern_asakusa | 5 | applied / 0 / -1,930 / 0.0172 | applied / 1 / -2,673 / 0.0444 | not like-for-like; aware costs 743 JPY more than naive |
| 4 | remove | 4 | kitsune_shinjuku | 8 | applied / 0 / -404 / 0.0288 | applied / 3 / -717 / 0.3721 | not like-for-like; aware costs 313 JPY more than naive |
| 5 | remove | 2 | kitsune_shinjuku | 6 | applied / 0 / -3,280 / 0.025 | applied / 1 / -3,280 / 0.0561 | not like-for-like |
| 6 | remove | 4 | lantern_asakusa | 5 | applied / 0 / -1,217 / 0.0139 | applied / 0 / -1,217 / 0.0214 | not like-for-like |
| 7 | lock | 4 | harbour_odaiba | 3 | applied / 0 / +0 / 0.0236 | applied / 0 / +0 / 0.0335 |  |
| 8 | lock | 2 | harbour_odaiba | 4 | applied / 0 / +0 / 0.0064 | applied / 0 / +0 / 0.0057 |  |
| 9 | lock | 3 | harbour_odaiba | 6 | applied / 0 / +0 / 0.0169 | applied / 0 / +0 / 0.017 |  |
| 10 | lock | 4 | harbour_odaiba | 5 | applied / 0 / +0 / 0.0176 | applied / 2 / +0 / 0.0357 |  |
| 11 | lock | 2 | harbour_odaiba | 3 | applied / 0 / +0 / 0.0117 | applied / 0 / +0 / 0.0121 |  |
| 12 | lock | 2 | lantern_asakusa | 6 | applied / 0 / +0 / 0.0127 | applied / 2 / +0 / 0.015 |  |
| 13 | move | 3 | harbour_odaiba | 6 | applied / 0 / +487 / 0.0358 | applied / 4 / +154 / 0.0627 | not like-for-like; aware costs 333 JPY more than naive |
| 14 | move | 4 | lantern_asakusa | 5 | rejected (conflicting_operations) | rejected (conflicting_operations) |  |
| 15 | move | 3 | lantern_asakusa | 6 | applied / 1 / +86 / 0.0144 | applied / 2 / +0 / 0.0145 | aware costs 86 JPY more than naive |
| 16 | move | 3 | kitsune_shinjuku | 6 | rejected (conflicting_operations) | rejected (conflicting_operations) |  |
| 17 | move | 2 | harbour_odaiba | 6 | rejected (conflicting_operations) | rejected (conflicting_operations) |  |
| 18 | move | 3 | harbour_odaiba | 3 | applied / 0 / +1,570 / 0.0102 | applied / 2 / +0 / 0.0073 | not like-for-like; aware costs 1,570 JPY more than naive |
| 19 | switch_hotel | 4 | harbour_odaiba | 6 | applied / 0 / +4,250 / 0.0301 | applied / 3 / +4,250 / 0.3096 |  |
| 20 | switch_hotel | 3 | kitsune_shinjuku | 5 | applied / 0 / -6,327 / 0.018 | applied / 4 / -7,123 / 0.0333 | aware costs 796 JPY more than naive |
| 21 | switch_hotel | 2 | lantern_asakusa | 6 | applied / 0 / +3,440 / 0.0312 | applied / 5 / +3,247 / 0.1245 | aware costs 193 JPY more than naive |
| 22 | switch_hotel | 4 | kitsune_shinjuku | 6 | applied / 0 / -9,424 / 0.0946 | applied / 6 / -9,590 / 0.9535 | aware costs 166 JPY more than naive |
| 23 | switch_hotel | 2 | kitsune_shinjuku | 6 | applied / 1 / -2,350 / 0.0249 | applied / 6 / -2,646 / 0.0325 | aware costs 296 JPY more than naive |
| 24 | switch_hotel | 4 | harbour_odaiba | 6 | applied / 0 / +3,630 / 0.0419 | applied / 6 / +3,543 / 0.4343 | aware costs 87 JPY more than naive |

Notes: a `lock` edit here locks an activity at its CURRENT slot, so it changes nothing by itself (cost change 0) and mainly tests that other activities stay put; `move` edits that conflict with opening hours, travel time or other constraints are rejected before solving (counted separately, not as infeasible). Cost changes are not like-for-like when optional sights change (flagged per scenario). A shift of 30 minutes or less does not count as moved.
