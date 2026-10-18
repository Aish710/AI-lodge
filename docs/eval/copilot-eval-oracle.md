# Copilot evaluation: MOCK ORACLE (integration only: intent accuracy is 100% by construction and says nothing about any model)

Generated 2026-10-18 08:51 UTC by `backend/scripts/run_copilot_eval.py`. Prompt version `4`. Cases: `backend/tests/fixtures/copilot_eval_cases.json` (76 cases, 68 need a classifier, 8 are AI-off quick questions), developer-authored, frozen before any model ran on them, **not independent**. Sample data, fictional hotels. 

| Metric | Result |
|---|---|
| Intent accuracy | 68 of 68 (100.0%) |
| Clarification: right answer was CLARIFY and it was chosen | 8 of 8 |
| Clarification: asked when it should have answered (over-clarification) | 0 of 60 |
| Routing (hand-off shown) | 76 of 76 (100.0%) |
| Factual grounding (evidence equals an independent recomputation; no unexplained number) | 76 of 76 (100.0%) |
| AI-off quick questions answered with no model call | 8 of 8 |
| Task success (all of the above, nothing executed) | 76 of 76 (100.0%) |
| Anything executed by a question | 0 |

## By category

| Category | Cases | Intent | Routing | Success |
|---|---|---|---|---|
| ai_off | 8 | 0/0 | 8/8 | 8/8 |
| alternative_comparison | 8 | 8/8 | 8/8 | 8/8 |
| ambiguous_preference | 4 | 4/4 | 4/4 | 4/4 |
| conflicting_preference | 4 | 4/4 | 4/4 | 4/4 |
| cost_explanation | 8 | 8/8 | 8/8 | 8/8 |
| missing_data | 8 | 8/8 | 8/8 | 8/8 |
| multi_constraint | 4 | 4/4 | 4/4 | 4/4 |
| omission | 4 | 4/4 | 4/4 | 4/4 |
| repair_request | 8 | 8/8 | 8/8 | 8/8 |
| simple_question | 8 | 8/8 | 8/8 | 8/8 |
| unsupported | 8 | 8/8 | 8/8 | 8/8 |
| what_if | 4 | 4/4 | 4/4 | 4/4 |

## By city (never pooled in the claims)

| City | Cases | Intent | Success |
|---|---|---|---|
| kuala_lumpur | 19 | 17/17 | 19/19 |
| seoul | 19 | 17/17 | 19/19 |
| singapore | 19 | 17/17 | 19/19 |
| tokyo | 19 | 17/17 | 19/19 |

## Cases that did not succeed (0)

None.

## Limits

- Expectations are the author's judgement; a legitimately ambiguous question may be answered differently by a reasonable classifier.
- Grounding compares evidence with an independent recomputation of spending and travel and with the dataset; constraint findings come from the solver's own checks and are not independently recomputed here.
- Mock and keyword results are not model results. A live run has not been made unless a live file exists.
