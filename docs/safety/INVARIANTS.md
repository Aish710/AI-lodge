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
