# AI repair and travel-style self-check (live)

Model: `claude-haiku-4-5-20251001`. Endpoint host: `api.apiyi.com`. Served via a third-party relay: the cleaned text and computed facts pass through that gateway to the model provider, so model behaviour and availability are the gateway's as well as the provider's. PROMPT_VERSION: `4`. LLM code fingerprint: `565f5dbf0b9b`. Date: 2026-10-18 04:35 UTC. Git: `dfc0c16`. Checks: N = 16 (4 per city, 4 cities). Model calls used: 16 of a hard cap of 40. Produced by `backend/scripts/ai_repair_selfcheck.py`.

A smoke check of the live pipeline, not a benchmark: one run, one prompt per check, developer-written. A FAIL is reported as it happened.

**16 of 16 checks passed.**

| City | repair_fit | repair_keep | style_slow | style_budget | Passed |
|---|---|---|---|---|---|
| Tokyo | PASS | PASS | PASS | PASS | 4/4 |
| Singapore | PASS | PASS | PASS | PASS | 4/4 |
| Seoul | PASS | PASS | PASS | PASS | 4/4 |
| Kuala Lumpur | PASS | PASS | PASS | PASS | 4/4 |

## Reasons

| City | Check | Result | Calls | Reason |
|---|---|---|---|---|
| Tokyo | repair_fit | PASS | 1 | allowlisted proposal, solver-verified, no must-visit given up |
| Tokyo | repair_keep | PASS | 1 | no hotel switch and no must-visit given up |
| Tokyo | style_slow | PASS | 1 | inferred settings only, each needs confirmation |
| Tokyo | style_budget | PASS | 1 | asked for an amount instead of inventing one; the essential place proposed |
| Singapore | repair_fit | PASS | 1 | allowlisted proposal, solver-verified, no must-visit given up |
| Singapore | repair_keep | PASS | 1 | no hotel switch and no must-visit given up |
| Singapore | style_slow | PASS | 1 | inferred settings only, each needs confirmation |
| Singapore | style_budget | PASS | 1 | asked for an amount instead of inventing one; the essential place proposed |
| Seoul | repair_fit | PASS | 1 | allowlisted proposal, solver-verified, no must-visit given up |
| Seoul | repair_keep | PASS | 1 | no hotel switch and no must-visit given up |
| Seoul | style_slow | PASS | 1 | inferred settings only, each needs confirmation |
| Seoul | style_budget | PASS | 1 | asked for an amount instead of inventing one; the essential place proposed |
| Kuala Lumpur | repair_fit | PASS | 1 | allowlisted proposal, solver-verified, no must-visit given up |
| Kuala Lumpur | repair_keep | PASS | 1 | no hotel switch and no must-visit given up |
| Kuala Lumpur | style_slow | PASS | 1 | inferred settings only, each needs confirmation |
| Kuala Lumpur | style_budget | PASS | 1 | asked for an amount instead of inventing one; the essential place proposed |

No prompts, no model replies and no key are stored in this file. All data is sample data.
