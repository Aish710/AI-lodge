# Worked examples (from real output)

Generated 2026-10-17 20:01 UTC by `scripts/make_worked_example.py` at git `4ce46ae`. Each table is the real `/compare-hotels` answer of the app (sample mode, no language model) for the city's pinned example trip in `frontend/src/lib/examples.json`.

**These example trips were chosen to show the trade-off. They are not representative.** Where the winner changes (Tokyo, Seoul) it is because the example uses a high value of time; where it does not (Singapore, Kuala Lumpur) the arithmetic simply confirms the cheapest rate. The measured frequency under each example is the honest picture, and it differs by city: how often the lowest-rate hotel is not the best is stated under each one. Sample data, made-up hotels, estimated travel times and fares.

## Tokyo

Example trip: 3 days, must-see places: senso ji, meiji jingu, an example value of time of 3,000 JPY an hour (chosen to illustrate the trade-off, not a typical value). All amounts are in JPY; hotels are made up; travel times and fares are estimates.

| Hotel | Rate per night | Rooms | Admissions | Transport (estimated) | Travel time | Value of that time | Missed-sights charge | True cost |
|---|---|---|---|---|---|---|---|---|
| Hotel Kitsune Shinjuku (fictional) | 14,000 JPY | 28,000 JPY | 500 JPY | 1,750 JPY | 2.95 h | 8,850 JPY | 18,000 JPY | 57,100 JPY |
| Asakusa Lantern Inn (fictional) (best by true cost) | 10,500 JPY | 21,000 JPY | 1,500 JPY | 2,490 JPY | 4.22 h | 12,650 JPY | 12,000 JPY | 49,640 JPY |
| Odaiba Harbour Stay (fictional) (cheapest rate) | 8,500 JPY | 17,000 JPY | 500 JPY | 2,660 JPY | 5.0 h | 15,000 JPY | 15,000 JPY | 50,160 JPY |

**The winner changes.** Asakusa Lantern Inn (fictional) is best by true cost, 520 JPY cheaper overall than Odaiba Harbour Stay (fictional), the lowest-rate hotel. It costs more per night; over this trip it needs 0.78 h less travel, 170 JPY less in estimated fares, 1 fewer of the optional sights left out (each missed sight is charged in the true cost).

In the measured evaluation (docs/eval-results.json, 60 seeded synthetic trips), the lowest-rate hotel was not the best by true cost in 4 of 52 trips where all three hotels were feasible, at the default value of time (1,000 JPY an hour).

## Singapore

Example trip: 3 days, must-see places: gardens by the bay, singapore botanic gardens, an example value of time of 54 SGD an hour (chosen to illustrate the trade-off, not a typical value). All amounts are in SGD; hotels are made up; travel times and fares are estimates.

| Hotel | Rate per night | Rooms | Admissions | Transport (estimated) | Travel time | Value of that time | Missed-sights charge | True cost |
|---|---|---|---|---|---|---|---|---|
| Rochor River Hotel (fictional) | 185 SGD | 370 SGD | 89 SGD | 27 SGD | 2.93 h | 158 SGD | 54 SGD | 698 SGD |
| Bay Lantern Stay (fictional) | 260 SGD | 520 SGD | 89 SGD | 24 SGD | 2.77 h | 149 SGD | 54 SGD | 836 SGD |
| East Coast Pier Inn (fictional) (cheapest rate) (best by true cost) | 125 SGD | 250 SGD | 32 SGD | 24 SGD | 3.45 h | 186 SGD | 162 SGD | 654 SGD |

**The winner does not change.** East Coast Pier Inn (fictional) is both the lowest-rate hotel and the best by true cost for this trip, so here the arithmetic confirms the obvious choice.

In the city evaluation (docs/city-eval-results.json, 20 seeded synthetic trips, reported separately and never pooled), the lowest-rate hotel was not the best by true cost in 7 of 18 eligible trips at the middle tested value of time (1000 local units an hour; the same number in every currency, so it is not a like-for-like value of time across cities).

## Seoul

Example trip: 3 days, must-see places: gyeongbokgung, changdeokgung, an example value of time of 45,000 KRW an hour (chosen to illustrate the trade-off, not a typical value). All amounts are in KRW; hotels are made up; travel times and fares are estimates.

| Hotel | Rate per night | Rooms | Admissions | Transport (estimated) | Travel time | Value of that time | Missed-sights charge | True cost |
|---|---|---|---|---|---|---|---|---|
| Jongno Garden Hotel (fictional) (best by true cost) | 135,000 KRW | 270,000 KRW | 27,000 KRW | 17,713 KRW | 3.03 h | 136,500 KRW | 45,000 KRW | 496,213 KRW |
| Myeongdong Sky Stay (fictional) | 165,000 KRW | 330,000 KRW | 27,000 KRW | 17,829 KRW | 3.1 h | 139,500 KRW | 45,000 KRW | 559,329 KRW |
| Guro River Inn (fictional) (cheapest rate) | 85,000 KRW | 170,000 KRW | 6,000 KRW | 17,680 KRW | 4.53 h | 204,000 KRW | 135,000 KRW | 532,680 KRW |

**The winner changes.** Jongno Garden Hotel (fictional) is best by true cost, 36,467 KRW cheaper overall than Guro River Inn (fictional), the lowest-rate hotel. It costs more per night; over this trip it needs 1.50 h less travel, 33 KRW more in estimated fares, 2 fewer of the optional sights left out (each missed sight is charged in the true cost).

In the city evaluation (docs/city-eval-results.json, 20 seeded synthetic trips, reported separately and never pooled), the lowest-rate hotel was not the best by true cost in 0 of 15 eligible trips at the middle tested value of time (1000 local units an hour; the same number in every currency, so it is not a like-for-like value of time across cities).

## Kuala Lumpur

Example trip: 3 days, must-see places: petronas twin towers, batu caves, an example value of time of 135 MYR an hour (chosen to illustrate the trade-off, not a typical value). All amounts are in MYR; hotels are made up; travel times and fares are estimates.

| Hotel | Rate per night | Rooms | Admissions | Transport (estimated) | Travel time | Value of that time | Missed-sights charge | True cost |
|---|---|---|---|---|---|---|---|---|
| KLCC Lantern Hotel (fictional) | 320 MYR | 640 MYR | 172 MYR | 40 MYR | 4.38 h | 592 MYR | 0 MYR | 1,444 MYR |
| Bukit Bintang Lane Stay (fictional) | 220 MYR | 440 MYR | 172 MYR | 41 MYR | 4.25 h | 574 MYR | 0 MYR | 1,227 MYR |
| Bangsar Edge Inn (fictional) (cheapest rate) (best by true cost) | 140 MYR | 280 MYR | 172 MYR | 45 MYR | 4.77 h | 644 MYR | 0 MYR | 1,141 MYR |

**The winner does not change.** Bangsar Edge Inn (fictional) is both the lowest-rate hotel and the best by true cost for this trip, so here the arithmetic confirms the obvious choice.

In the city evaluation (docs/city-eval-results.json, 20 seeded synthetic trips, reported separately and never pooled), the lowest-rate hotel was not the best by true cost in 8 of 15 eligible trips at the middle tested value of time (1000 local units an hour; the same number in every currency, so it is not a like-for-like value of time across cities).
