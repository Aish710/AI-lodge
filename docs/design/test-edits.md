# Existing-test edits (selector, label and navigation edits only)

Rule: every edit to an existing test is listed here with before and after. A behaviour assertion is never changed without asking.

| # | File | Before | After | Why |
|---|---|---|---|---|
| (none) | | | | Stage 1 Tier A and B kept every existing test id, label and text |
| 1 | frontend/tests/unit/proof.test.js line 200 | `header` fixture string = the OLD results.csv columns (`participant_id,date,city,completed_task,...,quote`) | the NEW 18 columns of Addendum A | The test compares the shipped template with this literal; the template header changed by instruction. Data fixture only, no behaviour change |
| 2 | backend/tests/test_user_test_summary.py (whole file) | Tests for the OLD schema: 12 columns, completed_task, q1..q5, a 5-minute task, a single `quote` column | Same kinds of tests for the NEW schema (see Addendum A): template empty, exact columns, medians, quotes only where quote_ok is yes, refusing PII and bad values, duplicate ids, extra columns, `add_user_test_row.py` | **Needs your OK.** Addendum A replaces the columns and the summary contents, so every old assertion about the old schema had to go. No behaviour outside the user-test kit changed. Made in its own commit so it can be reverted |
| 3 | backend/tests/test_scorecard.py `test_unrun_things_are_stated_as_not_run_and_nothing_is_pre_filled` | When no `llm-live-eval.md`: the scorecard must contain "**Not run.** `backend/scripts/run_llm_live_eval.py`" | When no `llm-live-eval.md` AND `ai-selfcheck.md` exists: the scorecard must say a live smoke test is recorded in `docs/ai-selfcheck.md`, tuned on those checks, not a benchmark, and that `llm-live-eval.md` does not exist. With neither file: "No live result file exists" | **Needs your OK.** The old assertion pinned exactly the stale statement Addendum D told me to fix ("live AI not run" while a 20/20 run exists). A mutation check is the doc-consistency test with a stale "not run" |
