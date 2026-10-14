# Latest test results

Generated 2026-10-14 13:07:42 UTC by pytest (auto-written by tests/conftest.py).
Run type: partial backend run.
Git revision: 44ca387bb3789e0076c23f66c01fc74c72694b70 + uncommitted changes.
Pytest args: -q tests/test_city_isolation.py -p no:cacheprovider
Collected: 72; deselected: 0; executed rows: 72.
Passed: 72, failed: 0, skipped: 0, total: 72.
Partial-run reason: pytest path/test selection was used.

| Time | Result | Test |
|---|---|---|
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_every_response_echoes_its_city_id[kuala_lumpur]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_every_response_echoes_its_city_id[seoul]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_every_response_echoes_its_city_id[singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_every_response_echoes_its_city_id[tokyo]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[kuala_lumpur-seoul]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[kuala_lumpur-singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[kuala_lumpur-tokyo]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[seoul-kuala_lumpur]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[seoul-singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[seoul-tokyo]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[singapore-kuala_lumpur]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[singapore-seoul]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[singapore-tokyo]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[tokyo-kuala_lumpur]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[tokyo-seoul]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_hotel_is_rejected_on_optimise_and_compare[tokyo-singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[kuala_lumpur-seoul]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[kuala_lumpur-singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[kuala_lumpur-tokyo]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[seoul-kuala_lumpur]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[seoul-singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[seoul-tokyo]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[singapore-kuala_lumpur]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[singapore-seoul]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[singapore-tokyo]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[tokyo-kuala_lumpur]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[tokyo-seoul]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_locked_stop_is_rejected_on_every_solving_route[tokyo-singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[kuala_lumpur-seoul]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[kuala_lumpur-singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[kuala_lumpur-tokyo]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[seoul-kuala_lumpur]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[seoul-singapore]` |
| 2026-10-14 13:07:37 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[seoul-tokyo]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[singapore-kuala_lumpur]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[singapore-seoul]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[singapore-tokyo]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[tokyo-kuala_lumpur]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[tokyo-seoul]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_replan_operation_targets_are_rejected[tokyo-singapore]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[kuala_lumpur-seoul]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[kuala_lumpur-singapore]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[kuala_lumpur-tokyo]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[seoul-kuala_lumpur]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[seoul-singapore]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[seoul-tokyo]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[singapore-kuala_lumpur]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[singapore-seoul]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[singapore-tokyo]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[tokyo-kuala_lumpur]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[tokyo-seoul]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_a_schedule_from_another_city_is_rejected_and_names_the_city[tokyo-singapore]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[kuala_lumpur-seoul]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[kuala_lumpur-singapore]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[kuala_lumpur-tokyo]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[seoul-kuala_lumpur]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[seoul-singapore]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[seoul-tokyo]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[singapore-kuala_lumpur]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[singapore-seoul]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[singapore-tokyo]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[tokyo-kuala_lumpur]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[tokyo-seoul]` |
| 2026-10-14 13:07:38 UTC | PASS | `tests/test_city_isolation.py::test_foreign_must_visit_and_skip_ids_are_rejected_on_every_route_that_takes_preferences[tokyo-singapore]` |
| 2026-10-14 13:07:39 UTC | PASS | `tests/test_city_isolation.py::test_the_default_sensitivity_range_scales_with_the_cities_own_value_of_time[kuala_lumpur]` |
| 2026-10-14 13:07:39 UTC | PASS | `tests/test_city_isolation.py::test_the_default_sensitivity_range_scales_with_the_cities_own_value_of_time[seoul]` |
| 2026-10-14 13:07:40 UTC | PASS | `tests/test_city_isolation.py::test_the_default_sensitivity_range_scales_with_the_cities_own_value_of_time[singapore]` |
| 2026-10-14 13:07:40 UTC | PASS | `tests/test_city_isolation.py::test_the_default_sensitivity_range_scales_with_the_cities_own_value_of_time[tokyo]` |
| 2026-10-14 13:07:41 UTC | PASS | `tests/test_city_isolation.py::test_the_missed_sight_charge_scales_with_the_city_and_a_default_trip_is_not_nearly_empty[kuala_lumpur]` |
| 2026-10-14 13:07:41 UTC | PASS | `tests/test_city_isolation.py::test_the_missed_sight_charge_scales_with_the_city_and_a_default_trip_is_not_nearly_empty[seoul]` |
| 2026-10-14 13:07:42 UTC | PASS | `tests/test_city_isolation.py::test_the_missed_sight_charge_scales_with_the_city_and_a_default_trip_is_not_nearly_empty[singapore]` |
| 2026-10-14 13:07:42 UTC | PASS | `tests/test_city_isolation.py::test_the_missed_sight_charge_scales_with_the_city_and_a_default_trip_is_not_nearly_empty[tokyo]` |
