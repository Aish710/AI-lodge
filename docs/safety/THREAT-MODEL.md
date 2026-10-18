# Threat model and trust boundaries

Written 2026-10-18 from the code. "Enforcement point" is the exact place a safeguard runs; "Test" is what fails if it is removed (see `mutation-results.md` for the ones checked by mutation).

## Trust boundaries (what trusts what)

```
 user text ──▶ [B1 sanitise, delimit, length cap] ──▶ MODEL ──▶ [B2 strict schema, code-side name/currency/destination resolution]
                                                        │                              │
                                                        │                              ▼
                                                        │                  PROPOSAL (executed:false, flagged, never a schedule)
                                                        │                              │ human clicks (queue, confirm dialog)
                                                        ▼                              ▼
 facts (computed by code) ──▶ MODEL (explanation) ──▶ [B3 grounding, citations, leak guard, claims guard, template fallback] ──▶ screen
                                                                                       ▲
 deterministic planner (CP-SAT) ──▶ [B4 independent validator, shares no code] ────────┘  verdicts come ONLY from here
 browser state (in memory) ──▶ [B5 untrusted schedule rebuilt + re-validated, foreign-city ids refused] ──▶ /replan
```

| Boundary | What crosses it | Trusted? |
|---|---|---|
| B1 user text → model | One delimited data block; instructions are a fixed constant; no place descriptions are sent | user text is untrusted |
| B2 model → application | A strict JSON schema with a closed set of fields; names are resolved in code against the dataset | model output is untrusted |
| B3 model → screen | Prose that must cite facts; every number/name checked; leaks and unsupported claims rejected | model prose is untrusted |
| B4 plan → verdict | The independent validator decides feasible/conditional/fail; the model never does | code only |
| B5 browser → server | A schedule the client sends back is rebuilt from scratch and validated | client state is untrusted |
| B6 stored data (future: shared trips) | Not implemented. A future shared plan must store only server-produced data and ids | n/a |

## Threats, enforcement point, test

| Threat | Enforcement point | Test |
|---|---|---|
| Prompt injection in user text | B1 `llm/sanitize.py`, fixed system prompt; B2 schema has no authority fields | `test_llm_input.py`, `test_redteam.py` |
| Model removes a must-visit | B2 no confirm field in `ReplanOut`; `replan._apply` needs the human's flag; the response is `executed:false` | `test_safety_invariants.py` (1) |
| Model overrides a lock | Locks live in `Preferences.locked`; only a typed op the human queues can unlock/move; replans keep locks | `test_safety_invariants.py` (2) |
| Model invents an attraction/hotel | `llm/names.py` resolves to dataset ids; unresolved names become clarifications | `test_safety_invariants.py` (3) |
| Model relaxes a hard constraint | Schemas have no field for it; budget/hotel changes are proposals | `test_safety_invariants.py` (4) |
| Model commits a plan | Proposals carry no schedule; only `/replan` (human) produces one | `test_safety_invariants.py` (5) |
| Model declares an invalid plan valid | Validator verdict is code; `main._explain_args` never asks the model to word a plan that does not exist (found and fixed by this audit, see below) | `test_safety_invariants.py` (6) |
| Invented price / availability | Grounding (numbers, names), citations, claims guard | `test_safety_invariants.py` (7), `test_llm_explain.py` |
| Stale or mismatched state | B5 rebuild + validate; foreign-city ids refused; plan fingerprint changes with any input | `test_safety_invariants.py` (8), `test_fingerprint.py` |
| Leakage through explanations | `llm/leakguard.py` (runner scrub + explain check); key never in responses or logs | `test_safety_invariants.py` (9), `test_redteam.py` |
| Malformed/unexpected output | Strict schemas (`extra="forbid"`), parse failure → clarification, never partial application | `test_safety_invariants.py` (10) |
| Missing data shown as impossibility / provisional shown as verified | `Conflict.category` (server-derived), `verification` in the report, UI wording | `test_conflict_resolver.py`, `unknown-hours.spec.js` |
| Cost runaway / abuse | Rate tiers, call caps, daily breaker, solver slot | `test_hardening.py` |
| Shared-trip threats (future) | Not implemented: see `../design/collaboration-proposal.md` | n/a |

## Finding made by this audit (fixed)
`/optimise?explain=true` on an INFEASIBLE plan let the model's prose through grounding even when it said "this itinerary is completely valid. Every check passed" (the grounding checks numbers and names, not validity claims). Fix, outside the AI package so existing live evidence stays current: `main._explain_args` does not call the model at all when there is no valid plan; the explanation is the code-written template. Pinned by `test_an_explanation_cannot_change_or_overrule_the_validators_verdict`.

## What is NOT claimed
No immunity from prompt injection. The model can still produce misleading prose about a VALID plan inside what grounding and the claims word list can see; the code-computed verdicts, numbers and warnings beside it are the authority. The live red team is small-N, one model, developer-written.
