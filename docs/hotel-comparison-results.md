# Hotel comparison results (SAMPLE data)

Generated 2026-10-18 08:38 UTC by `backend/scripts/run_hotel_comparison.py`. Hotels are FICTIONAL; attraction data is approximate sample data; travel times and fares are ESTIMATES. Not live prices.

Settings: value of time 1,000 JPY/h unless stated; missed-preference penalty 3000 JPY per visitable nice-to-have not scheduled (a judgement call, not data); nights = days - 1; sensitivity range 0-3000 JPY/h. Reported results use a 120 s limit; the default API limit (10 s) is reported per trip.

Hotel nightly rates (JPY, fictional): Hotel Kitsune Shinjuku (fictional) 14,000, Asakusa Lantern Inn (fictional) 10,500, Odaiba Harbour Stay (fictional) 8,500

## Trip A: 2 days, Sat-Sun

Must-visits: senso_ji, shibuya_sky. Pace: balanced. Nights used: 1 (default (days - 1)).

| Line (JPY) | Hotel Kitsune Shinjuku (fictional) | Asakusa Lantern Inn (fictional) | Odaiba Harbour Stay (fictional) |
|---|---|---|---|
| Rooms | 14,000 | 10,500 | 8,500 |
| Admissions (known prices) | 2,700 | 2,700 | 2,200 |
| Transport (estimated) | 1,990 | 2,140 | 2,670 |
| Travel minutes | 201 | 225 | 302 |
| Time cost | 3,350 | 3,750 | 5,033 |
| Missed-preference penalty | 15,000 | 15,000 | 15,000 |
| **True cost** | 37,040 | 34,090 | 33,403 |
| Missed (count) | 5 | 5 | 5 |
| Solver status | feasible / OPTIMAL / 0.1045s | feasible / OPTIMAL / 0.2027s | feasible / OPTIMAL / 0.1316s |

- Cheapest by rate: **Odaiba Harbour Stay (fictional)**; best by true cost: **Odaiba Harbour Stay (fictional)**; rate winner differs from true winner: **False**.
- Insight: Odaiba Harbour Stay (fictional) is both the cheapest per night and the best by true cost; it is 687 JPY cheaper in total than Asakusa Lantern Inn (fictional).
- Warning: Odaiba Harbour Stay (fictional): price unknown for teamlab_planets; excluded from totals, so true cost is understated by an unknown amount (the optimiser assumed a placeholder of 500 JPY each, not included in the totals shown).
- Warning: Not like-for-like: hotels schedule different nice-to-have attractions (Hotel Kitsune Shinjuku (fictional): misses Tokyo Skytree, teamLab Planets, Tokyo National Museum, Tokyo Tower, Ghibli Museum; Asakusa Lantern Inn (fictional): misses Tokyo Skytree, teamLab Planets, Tokyo National Museum, Tokyo Tower, Ghibli Museum; Odaiba Harbour Stay (fictional): misses Tokyo Skytree, Tokyo National Museum, Shinjuku Gyoen, Tokyo Tower, Ghibli Museum). Compare missed preferences side by side.
- Sensitivity: ranking flips from hotel_harbour_odaiba to hotel_lantern_asakusa at about 1,535 JPY/h (exact_crossing). Approximate: False. Solves: 6, cache hits: 0.

| Value of time (JPY/h) | Hotel Kitsune Shinjuku (fictional) | Asakusa Lantern Inn (fictional) | Odaiba Harbour Stay (fictional) | Winner |
|---|---|---|---|---|
| 0 | 33,690 | 30,340 | 28,370 | Odaiba Harbour Stay (fictional) |
| 500 | 35,365 | 32,215 | 30,887 | Odaiba Harbour Stay (fictional) |
| 1,000 | 37,040 | 34,090 | 33,403 | Odaiba Harbour Stay (fictional) |
| 1,500 | 38,715 | 35,965 | 35,920 | Odaiba Harbour Stay (fictional) |
| 2,000 | 40,390 | 37,840 | 38,437 | Asakusa Lantern Inn (fictional) |
| 2,500 | 42,065 | 39,715 | 40,953 | Asakusa Lantern Inn (fictional) |
| 3,000 | 43,740 | 41,590 | 43,470 | Asakusa Lantern Inn (fictional) |

- Default-limit run (10 s): elapsed 1.143s, partial: False, approximate: False.
- Extended run: elapsed 1.136s, partial: False.

## Trip B: 3 days, Wed-Fri

Must-visits: senso_ji, meiji_jingu, tokyo_national_museum. Pace: balanced. Nights used: 2 (default (days - 1)).

| Line (JPY) | Hotel Kitsune Shinjuku (fictional) | Asakusa Lantern Inn (fictional) | Odaiba Harbour Stay (fictional) |
|---|---|---|---|
| Rooms | 28,000 | 21,000 | 17,000 |
| Admissions (known prices) | 5,200 | 5,100 | 5,100 |
| Transport (estimated) | 3,000 | 3,010 | 3,790 |
| Travel minutes | 304 | 304 | 424 |
| Time cost | 5,067 | 5,067 | 7,067 |
| Missed-preference penalty | 6,000 | 6,000 | 6,000 |
| **True cost** | 47,267 | 40,177 | 38,957 |
| Missed (count) | 2 | 2 | 2 |
| Solver status | feasible / OPTIMAL / 0.6718s | feasible / OPTIMAL / 1.1165s | feasible / OPTIMAL / 0.9151s |

- Cheapest by rate: **Odaiba Harbour Stay (fictional)**; best by true cost: **Odaiba Harbour Stay (fictional)**; rate winner differs from true winner: **False**.
- Insight: Odaiba Harbour Stay (fictional) is both the cheapest per night and the best by true cost; it is 1,220 JPY cheaper in total than Asakusa Lantern Inn (fictional).
- Warning: Hotel Kitsune Shinjuku (fictional): price unknown for teamlab_planets; excluded from totals, so true cost is understated by an unknown amount (the optimiser assumed a placeholder of 500 JPY each, not included in the totals shown).
- Warning: Asakusa Lantern Inn (fictional): price unknown for teamlab_planets; excluded from totals, so true cost is understated by an unknown amount (the optimiser assumed a placeholder of 500 JPY each, not included in the totals shown).
- Warning: Odaiba Harbour Stay (fictional): price unknown for teamlab_planets; excluded from totals, so true cost is understated by an unknown amount (the optimiser assumed a placeholder of 500 JPY each, not included in the totals shown).
- Warning: Not like-for-like: hotels schedule different nice-to-have attractions (Hotel Kitsune Shinjuku (fictional): misses Tokyo Skytree, Ghibli Museum; Asakusa Lantern Inn (fictional): misses Shibuya Sky, Ghibli Museum; Odaiba Harbour Stay (fictional): misses Shibuya Sky, Ghibli Museum). Compare missed preferences side by side.
- Warning: Sensitivity analysis is approximate: Refinement stopped early (depth, solve cap or time limit): values between solved points are upper bounds.
- Sensitivity: ranking flips from hotel_harbour_odaiba to hotel_lantern_asakusa at about 1,610 JPY/h (bisection_estimate). Approximate: True. Solves: 27, cache hits: 0.

| Value of time (JPY/h) | Hotel Kitsune Shinjuku (fictional) | Asakusa Lantern Inn (fictional) | Odaiba Harbour Stay (fictional) | Winner |
|---|---|---|---|---|
| 0 | 41,480 | 34,700 | 31,420 | Odaiba Harbour Stay (fictional) |
| 500 | 44,613 | 37,642 | 35,423 | Odaiba Harbour Stay (fictional) |
| 1,000 | 47,267 | 40,177 | 38,957 | Odaiba Harbour Stay (fictional) |
| 1,500 | 49,760 | 42,710 | 42,490 | Odaiba Harbour Stay (fictional) |
| 2,000 | 52,093 | 45,243 | 45,803 | Asakusa Lantern Inn (fictional) |
| 2,500 | 54,427 | 47,532 | 48,337 | Asakusa Lantern Inn (fictional) |
| 3,000 | 56,760 | 49,640 | 50,870 | Asakusa Lantern Inn (fictional) |

- Default-limit run (10 s): elapsed 10.008s, partial: True, approximate: True.
- Extended run: elapsed 24.759s, partial: False.

## Trip C: 4 days, Thu-Sun

Must-visits: ghibli_museum, teamlab_planets, tsukiji_outer_market, shinjuku_gyoen. Pace: relaxed. Nights used: 3 (default (days - 1)).

| Line (JPY) | Hotel Kitsune Shinjuku (fictional) | Asakusa Lantern Inn (fictional) | Odaiba Harbour Stay (fictional) |
|---|---|---|---|
| Rooms | 42,000 | 31,500 | 25,500 |
| Admissions (known prices) | 2,500 | 2,500 | 2,500 |
| Transport (estimated) | 3,680 | 3,850 | 4,970 |
| Travel minutes | 406 | 433 | 599 |
| Time cost | 6,767 | 7,217 | 9,983 |
| Missed-preference penalty | 9,000 | 9,000 | 9,000 |
| **True cost** | 63,947 | 54,067 | 51,953 |
| Missed (count) | 3 | 3 | 3 |
| Solver status | feasible / OPTIMAL / 0.2727s | feasible / OPTIMAL / 0.2252s | feasible / OPTIMAL / 0.3004s |

- Cheapest by rate: **Odaiba Harbour Stay (fictional)**; best by true cost: **Odaiba Harbour Stay (fictional)**; rate winner differs from true winner: **False**.
- Insight: Odaiba Harbour Stay (fictional) is both the cheapest per night and the best by true cost; it is 2,114 JPY cheaper in total than Asakusa Lantern Inn (fictional).
- Warning: Hotel Kitsune Shinjuku (fictional): price unknown for teamlab_planets; excluded from totals, so true cost is understated by an unknown amount (the optimiser assumed a placeholder of 500 JPY each, not included in the totals shown).
- Warning: Asakusa Lantern Inn (fictional): price unknown for teamlab_planets; excluded from totals, so true cost is understated by an unknown amount (the optimiser assumed a placeholder of 500 JPY each, not included in the totals shown).
- Warning: Odaiba Harbour Stay (fictional): price unknown for teamlab_planets; excluded from totals, so true cost is understated by an unknown amount (the optimiser assumed a placeholder of 500 JPY each, not included in the totals shown).
- Warning: Sensitivity analysis is approximate: Refinement stopped early (depth, solve cap or time limit): values between solved points are upper bounds.
- Sensitivity: ranking flips from hotel_harbour_odaiba to hotel_lantern_asakusa at about 1,912 JPY/h (bisection_estimate); ranking flips from hotel_lantern_asakusa to hotel_harbour_odaiba at about 2,136 JPY/h (bisection_estimate). Approximate: True. Solves: 18, cache hits: 0.

| Value of time (JPY/h) | Hotel Kitsune Shinjuku (fictional) | Asakusa Lantern Inn (fictional) | Odaiba Harbour Stay (fictional) | Winner |
|---|---|---|---|---|
| 0 | 57,180 | 46,850 | 41,970 | Odaiba Harbour Stay (fictional) |
| 500 | 60,563 | 50,458 | 46,962 | Odaiba Harbour Stay (fictional) |
| 1,000 | 63,947 | 54,067 | 51,953 | Odaiba Harbour Stay (fictional) |
| 1,500 | 67,330 | 57,675 | 56,945 | Odaiba Harbour Stay (fictional) |
| 2,000 | 70,713 | 61,283 | 61,330 | Asakusa Lantern Inn (fictional) |
| 2,500 | 73,968 | 64,892 | 64,243 | Odaiba Harbour Stay (fictional) |
| 3,000 | 76,510 | 68,500 | 66,960 | Odaiba Harbour Stay (fictional) |

- Default-limit run (10 s): elapsed 4.726s, partial: False, approximate: True.
- Extended run: elapsed 4.837s, partial: False.

## Does the cheapest-by-rate hotel ever lose?

Cheapest by rate: Odaiba Harbour Stay (fictional).

- Trip A: 2 days, Sat-Sun: best by true cost at 1,000 JPY/h = Odaiba Harbour Stay (fictional); rate winner differs: False; cheapest hotel wins at 4 of the grid points; flips: [('hotel_harbour_odaiba', 'hotel_lantern_asakusa', 1535.1)]; approximate: False.
- Trip B: 3 days, Wed-Fri: best by true cost at 1,000 JPY/h = Odaiba Harbour Stay (fictional); rate winner differs: False; cheapest hotel wins at 4 of the grid points; flips: [('hotel_harbour_odaiba', 'hotel_lantern_asakusa', 1610.0)]; approximate: True.
- Trip C: 4 days, Thu-Sun: best by true cost at 1,000 JPY/h = Odaiba Harbour Stay (fictional); rate winner differs: False; cheapest hotel wins at 6 of the grid points; flips: [('hotel_harbour_odaiba', 'hotel_lantern_asakusa', 1912.5), ('hotel_lantern_asakusa', 'hotel_harbour_odaiba', 2136.4)]; approximate: True.
