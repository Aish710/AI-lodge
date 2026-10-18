# Copilot evaluation: KEYWORD BASELINE (deterministic rules written by the case author AFTER seeing the cases: optimistic and case-aware, NOT a language model, and not an independent or lower-bound measure)

Generated 2026-10-18 07:37 UTC by `backend/scripts/run_copilot_eval.py`. Prompt version `4`. Cases: `backend/tests/fixtures/copilot_eval_cases.json` (76 cases, 68 need a classifier, 8 are AI-off quick questions), developer-authored, frozen before any model ran on them, **not independent**. Sample data, fictional hotels. 

| Metric | Result |
|---|---|
| Intent accuracy | 64 of 68 (94.1%) |
| Clarification: right answer was CLARIFY and it was chosen | 8 of 8 |
| Clarification: asked when it should have answered (over-clarification) | 0 of 60 |
| Routing (hand-off shown) | 68 of 76 (89.5%) |
| Factual grounding (evidence equals an independent recomputation; no unexplained number) | 76 of 76 (100.0%) |
| AI-off quick questions answered with no model call | 8 of 8 |
| Task success (all of the above, nothing executed) | 68 of 76 (89.5%) |
| Anything executed by a question | 0 |

## By category

| Category | Cases | Intent | Routing | Success |
|---|---|---|---|---|
| ai_off | 8 | 0/0 | 8/8 | 8/8 |
| alternative_comparison | 8 | 8/8 | 8/8 | 8/8 |
| ambiguous_preference | 4 | 4/4 | 4/4 | 4/4 |
| conflicting_preference | 4 | 4/4 | 4/4 | 4/4 |
| cost_explanation | 8 | 8/8 | 8/8 | 8/8 |
| missing_data | 8 | 4/8 | 4/8 | 4/8 |
| multi_constraint | 4 | 4/4 | 4/4 | 4/4 |
| omission | 4 | 4/4 | 0/4 | 0/4 |
| repair_request | 8 | 8/8 | 8/8 | 8/8 |
| simple_question | 8 | 8/8 | 8/8 | 8/8 |
| unsupported | 8 | 8/8 | 8/8 | 8/8 |
| what_if | 4 | 4/4 | 4/4 | 4/4 |

## By city (never pooled in the claims)

| City | Cases | Intent | Success |
|---|---|---|---|
| kuala_lumpur | 19 | 16/17 | 17/19 |
| seoul | 19 | 16/17 | 17/19 |
| singapore | 19 | 16/17 | 17/19 |
| tokyo | 19 | 16/17 | 17/19 |

## Cases that did not succeed (8)

- `kuala_lumpur_omission_1`: expected `EXPLAIN_OMISSION`, got `EXPLAIN_OMISSION`; hand-off expected `scenario`, got `None`
- `kuala_lumpur_missing_data_2`: expected `IDENTIFY_UNCERTAINTY`, got `EXPLAIN_COST_BREAKDOWN`; hand-off expected `None`, got `alternatives`
- `seoul_omission_1`: expected `EXPLAIN_OMISSION`, got `EXPLAIN_OMISSION`; hand-off expected `scenario`, got `None`
- `seoul_missing_data_2`: expected `IDENTIFY_UNCERTAINTY`, got `EXPLAIN_COST_BREAKDOWN`; hand-off expected `None`, got `alternatives`
- `singapore_omission_1`: expected `EXPLAIN_OMISSION`, got `EXPLAIN_OMISSION`; hand-off expected `scenario`, got `None`
- `singapore_missing_data_2`: expected `IDENTIFY_UNCERTAINTY`, got `EXPLAIN_COST_BREAKDOWN`; hand-off expected `None`, got `alternatives`
- `tokyo_omission_1`: expected `EXPLAIN_OMISSION`, got `EXPLAIN_OMISSION`; hand-off expected `scenario`, got `None`
- `tokyo_missing_data_2`: expected `IDENTIFY_UNCERTAINTY`, got `EXPLAIN_COST_BREAKDOWN`; hand-off expected `None`, got `alternatives`

## Limits

- Expectations are the author's judgement; a legitimately ambiguous question may be answered differently by a reasonable classifier.
- Grounding compares evidence with an independent recomputation of spending and travel and with the dataset; constraint findings come from the solver's own checks and are not independently recomputed here.
- Mock and keyword results are not model results. A live run has not been made unless a live file exists.
