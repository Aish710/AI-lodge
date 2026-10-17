# Existing-test edits (selector, label and navigation edits only)

Rule: every edit to an existing test is listed here with before and after. A behaviour assertion is never changed without asking.

| # | File | Before | After | Why |
|---|---|---|---|---|
| (none) | | | | Stage 1 Tier A and B kept every existing test id, label and text |
| 1 | frontend/tests/unit/proof.test.js line 200 | `header` fixture string = the OLD results.csv columns (`participant_id,date,city,completed_task,...,quote`) | the NEW 18 columns of Addendum A | The test compares the shipped template with this literal; the template header changed by instruction. Data fixture only, no behaviour change |
| 2 | backend/tests/test_user_test_summary.py (whole file) | Tests for the OLD schema: 12 columns, completed_task, q1..q5, a 5-minute task, a single `quote` column | Same kinds of tests for the NEW schema (see Addendum A): template empty, exact columns, medians, quotes only where quote_ok is yes, refusing PII and bad values, duplicate ids, extra columns, `add_user_test_row.py` | **Needs your OK.** Addendum A replaces the columns and the summary contents, so every old assertion about the old schema had to go. No behaviour outside the user-test kit changed. Made in its own commit so it can be reverted |
