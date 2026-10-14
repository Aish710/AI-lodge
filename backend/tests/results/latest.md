# Latest test results

Generated 2026-10-14 12:03:17 UTC by pytest (auto-written by tests/conftest.py).
Run type: partial backend run.
Git revision: 520262e2a1c43253293c78de200c88c7130435d6 + uncommitted changes.
Pytest args: -q tests/test_hotel_compare.py tests/test_currency_labels.py -p no:cacheprovider
Collected: 41; deselected: 0; executed rows: 41.
Passed: 41, failed: 0, skipped: 0, total: 41.
Partial-run reason: pytest path/test selection was used.

| Time | Result | Test |
|---|---|---|
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_reference_matrix_values_are_what_the_hand_calculation_assumes` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_hand_computed_true_cost_breakdown` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_true_cost_equals_sum_of_displayed_lines` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_solver_objective_matches_true_cost_units` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_solver_objective_matches_true_cost_with_optional_sights[0]` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_solver_objective_matches_true_cost_with_optional_sights[1500]` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_solver_objective_matches_true_cost_with_optional_sights[3000]` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_default_objective_is_unchanged_by_the_spec_parameter` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_nights_default_is_days_minus_one_and_override_works` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_changing_value_of_time_changes_the_ranking` |
| 2026-10-14 12:03:06 UTC | PASS | `tests/test_hotel_compare.py::test_flip_point_matches_the_analytic_value_and_cache_saves_solves` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_sensitivity_refines_where_plans_change_and_is_honest_about_it` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_no_flip_reported_when_one_hotel_dominates` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_sensitivity_grid_costs_match_a_direct_solve` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_s06_hotel_change_recalculates_itinerary` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_hotel_that_breaks_a_must_visit_is_reported_not_dropped` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_all_hotels_infeasible_is_handled` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_unknown_price_stays_out_of_totals_and_is_warned` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_different_nice_to_have_sets_trigger_a_comparability_warning` |
| 2026-10-14 12:03:07 UTC | PASS | `tests/test_hotel_compare.py::test_same_nice_to_have_sets_give_no_comparability_warning` |
| 2026-10-14 12:03:13 UTC | PASS | `tests/test_hotel_compare.py::test_non_optimal_solve_marks_comparison_approximate` |
| 2026-10-14 12:03:13 UTC | PASS | `tests/test_hotel_compare.py::test_optimal_solves_are_labelled_optimal_and_not_approximate` |
| 2026-10-14 12:03:13 UTC | PASS | `tests/test_hotel_compare.py::test_every_comparison_itinerary_passes_the_independent_validator` |
| 2026-10-14 12:03:13 UTC | PASS | `tests/test_hotel_compare.py::test_time_limit_returns_labelled_partial_results_instead_of_hanging` |
| 2026-10-14 12:03:13 UTC | PASS | `tests/test_hotel_compare.py::test_input_validation` |
| 2026-10-14 12:03:13 UTC | PASS | `tests/test_hotel_compare.py::test_api_compare_hotels_works_in_sample_mode` |
| 2026-10-14 12:03:13 UTC | PASS | `tests/test_hotel_compare.py::test_api_returns_clear_json_errors` |
| 2026-10-14 12:03:13 UTC | PASS | `tests/test_currency_labels.py::test_money_helpers_print_the_cities_own_code` |
| 2026-10-14 12:03:14 UTC | PASS | `tests/test_currency_labels.py::test_hotel_comparison_sentences_and_explanation_use_the_cities_currency[kuala_lumpur]` |
| 2026-10-14 12:03:14 UTC | PASS | `tests/test_currency_labels.py::test_hotel_comparison_sentences_and_explanation_use_the_cities_currency[seoul]` |
| 2026-10-14 12:03:15 UTC | PASS | `tests/test_currency_labels.py::test_hotel_comparison_sentences_and_explanation_use_the_cities_currency[singapore]` |
| 2026-10-14 12:03:16 UTC | PASS | `tests/test_currency_labels.py::test_hotel_comparison_sentences_and_explanation_use_the_cities_currency[tokyo]` |
| 2026-10-14 12:03:16 UTC | PASS | `tests/test_currency_labels.py::test_optimise_report_and_conflict_sentences_use_the_cities_currency[kuala_lumpur]` |
| 2026-10-14 12:03:16 UTC | PASS | `tests/test_currency_labels.py::test_optimise_report_and_conflict_sentences_use_the_cities_currency[seoul]` |
| 2026-10-14 12:03:16 UTC | PASS | `tests/test_currency_labels.py::test_optimise_report_and_conflict_sentences_use_the_cities_currency[singapore]` |
| 2026-10-14 12:03:16 UTC | PASS | `tests/test_currency_labels.py::test_optimise_report_and_conflict_sentences_use_the_cities_currency[tokyo]` |
| 2026-10-14 12:03:16 UTC | PASS | `tests/test_currency_labels.py::test_replan_summary_diff_warnings_and_explanation_use_the_cities_currency[kuala_lumpur]` |
| 2026-10-14 12:03:17 UTC | PASS | `tests/test_currency_labels.py::test_replan_summary_diff_warnings_and_explanation_use_the_cities_currency[seoul]` |
| 2026-10-14 12:03:17 UTC | PASS | `tests/test_currency_labels.py::test_replan_summary_diff_warnings_and_explanation_use_the_cities_currency[singapore]` |
| 2026-10-14 12:03:17 UTC | PASS | `tests/test_currency_labels.py::test_replan_summary_diff_warnings_and_explanation_use_the_cities_currency[tokyo]` |
| 2026-10-14 12:03:17 UTC | PASS | `tests/test_currency_labels.py::test_the_api_responses_carry_no_foreign_code_either` |
