# Gold-set field accuracy, per city (MOCK rule-based baseline: not a model)

Scorer: `rule-based baseline v1`. PROMPT_VERSION: `2`. Date: 2026-10-15 10:24 UTC. Git: `35849ba + uncommitted changes`. Zero model calls. Produced by `backend/scripts/score_gold.py`. This baseline is a deterministic stand-in made of regexes and alias scanning. It shows that the scoring and the validation pipeline work and gives a floor to compare a model against. It is NOT a measurement of any language model.

Gold set: `docs/eval/gold-prompts.json`, 12 hand-written prompts per city (2 each of typical, vague, wrong-city, mixed-language, ambiguous, adversarial). Small N: each cell is indicative, and cities are reported separately, never pooled. Field accuracy counts each scored field of each prompt once; a prompt is exact only if all its scored fields are right.

| City | Prompts (N) | Field accuracy | Exact prompts | typical | vague | wrong_city | mixed_language | ambiguous | adversarial |
|---|---|---|---|---|---|---|---|---|---|
| Tokyo | 12 | 34/37 (92%) | 10/12 (83%) | 13/13 (100%) | 2/2 (100%) | 2/4 (50%) | 8/8 (100%) | 7/8 (88%) | 2/2 (100%) |
| Singapore | 12 | 35/37 (95%) | 10/12 (83%) | 13/13 (100%) | 2/2 (100%) | 3/4 (75%) | 8/8 (100%) | 7/8 (88%) | 2/2 (100%) |
| Seoul | 12 | 33/37 (89%) | 9/12 (75%) | 13/13 (100%) | 2/2 (100%) | 2/4 (50%) | 7/8 (88%) | 7/8 (88%) | 2/2 (100%) |
| Kuala Lumpur | 12 | 34/37 (92%) | 10/12 (83%) | 13/13 (100%) | 2/2 (100%) | 2/4 (50%) | 8/8 (100%) | 7/8 (88%) | 2/2 (100%) |

## Prompts with at least one wrong field

| Prompt | Wrong fields |
|---|---|
| tokyo_wrong_city_2 | draft, destination |
| tokyo_ambiguous_1 | ambiguous |
| singapore_wrong_city_2 | destination |
| singapore_ambiguous_1 | ambiguous |
| seoul_wrong_city_2 | draft, destination |
| seoul_mixed_language_1 | budget |
| seoul_ambiguous_1 | ambiguous |
| kuala_lumpur_wrong_city_2 | draft, destination |
| kuala_lumpur_ambiguous_1 | ambiguous |
