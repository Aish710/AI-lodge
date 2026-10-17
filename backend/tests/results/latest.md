# Latest test results

Generated 2026-10-17 13:57:53 UTC by pytest (auto-written by tests/conftest.py).
Run type: partial backend run.
Git revision: 6128e7473201d0e58d2d04fa1b5202e617cf0476 + uncommitted changes.
Pytest args: tests/test_llm_endpoint.py -q
Collected: 22; deselected: 0; executed rows: 22.
Passed: 22, failed: 0, skipped: 0, total: 22.
Partial-run reason: pytest path/test selection was used.

| Time | Result | Test |
|---|---|---|
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_unset_means_the_sdk_default_exactly_as_before` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_base_url_reaches_the_sdk_constructor` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_trailing_v1_and_slash_are_stripped_with_a_warning_that_names_only_the_host` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_anything_but_plain_https_is_refused_and_the_llm_stays_off[http://relay.example.com]` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_anything_but_plain_https_is_refused_and_the_llm_stays_off[ftp://relay.example.com]` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_anything_but_plain_https_is_refused_and_the_llm_stays_off[relay.example.com]` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_anything_but_plain_https_is_refused_and_the_llm_stays_off[https://user:pw@relay.example.com]` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_anything_but_plain_https_is_refused_and_the_llm_stays_off[https://relay.example.com/?k=1]` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_anything_but_plain_https_is_refused_and_the_llm_stays_off[https://]` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_health_shows_the_host_only_and_never_the_key_or_the_path` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_health_in_sample_mode_has_no_endpoint_fields_and_a_refused_url_means_sample_mode` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_the_key_and_url_never_appear_in_repr_or_startup_logs` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_a_rejected_key_message_names_the_host_and_never_the_key` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_a_bad_model_message_mentions_the_gateway_root_domain_hint` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_report_stamp_says_relay_only_when_a_base_url_is_set` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_the_live_gate_refuses_an_unsafe_base_url_before_anything_runs` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_a_provider_error_keeps_status_type_and_a_short_message_for_the_live_scripts_only` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_haiku_gets_no_effort_parameter_by_default_so_the_gateway_call_succeeds` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_other_models_keep_the_default_low_effort_exactly_as_before` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_an_explicit_llm_effort_is_respected_for_models_that_accept_it_and_empty_means_none` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_haiku_ignores_an_explicit_llm_effort_with_a_warning_because_it_always_rejects_it` |
| 2026-10-17 13:57:53 UTC | PASS | `tests/test_llm_endpoint.py::test_health_shows_the_model_name_only_when_the_ai_is_on` |
