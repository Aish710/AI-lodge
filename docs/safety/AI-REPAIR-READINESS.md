# AI-assisted repair: contract (IMPLEMENTED 2026-10-18)

Status: implemented as `/parse-repair` and `/apply-repair` (`app/repair.py`, `app/llm/repair.py`) and `/parse-profile` (`app/llm/profile.py`). The contract below is what the code enforces; the tests are `backend/tests/test_ai_repair.py` and `test_safety_invariants_ai.py`. Differences from the first design: ids and flags are never read from the model, and the model's free-text reason is dropped when it mentions money or numbers.

## Allowlisted action schema
Every model-proposed change is one object from a closed set; anything else is rejected before display:

```json
{ "action": "set_max_activities_per_day" | "set_max_daily_travel_minutes" | "set_pace" | "set_day_end" | "set_days" | "set_strict_budget"
           | "allow_unknown_hours" | "switch_hotel" | "demote_must_visit" | "remove_optional_sight",
  "target": "<dataset id or field name, resolved in code>",
  "expected_previous": "<the value the proposal was made against>",
  "proposed": "<new value, range-checked>",
  "requires_user_approval": true }
```

## Rules
1. `requires_user_approval` is set by code, never read from the model. Actions that give something up (`demote_must_visit`, `allow_unknown_hours`, a lock change) are additionally flagged and shown in their own words.
2. **At proposal time**: schema-validate, resolve the target to an existing id, check `expected_previous` equals the current value, range-check `proposed`, and solve + validate the result (the existing resolver already does this for its own repairs).
3. **At application time**: re-check `expected_previous` against the CURRENT plan (a stale proposal is rejected and the user is told what changed), re-solve, re-validate. A proposal whose plan fingerprint no longer matches is never applied.
4. The model supplies only words (which action, which name); numbers, ids, verification and the effect come from code.
5. Every resulting plan is independently validated; `verification` (verified / conditional) is shown with it.
6. Failure of the model leaves the plan in force and the deterministic repair cards available (as today).

Reuse: `solver._alternatives` (verified repairs), `lib/conflicts.js` (cards), `/parse-replan` (queue + confirmation), `fingerprint.py` (staleness).
Cost: adding a repair action to the model schema changes the AI code, so the self-check, gold set and red team must be re-run (paid) before the Proof page reads them as current.
