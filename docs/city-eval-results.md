# Multi-city evaluation

Generated 2026-10-14 06:58 UTC by `backend/scripts/run_city_evaluation.py`. Code version: 859c357 + uncommitted changes.

Singapore and Seoul use smaller seeded samples than Tokyo. They are reported separately and are not pooled into headline claims.
All city data is sample data; hotels are fictional; travel times, prices and hours must be verified before real use.

## Data integrity

| City | Attractions | Hotels | Matrix | Provenance | Edge cases |
|---|---:|---:|---|---|---|
| Seoul | 10 | 3 | pass | {'attractions': {'sample': 10}, 'hours': {'sample': 10}, 'costs': {'sample': 10}, 'hotels': {'sample': 3}, 'travel_matrix': 'estimated'} | unknown hours 1; unknown price 1; booking 2; closures 3 |
| Singapore | 10 | 3 | pass | {'attractions': {'sample': 10}, 'hours': {'sample': 10}, 'costs': {'sample': 10}, 'hotels': {'sample': 3}, 'travel_matrix': 'estimated'} | unknown hours 1; unknown price 1; booking 2; closures 3 |
| Tokyo | 12 | 3 | pass | {'attractions': {'sample': 12}, 'hours': {'sample': 12}, 'costs': {'sample': 12}, 'hotels': {'sample': 3}, 'travel_matrix': 'estimated'} | unknown hours 1; unknown price 1; booking 2; closures 5 |

## Smaller-sample city results

### Seoul

- Sample size: 20 generated trips (smaller sample, not a headline).
- Solver plans checked independently: 15 of 20 had a plan/check result; 0 failed.
- Like-for-like vs input-order baseline: 1 comparable trips; mean minutes reduction 0.0.
- Like-for-like vs nearest-neighbour baseline: 1 comparable trips; mean minutes reduction 61.0.
- Hotel value at the middle tested value-of-time (1000 local units/hour): cheapest nightly rate was not best in 0 of 15 eligible trips.

### Singapore

- Sample size: 20 generated trips (smaller sample, not a headline).
- Solver plans checked independently: 18 of 20 had a plan/check result; 0 failed.
- Like-for-like vs input-order baseline: 17 comparable trips; mean minutes reduction 14.470588235294118.
- Like-for-like vs nearest-neighbour baseline: 17 comparable trips; mean minutes reduction 4.882352941176471.
- Hotel value at the middle tested value-of-time (1000 local units/hour): cheapest nightly rate was not best in 16 of 18 eligible trips.

## What these numbers do not show

- They do not verify live opening hours, prices, exchange rates or hotel rates.
- They do not measure a live LLM; the LLM remains covered by mocked safety tests unless the opt-in live eval is run.
- They do not prove statistical significance.
- They do not compare cities against each other.
- They do not replace Tokyo's full 60-trip evaluation.
