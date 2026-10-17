# Latest test results

Generated 2026-10-17 02:34:55 UTC by pytest (auto-written by tests/conftest.py).
Run type: partial backend run.
Git revision: 3873fb5baa3d45bbd3541a73afe1b33b26268ba2 + uncommitted changes.
Pytest args: tests/test_scorecard.py -q
Collected: 4; deselected: 0; executed rows: 4.
Passed: 4, failed: 0, skipped: 0, total: 4.
Partial-run reason: pytest path/test selection was used.

| Time | Result | Test |
|---|---|---|
| 2026-10-17 02:34:55 UTC | PASS | `tests/test_scorecard.py::test_the_three_criteria_are_covered_with_gaps_and_no_self_grading` |
| 2026-10-17 02:34:55 UTC | PASS | `tests/test_scorecard.py::test_facts_in_the_scorecard_match_the_files_they_come_from` |
| 2026-10-17 02:34:55 UTC | PASS | `tests/test_scorecard.py::test_unrun_things_are_stated_as_not_run_and_nothing_is_pre_filled` |
| 2026-10-17 02:34:55 UTC | PASS | `tests/test_scorecard.py::test_every_generated_claim_sentence_is_copied_verbatim` |
