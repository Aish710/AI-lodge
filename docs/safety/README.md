# Safety documentation index

| Document | What it is |
|---|---|
| [THREAT-MODEL.md](THREAT-MODEL.md) | Trust boundaries, threats, the exact enforcement point and test for each, one finding from this audit and its fix |
| [INVARIANTS.md](INVARIANTS.md) | Ten statements about the final application state, each pinned by tests with hostile mock-model output |
| [mutation-results.md](mutation-results.md) | Which test notices when one safeguard is disabled (generated; nothing weakened is committed) |
| [HOLDOUT-PROTOCOL.md](HOLDOUT-PROTOCOL.md) | How an independent tester should write and freeze 30 to 50 new attacks. **Not run.** |
| [PROVENANCE-AUDIT.md](PROVENANCE-AUDIT.md) | What is sample, estimated, unknown or verified, and where it is labelled |
| [AI-REPAIR-READINESS.md](AI-REPAIR-READINESS.md) | The allowlisted action contract a future AI repair feature must meet. Nothing enabled. |

## Red-team methodology and results (kept in their own files)
- **Simulated red team** (`../redteam-results.md`): 60 attacks in four languages against scripted stand-in models, 840 runs. The final result was affected in 0 runs after four fixes the red team itself found. This tests the code around a model, not a real model.
- **Live red team** (`../redteam-live.md`, current: prompt version 3, 31 attacks): the raw reply tried to comply in 3, the final result was affected in 0. One model, through a third-party relay, small N, attacks written by the developer.
- **First live run** (`../redteam-live-first-run.md`, historical): 27 attacks; the final result was affected in 2 (a currency attack left a yen-scale default), fixed afterwards.
- **Human red team** and **independent holdout**: kits exist (`../user-test/HUMAN-REDTEAM.md`, `HOLDOUT-PROTOCOL.md`); no results yet.

**Raw versus final** are always reported separately: *raw* is what the model's reply tried to do; *final* is what a user or the plan in force would actually see or suffer after the code ran.

## What changed in this pass, and what it does to the evidence
- Added: `backend/tests/test_safety_invariants.py` (21 tests), `backend/scripts/run_safety_mutations.py` + `tests/safety_mutation_plugin.py`, `backend/scripts/freeze_holdout.py`, and the documents above.
- One production change: `main._explain_args` (outside `backend/app/llm`) stops the model being asked to word an explanation of a plan that does not exist. It does not touch the AI package, its prompts or its contracts, so the LLM code fingerprint and the live evidence on the Proof page stay current.
- Not changed: AI prompts, model-facing schemas, grounding, claims and leak guards.

## Remaining limitations
Tests are written by the developer who built the controls. The live evidence is small-N on one model. The claims guard still relies partly on a word list; the structural protection is that verdicts, numbers and warnings come from code. No independent tester has attacked the system. Provenance is label-based in the UI, not a structured field in every response (see the audit).
