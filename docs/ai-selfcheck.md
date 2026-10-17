# AI self-check (live)

Model: `claude-haiku-4-5-20251001`. Endpoint host: `api.apiyi.com`. Served via a third-party relay: the cleaned text and computed facts pass through that gateway to the model provider, so model behaviour and availability are the gateway's as well as the provider's. PROMPT_VERSION: `2`. Date: 2026-10-17 02:34 UTC. Git: `3873fb5 + uncommitted changes`. Checks: N = 20 (5 per city, 4 cities). Model calls used: 17 of a hard cap of 40. Produced by `backend/scripts/ai_selfcheck.py`.

This is a smoke check of the live pipeline, not a benchmark: one run, one prompt per check, a handful of checks per city. A FAIL is reported as it happened; a template fallback on check 5 is safe behaviour but counts as FAIL here because the model's wording was not accepted.

**20 of 20 checks passed.**

| City | parse_typical | wrong_city | ambiguous_name | currency_symbol | explain_real_result | Passed |
|---|---|---|---|---|---|---|
| Tokyo | PASS | PASS | PASS | PASS | PASS | 5/5 |
| Singapore | PASS | PASS | PASS | PASS | PASS | 5/5 |
| Seoul | PASS | PASS | PASS | PASS | PASS | 5/5 |
| Kuala Lumpur | PASS | PASS | PASS | PASS | PASS | 5/5 |

## Reasons

| City | Check | Result | Calls | Reason |
|---|---|---|---|---|
| Tokyo | parse_typical | PASS | 1 | draft built and expected places resolved |
| Tokyo | wrong_city | PASS | 0 | stopped, nothing planned, switch offered to seoul (by the code check: 0 model calls) |
| Tokyo | ambiguous_name | PASS | 1 | flagged as ambiguous, not guessed |
| Tokyo | currency_symbol | PASS | 1 | read as 25,000 JPY |
| Tokyo | explain_real_result | PASS | 1 | model wording passed the grounding check (14 figures/names checked) |
| Singapore | parse_typical | PASS | 1 | draft built and expected places resolved |
| Singapore | wrong_city | PASS | 1 | stopped, nothing planned, city not available |
| Singapore | ambiguous_name | PASS | 1 | flagged as ambiguous, not guessed |
| Singapore | currency_symbol | PASS | 1 | ambiguous symbol sent back for confirmation, no amount guessed |
| Singapore | explain_real_result | PASS | 1 | model wording passed the grounding check (15 figures/names checked) |
| Seoul | parse_typical | PASS | 1 | draft built and expected places resolved |
| Seoul | wrong_city | PASS | 0 | stopped, nothing planned, switch offered to tokyo (by the code check: 0 model calls) |
| Seoul | ambiguous_name | PASS | 1 | flagged as ambiguous, not guessed |
| Seoul | currency_symbol | PASS | 1 | read as 250,000 KRW |
| Seoul | explain_real_result | PASS | 1 | model wording passed the grounding check (16 figures/names checked) |
| Kuala Lumpur | parse_typical | PASS | 1 | draft built and expected places resolved |
| Kuala Lumpur | wrong_city | PASS | 0 | stopped, nothing planned, switch offered to singapore (by the code check: 0 model calls) |
| Kuala Lumpur | ambiguous_name | PASS | 1 | flagged as ambiguous, not guessed |
| Kuala Lumpur | currency_symbol | PASS | 1 | read as 300 MYR |
| Kuala Lumpur | explain_real_result | PASS | 1 | model wording passed the grounding check (12 figures/names checked) |

No prompts, no model replies and no key are stored in this file. All data is sample data.
