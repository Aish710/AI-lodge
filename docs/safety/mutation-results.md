# Safety mutation testing

Generated 2026-10-18 04:10 UTC by `backend/scripts/run_safety_mutations.py`. Baseline (no mutation): 570 passed, 1 warning in 48.22s.

Each row disables ONE safeguard in a throw-away test process and runs the safety-relevant test files. Nothing in the repository or any configuration is changed, and no weakened safeguard is committed.

| Disabled safeguard | Detected? | Tests that failed (first 4 of N) |
|---|---|---|
| `leak_scrub_off`: model free text that quotes the system prompt or a secret is no longer scrubbed (runner) | YES | 6: test_after_the_fixes_no_simulated_run_changes_the_final_result; test_code_stops_the_requests_it_can_stop_before_any_model_call; test_live_run_writes_a_stamped_report_without_prompts_or_keys; test_model_notes_that_quote_the_prompt_a_key_or_an_email_are_removed_and_the_user_is_told[parse] |
| `leak_check_off`: an explanation that quotes the prompt or a key is no longer rejected (explain) | YES | 5: test_injection_text_inside_a_fact_field_cannot_make_a_sentence_pass_or_leak; test_after_the_fixes_no_simulated_run_changes_the_final_result; test_an_explanation_that_quotes_the_prompt_is_replaced_by_the_template_and_the_check_can_fail; test_live_run_writes_a_stamped_report_without_prompts_or_keys |
| `claims_guard_off`: unsupported-claims word list (access, safety, quiet, ...) no longer rejects explanations | YES | 8: test_a_claim_the_data_cannot_support_is_dropped_even_with_a_valid_citation; test_after_the_fixes_no_simulated_run_changes_the_final_result; test_the_committed_results_file_matches_a_fresh_run; test_an_explanation_with_such_a_claim_is_replaced_by_the_template_and_says_why[Every |
| `grounding_off`: numbers and names in an explanation are no longer checked against the computed facts | YES | 26: test_a_number_that_is_in_the_facts_but_not_in_the_cited_fact_is_dropped; test_a_place_from_another_city_is_dropped; test_a_short_alias_of_another_citys_place_inside_an_allowed_name_is_not_a_second_mention; test_the_right_id_with_a_wrong_number_is_dropped |
| `must_visit_confirmation_off`: removing a must-visit no longer needs the human's confirmation flag (replanner) | YES | 3: test_api_must_visit_removal_needs_explicit_flag_and_server_never_sets_it; test_removing_a_must_visit_without_confirmation_is_rejected; test_a_model_proposed_must_visit_removal_is_only_a_flagged_proposal_and_cannot_be_applied_without_the_humans_flag |
| `untrusted_schedule_trusted`: a client-supplied schedule is used as is instead of being rebuilt and validated | YES | 26: test_a_schedule_from_another_city_is_rejected_and_names_the_city[kuala_lumpur-seoul]; test_a_schedule_from_another_city_is_rejected_and_names_the_city[kuala_lumpur-singapore]; test_a_schedule_from_another_city_is_rejected_and_names_the_city[kuala_lumpur-tokyo]; test_a_schedule_from_another_city_is_rejected_and_names_the_city[seoul-kuala_lumpur] |
| `no_valid_plan_guard_off`: the model may word an explanation of a plan that does not exist (main._explain_args) | YES | 1: test_an_explanation_cannot_change_or_overrule_the_validators_verdict |
| `foreign_city_ids_accepted`: ids from another city are no longer rejected | YES | 48: test_foreign_hotel_is_rejected_on_optimise_and_compare[kuala_lumpur-seoul]; test_foreign_hotel_is_rejected_on_optimise_and_compare[kuala_lumpur-singapore]; test_foreign_hotel_is_rejected_on_optimise_and_compare[kuala_lumpur-tokyo]; test_foreign_hotel_is_rejected_on_optimise_and_compare[seoul-kuala_lumpur] |
| `unknown_hours_assumed_open_by_default`: allow_unknown_hours defaults to True: a place with unknown hours is silently assumed open | YES | 63: test_a_claim_the_data_cannot_support_is_dropped_even_with_a_valid_citation; test_a_number_that_is_in_the_facts_but_not_in_the_cited_fact_is_dropped; test_a_place_from_another_city_is_dropped; test_a_sentence_citing_a_missing_fact_id_is_dropped_and_the_rest_are_kept |
| `conflict_category_wrong`: missing-information conflicts are reported as known-constraint conflicts (UI would say 'impossible') | YES | 2: test_every_hotel_is_blocked_by_the_same_missing_information_and_the_insight_does_not_claim_impossibility; test_strict_mode_blocks_by_missing_information_and_says_so_once |
| `alternatives_validator_gate_rejects_all`: the independent-validator gate on repair suggestions rejects everything (shows suggestions really pass through that gate) | YES | 7: test_a_travel_limit_conflict_offers_to_relax_or_remove_the_limit; test_an_activity_limit_conflict_offers_the_limit_lever_and_each_repair_is_validated; test_repairs_are_complete_validated_and_never_apply_themselves; test_the_api_returns_structured_changes_the_interface_can_apply |

## Limits

- A mutation models one way a control can fail; it is not every way.
- "Detected" means at least one test failed, not that every scenario is covered.
- The tests were written by the developer who also built the safeguards; this is not an independent assessment.
- The validator gate on repair suggestions cannot be removed in a way that changes any output today (the solver's own plans already pass the validator), so that row checks the gate by making it reject everything.
