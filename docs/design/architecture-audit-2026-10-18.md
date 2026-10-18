# Architecture audit and implementation design (Phase 0)

Written 2026-10-18 from the code in this repository, before any new feature code. Where something was not inspected it is marked "not inspected".

## 1. What already exists (reuse, do not rebuild)

| Capability in the brief | What the code already has | Where |
|---|---|---|
| One planning engine | CP-SAT `solve(prefs, hotel_id, ds)` with a fixed seed; `compare_hotels` solves per candidate hotel; `replan` re-solves with locks | `optimiser/solver.py`, `hotel_compare.py`, `replan.py` |
| Independent validation | A validator that shares no code with the optimiser; `rebuild_client_schedule` rebuilds and validates an UNTRUSTED client schedule | `validator/checks.py`, `feasibility_report.py` |
| Conflict detection, stage A | `_precheck` returns named conflicts from data alone: `unknown_attraction`, `must_and_skip`, `locked_and_skip`, `lock_outside_trip`, `locked_not_possible`, `locked_no_travel_time`, `does_not_fit_day`, `daily_travel_limit`, `unknown_hours_not_allowed`, `closed_all_days`, `no_open_slot`, `pace_cap`, `not_enough_time`, `budget_too_low`, `locked_overlap` | `solver.py::_precheck` |
| Conflict diagnosis, stage B (single relaxation, solver-verified) | `_alternatives` solves relaxed problems and keeps only feasible ones: `add_day`, `relax_budget`, `allow_unknown_hours`, `extend_day`, `demote_must_visit`. Bounded by a time budget. | `solver.py::_alternatives` |
| Honest fallback | `no_feasible_schedule` (each requirement possible, not together) and `solver_timeout` ("not a proof of infeasibility") | `solver.py` |
| Conflict UI | `ConflictPanel.vue` + `rules.js::conflictActions`: each alternative with a mappable patch becomes an Apply button; others are plain text | frontend |
| Replan operations | `lock`, `move`, `unlock`, `remove`, `change_budget`, `switch_hotel`; must-visit removal needs the confirmation dialog; diff + previous plan | `replan.py`, `/replan` |
| AI proposals | `/parse-replan` returns `ProposedOperations` with `executed: false`; queue, confirm, then `/replan` | `llm/parse_replan.py`, `ProposedOperations.vue`, `PendingChanges.vue` |
| Baselines | input-order `baseline()` (accepts an `order`), nearest-neighbour, three hotel baselines | `optimiser/baseline.py`, `baselines.py` |
| Trade-offs | value-of-time presets, Explorer (real `/compare-hotels` reruns), 8-state in-memory history, `keepHotel` | `TradeoffExplorer.vue`, `lib/tradeoff.js`, `store.js` |
| User limits | `max_activities_per_day`, `max_daily_travel_minutes`, enforced + validated | Phase 2 of the earlier pass |
| AI safety | strict schemas, grounding, leak guard, claims guard, AI switch, rate tiers, solver slot | `app/llm/*`, hardening middleware |

## 2. Missing capabilities (gap list)

1. **Conflict resolver gaps.** Relaxations exist only for five levers. Missing: raise `max_activities_per_day` / `max_daily_travel_minutes`, change pace, unlock one lock, switch hotel, and **two-change combinations** (stage C). No ranking beyond list order. No "verified by independent validator" flag on a repair. No explicit statement when only a combination works.
2. **Manual itinerary.** No endpoint evaluates a user-ordered plan. `baseline(order=...)` exists but assigns days greedily and ignores locks; there is no day-assignment input, no same-attraction vs full-plan comparison, no UI.
3. **Fair itinerary baseline.** Existing baselines only enter the travel comparison when both arms scheduled exactly the same sights (Tokyo 15 of 60 against input order; Seoul 1 of 20). They are not scored with the optimiser's generalised cost, and a baseline that breaks a must-visit is counted as "placed".
4. **Profiles.** Nothing beyond three value-of-time buttons. No provenance (stated / inferred / profile / default).
5. **Alternatives.** The Explorer shows three hotel rules, not itinerary alternatives and no dominance filtering.
6. **What-if.** Reruns exist but each overwrites the current plan on Adopt; there is no non-destructive preview panel.
7. **Collaboration.** None. The service is stateless: no database, no sessions, no authentication, no stored trips.
8. **Scenario identity.** No input fingerprint, no dataset version, no plan id. `planKey` is a client JSON string.

## 3. Shared domain model (smallest change that supports the above)

- **`plan_fingerprint(prefs, hotel_id, dataset_fingerprint, solver_version)`**: a stable sha256 over the canonical JSON of the inputs. Dataset fingerprint = sha256 of the city's JSON files, computed once at load. Returned (additively) by `/optimise`, `/compare-hotels` and `/replan`. Used to refuse comparing results made from different inputs. Backward compatible: new optional response fields only.
- **Preference provenance** is a frontend + parse-response concept: each form field gets `source` in {stated, inferred, profile, default}. The backend does not need it to solve; it must only never receive an inferred value as a hard constraint without a confirmation step (already true for `/parse`: it returns a draft).
- **Scenario** = `{id, parent_id, prefs, hotel_id, fingerprint, result, kind: current|preview|saved|historical}` held in the store. The current `store.history` entry is extended with `kind`, `fingerprint` and `parent`. No browser storage.
- No new solver, validator or cost model. Every new feature builds a `Preferences` object and calls the existing endpoints.

## 4. Planned API changes (all additive)

| Endpoint | Change |
|---|---|
| `POST /optimise`, `/replan`, `/compare-hotels` | add `fingerprint` and `dataset_version` to the response |
| `POST /evaluate-itinerary` (new) | body: `{city_id, preferences, hotel_id, days: [[attraction_id,...],...], locked?}`. Rebuilds the user's plan with the same timing rules, runs the independent validator, then solves (A) the same attraction set and (B) the full plan. Returns both plans, the comparison arithmetic and per-field `comparable` flags. Reuses `assemble`, `rebuild_client_schedule`, `solve`. |
| `POST /optimise` infeasible path | `alternatives` gains kinds for the new levers, a `combination` flag, `validator_passed` and a rank; stays within the existing probe time budget |
| `POST /explore` (new, thin) | runs a bounded list of value-of-time and limit variations through `solve` and returns the non-dominated set with the dominance rule stated. Not a complete Pareto frontier and labelled so. |

No new endpoint is needed for profiles or the what-if panel: both build preferences client-side and call existing routes.

## 5. Persistence, security, privacy

- Phases 1 to 7 need **no database** and store nothing server-side. That keeps the existing privacy statement true.
- Collaboration (phase 8) needs server-side persistence, capability tokens, revocation, revision numbers for optimistic concurrency, server-side authorisation and a stored-prompt-injection review. None exist. **Not started; waiting for your approval** (see section 8).
- New AI-facing work (phase 4) changes the LLM code fingerprint, so live reports made before the change are shown as made for an earlier version until they are re-run (paid). Plan: keep AI changes to the end, and re-run once. (Done on 2026-10-18; see `docs/EVALUATION.md`.)

## 6. Dependency order and complexity

| Phase | Depends on | Complexity | Risk |
|---|---|---|---|
| 1 fingerprint + scenario ids | none | low | low (additive) |
| 2 itinerary baseline harness, `/evaluate-itinerary`, compare UI | 1 | high | medium: day assignment and timing rules must match the validator |
| 3 resolver extension | none | medium | low (probe time budget already exists) |
| 6 alternatives + dominance | 1 | medium | low |
| 7 what-if preview panel | 1, store scenarios | medium | medium: stale-result handling |
| 5 profiles | 1 | low-medium | low |
| 4 AI repair | 3, 5 | medium | high for evidence (re-run needed) |
| 8 collaboration | approval | high | high |

## 7. Breaking-change review

- Response additions are optional; no field is renamed or removed.
- The existing tests pin the exact `Preferences` key set when unset limits are used; new request fields are sent only when set.
- `store.history` entry shape grows; the existing history tests read only `id`, `label`, `hotel`, `plan`, `prefs`.
- `docs/baseline-results.*`, `eval-results.*` and live files are historical; new studies write new files.

## 8. Decisions needed before building the large items

1. **Collaboration**: recommended level is read-only share (level 1), which needs a small store (SQLite file), unguessable tokens, expiry and revoke. I will not build it, or any storage, without your explicit approval.
2. **Deployment**: if the host has an ephemeral disk, a SQLite file will not survive redeploys. Not inspected; needs your input.
3. **AI repair (phase 4)**: needs a paid re-run of all live evidence afterwards.

## 9. Honest timing note

The brief describes several weeks of work. The Devpost deadline is today. The order above is chosen so that each finished phase is independently shippable and tested; anything unfinished is reported as not done, never as a mock-up.
