# Latest test results

Generated 2026-10-17 14:00:08 UTC by pytest (auto-written by tests/conftest.py).
Run type: partial backend run.
Git revision: 042cabf3275d469f2b7185eb1b2b6cd2c340b994 + uncommitted changes.
Pytest args: tests/test_user_test_summary.py -q
Collected: 18; deselected: 0; executed rows: 18.
Passed: 18, failed: 0, skipped: 0, total: 18.
Partial-run reason: pytest path/test selection was used.

| Time | Result | Test |
|---|---|---|
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_the_shipped_template_has_a_header_and_no_rows_and_no_pre_filled_summary` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_the_columns_are_exactly_the_agreed_ones` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_counts_and_medians_are_computed_exactly` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_quotes_only_where_quote_ok_is_yes` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over0]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over1]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over2]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over3]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over4]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over5]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over6]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over7]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over8]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_invalid_rows_and_personal_data_are_refused[over9]` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_duplicate_ids_and_extra_columns_are_refused` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_main_writes_the_summary_and_reports_errors_with_a_nonzero_exit` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_add_row_appends_one_validated_row_and_refuses_an_email` |
| 2026-10-17 14:00:08 UTC | PASS | `tests/test_user_test_summary.py::test_prompts_cover_every_column_exactly_once` |
