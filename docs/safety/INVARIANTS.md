# Safety invariants

Each is a statement about the final application state, tested with hostile mock-model output in `backend/tests/test_safety_invariants.py` (and, for the strict-mode data rules, `test_conflict_resolver.py`).

1. A model cannot silently remove a must-visit. A proposed removal is `executed:false`, flagged `requires_confirmation`, and replaying it without the human's flag is refused (422).
2. A model cannot override a lock. Only a typed, human-queued operation changes a lock; a model proposal changes nothing.
3. A model cannot introduce an unknown attraction or hotel. Unknown and cross-city names become clarifications; an id smuggled into the output is rejected.
4. A model cannot relax a hard constraint. The extraction/replan schemas have no such field; a forbidden extra field never reaches a draft; a budget change is only a proposal.
5. A model cannot commit a plan. Proposals carry no schedule and `executed` is always false.
6. A model cannot declare an invalid plan valid. The verdict is the validator's; no model text is used for a plan that does not exist; a tampered client schedule is rejected.
7. A model cannot invent verified prices or availability in what the user sees.
8. A mismatched or stale state is not accepted: other-city schedules are refused, fingerprints change with any input.
9. A model cannot leak the system prompt or a key through an explanation.
10. Malformed or unexpected model output yields no operations and never breaks the plan in force; with the model down, deterministic replanning still works.

Strict-mode data rule: opening hours are never invented. A required sight with unknown hours blocks planning in strict mode (reported as missing information), and a provisional plan needs an explicit opt-in and is labelled conditional.

## AI repair and AI travel style (added with those features; `test_ai_repair.py`, `test_safety_invariants_ai.py`)
11. A repair cannot silently remove a must-visit: giving one up is its own action, flagged, and applied only with that action's individual confirmation; the optional-removal action refuses a must-visit.
12. A kept hotel and locked stops are never changed by a repair; the only way out of a hotel lock is an individually confirmed unlock.
13. The model cannot invent an attraction, a hotel or opening hours: names resolve in code, the schema has no hours/price/time fields, unknown hours stay unknown and flagged.
14. A fabricated saving or number in the model's reason never reaches the user.
15. Hard-constraint changes need approval; confirmation and hard flags are derived from the action in code, so a forged or model-set flag is ignored.
16. A proposal cannot be applied to a different plan, hotel, lock state or after the plan changed (fingerprint and expected-previous-value re-check at apply time).
17. Prompt injection cannot obtain a privileged action: extra fields reject the whole reply, and a requested confirmation is not honoured.
18. An infeasible repair is labelled not verified, cannot be applied from the interface, and if forced the result is an honest failing plan; a provisional repair is conditional, never verified.
19. A failing model, invalid output or leak attempt leaves the plan in force untouched and the deterministic repairs available.
20. A style text cannot invent a number or override a value the user set.

## Contextual copilot (local upgrade, 2026-10-18)

- `/copilot` is read-only, regardless of selected operation. `PROPOSE_REPAIR` and `PREVIEW_SCENARIO` identify existing controls; they grant no authority and execute no change.
- The only accepted model fields are an allowlisted operation and an optional copied attraction name. Extra fields, malformed output and removed sensitive text fail closed. No model prose is displayed.
- Every cost and schedule fact comes from a rebuilt feasible schedule and the independent validator. A client-declared infeasible result is recomputed; client conflict text is discarded.
- Fingerprints bind questions to their supplied current preferences, city and hotel. They are not signatures or server-side session authentication. The UI discards in-flight answers after a plan change.
- Evidence distinguishes dataset facts, calculations, preferences and unknowns. Conditional feasibility is never relabelled verified. A validated sample plan is not proof of real-world availability.
- Omissions carry no unique causal claim without a counterfactual. Comparisons with different coverage carry no like-for-like savings claim.
- Style tensions withhold conflicting inferred fields and ask a targeted question; explicit numeric settings and overrides survive.

Tests: `test_copilot.py`, `test_copilot_redteam.py`, additional `test_ai_repair.py` cases, frontend `copilot.test.js`, desktop/mobile `copilot.spec.js`. These are developer-authored, not independent testing.

Apply-time repair validation is now a rejection gate: even a syntactically valid, current-fingerprint action is refused if re-solving is infeasible or the independent validator fails. `/apply-repair` returns `repair_not_feasible` with no replacement plan; the UI's error path preserves the current plan and preferences. Dedicated backend tests force each failure and a frontend test checks state preservation. The `repair_apply_validation_ignored` mutation disables only this gate.
