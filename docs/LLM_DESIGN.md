# LLM design

## Core principle
**The pipeline must stay safe even if the LLM is fully compromised or wrong.** The LLM can propose; deterministic code validates and decides. The LLM never sets safety flags, never invents ids, numbers, prices, hours or travel times, and never triggers a state change.

## Trust boundaries (text diagram)
```
 user text ──► sanitiser (length cap, strip control/bidi/zero-width, NFKC, neutralise tags)
                  │  wrapped as <user_request> DATA
                  ▼
 fixed prompts (prompts.py, PROMPT_VERSION) ──► LLM (no tools, no web, no streaming, low effort, small max_tokens)
                  │  untrusted JSON / prose
                  ▼
 ┌────────────────────────────── deterministic code (trusted) ──────────────────────────────┐
 │ strict schema (extra=forbid) → name resolution (dataset only) → FX conversion in code →   │
 │ disclosed defaults → Preferences DRAFT / operation PROPOSAL (nothing executed)            │
 └───────────────────────────────────────────────────────────────────────────────────────────┘
                  │ user edits / confirms (only a human can set confirm_remove_must_visit)
                  ▼
 optimiser → independent validator → feasibility report → computed diff / comparison
                  │ facts only (display-ready strings), never descriptions
                  ▼
 LLM explanation ──► grounding check ──► pass: LLM text │ fail/outage: template text
                                           + warnings appended by CODE, verbatim
```
Attraction `description` text is untrusted external text and is never sent to the model.

## What the LLM may do
- Extract preferences from free text (`/parse`) into a strict JSON schema.
- Turn a change request into operation proposals by place NAME and day-part word (`/parse-replan`).
- Describe a computed result using only precomputed facts (`explain=true`).

## What the LLM may not do
- Set `confirm_remove_must_visit`, `allow_unknown_hours`, hotel prices, a nights override, locks by clock time, or any id: these keys do not exist in its output schemas, and every output model is `extra="forbid"` (an unexpected key invalidates the whole reply).
- Choose the schedule, compute any figure, or change any state. `/parse` and `/parse-replan` return proposals; the client must submit them to the optimiser endpoints.
- Use tools, function calling, web access or streaming. The SDK wrapper sends only model, max_tokens, system, messages and `output_config.effort`; SDK auto-retries are disabled (`max_retries=0`) so call caps are exact.

## Validation pipeline
1. Sanitise (`llm/sanitize.py`): reject over-length input (never truncate), strip control, zero-width and bidi characters, NFKC, collapse whitespace, neutralise literal `<user_request>` tags (including fullwidth forms), wrap in data tags. **It does not try to detect injection by keyword**: such filters are brittle and give false confidence. Defence is structural (the principle above).
2. Call (`llm/runner.py`): at most 2 calls (one retry that appends the schema error: field paths and messages only, never the offending values). Explanations: 1 call.
3. Validate with the strict Pydantic model.
4. Resolve names (`llm/names.py`): normalised exact match (case, punctuation, diacritics, leading "the") against names and aliases only. Several candidates containing all the typed words (e.g. "the museum") return an ambiguity with candidates. A single partial match, a near spelling (difflib ratio >= 0.92) or a shared first word is only a "did you mean" suggestion and is **never auto-accepted**. Replanning resolves against the current schedule first, then the dataset, still without guessing.
5. Convert currency in code with the labelled SAMPLE FX rate; the response states the rate and the budget scope (admissions + estimated transport).
6. Apply disclosed defaults for low-stakes fields only (pace, day window, value of time, max walking, no budget). `days` is never defaulted.
7. Build a `Preferences` draft or typed operations; optimiser endpoints re-validate everything.

## Explanations and the grounding checker
`build_facts` precomputes every figure as display-ready text (rounded JPY, signed deltas, minutes and h/m, SGD display, counts, names, solver status, warnings); the model does no arithmetic. `llm/grounding.py` then checks the reply:
- every number, percentage and HH:MM time must occur in the facts (thousands separators, `+/-/−` signs, `¥ JPY S$ SGD`, `1h 32m`, decimals and `k` suffixes are parsed; the comparison is on absolute values);
- percentages must appear as percentages in the facts, so an invented "about 12%" is rejected;
- spelled-out numbers (one to twenty, tens, hundred, thousand, million) followed by a unit or noun (minutes, hours, yen, JPY, SGD, days, nights, activities, stops, sights, ...) must have a value present in the facts;
- any dataset attraction or hotel name (or alias) whose place is not named in the facts is rejected.
Any rejection, empty or overlong output, or outage discards the model text and uses the template. Warnings ("not like-for-like", approximate / solver not OPTIMAL, must-visit removed by user, unknown prices, conflicts) are appended by code, verbatim from the computed result, never left to the model.

### Known gaps of the grounding checker
- A fabricated number that happens to equal some other number in the facts passes (e.g. "2 hotels" when 2 appears elsewhere); the checker verifies presence, not meaning.
- Spelled-out numbers without one of the listed units or nouns, fractions and quantity words ("half", "double", "a couple", "dozens", "twice"), ordinals ("second day") and numbers in non-Latin scripts are not checked.
- Spelled-out percentages are always rejected (safe, but may reject a true statement).
- Qualitative claims (cheaper, better, "worth it") are not verified. The prompt forbids advice, but compliance is not guaranteed; the check only covers numbers and names.
- Names are matched as whole words against dataset names and aliases; a description of a place without naming it is not detected.
- Reordered facts (attributing a real number to the wrong hotel) pass.

## Prompt versioning
Instructions are fixed constants in `llm/prompts.py`, `PROMPT_VERSION = "1"`. Bump it on any text change; `ParseResult` and the live evaluation report it.

## Model parameters (judgement calls)
No temperature or top_p is sent: current Claude models reject sampling parameters. Determinism and safety come from low effort (`LLM_EFFORT`, default `low`), strict schemas and validation. Thinking tokens count toward `max_tokens`, so the caps (2000 extraction, 1200 explanation) leave headroom.

## Sample mode
With no `LLM_API_KEY`/`LLM_MODEL`, or on any API failure (`LLMUnavailable`), `/parse` and `/parse-replan` return `status: "llm_unavailable"` with an instruction to use the form (never a 500), and explanations are the template text. Optimisation, comparison, replanning and validation run unchanged. `GET /health` reports `llm_configured` and `llm_mode`, never the key.

## Privacy and logging
User text and prompts are not stored or logged. Logging is metadata only (operation, call count, latency, token counts, outcome category). The API key is never in messages, logs, responses or `repr()`; SDK exception text is not propagated.

## What the tests prove (and do not)
All 99 Phase 5 tests use a MOCK client and run with the network blocked and no API key. They verify the **pipeline**: schemas, retry and call caps, name resolution, flag rejection, grounding, template fallbacks, key hygiene, absence of descriptions from prompts. They do **not** measure how well the real model behaves. That is what the opt-in `scripts/run_llm_live_eval.py` is for; its figures are indicative (small N), not benchmarks.
