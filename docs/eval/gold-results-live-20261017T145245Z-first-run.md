# Gold-set field accuracy, per city (LIVE model)

Run label: `first-run`. Model: `claude-haiku-4-5-20251001`. Endpoint host: `api.apiyi.com`. Served via a third-party relay: the cleaned text and computed facts pass through that gateway to the model provider, so model behaviour and availability are the gateway's as well as the provider's. PROMPT_VERSION: `2`. Date: 2026-10-17 14:52 UTC. Git: `ea27ed5 + uncommitted changes`. Calls used: 44 of a hard cap of 100. Produced by `backend/scripts/score_gold.py --live`.

Gold set: `docs/eval/gold-prompts.json`, 12 hand-written prompts per city (2 each of typical, vague, wrong-city, mixed-language, ambiguous, adversarial). Small N: each cell is indicative, and cities are reported separately, never pooled. Field accuracy counts each scored field of each prompt once; a prompt is exact only if all its scored fields are right.

| City | Prompts (N) | Field accuracy | Exact prompts | typical | vague | wrong_city | mixed_language | ambiguous | adversarial |
|---|---|---|---|---|---|---|---|---|---|
| Tokyo | 12 | 37/37 (100%) | 12/12 (100%) | 13/13 (100%) | 2/2 (100%) | 4/4 (100%) | 8/8 (100%) | 8/8 (100%) | 2/2 (100%) |
| Singapore | 12 | 37/37 (100%) | 12/12 (100%) | 13/13 (100%) | 2/2 (100%) | 4/4 (100%) | 8/8 (100%) | 8/8 (100%) | 2/2 (100%) |
| Seoul | 12 | 37/37 (100%) | 12/12 (100%) | 13/13 (100%) | 2/2 (100%) | 4/4 (100%) | 8/8 (100%) | 8/8 (100%) | 2/2 (100%) |
| Kuala Lumpur | 12 | 37/37 (100%) | 12/12 (100%) | 13/13 (100%) | 2/2 (100%) | 4/4 (100%) | 8/8 (100%) | 8/8 (100%) | 2/2 (100%) |

## Prompts with at least one wrong field

| Prompt | Wrong fields |
|---|---|
| none | |

## Failure categories (counts of missed fields, all cities together; small sample, one model)

| Wrong field | Prompts |
|---|---|
| none | 0 |
