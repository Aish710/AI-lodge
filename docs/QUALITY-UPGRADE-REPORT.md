# Fitinerary local quality upgrade — engineering assessment

Date: 2026-10-18 (Singapore). Implementation: local commits `5d39974` and `11601ef` (apply-time repair gate). No push, deployment or publication. This is a developer self-assessment, not an independent review or judging score.

## What changed in the application

Your Trip now has **Understand your trip**, a bounded contextual copilot. Free text goes through a single strict intent-classification call. Quick questions work without AI. The model cannot supply plan facts, prices, savings, confirmation flags or executable actions. Code rebuilds client schedules, independently validates them, resolves names and writes the answer with typed evidence references. A stale fingerprint is rejected before classification, and the UI discards answers after a trip or preference change.

Cost questions show server-computed spending components, fictional room costs and excluded unknown admissions. Cheaper / less-travel questions reuse the existing Explorer for a bounded search with the current hotel and hard constraints fixed; candidates expose spending, travel, optional coverage, verification status and unknown prices. No global optimum, complete frontier or like-for-like savings is inferred. Scenario and repair questions lead to existing preview/Apply workflows and grant no approval. The repair apply route now rejects infeasible or independently failed re-solves instead of returning a replacement plan. Separate tests force each failure and verify preservation of the current client state.

Style interpretation now asks a targeted question for pace-versus-coverage and spending-versus-convenience tensions. Conflicting inferred settings are withheld; explicit numbers and existing overrides survive. The user can reject suggestions through the existing selection/Cancel controls. This depends on the model emitting the relevant tags; live classification accuracy remains unmeasured on the new version.

The places API exposes existing field verification records, including unknown/unchecked/not-applicable states. Attraction cards show dated source links and scope notes. What-if results state dataset validation versus provisional feasibility and warn about coverage differences. Omission copy no longer claims a unique marginal-cost cause without counterfactual evidence.

## Audit decisions and scope

The [audit and copilot design](COPILOT-UPGRADE.md) records user problems, AI contribution, verification, complexity, performance and risks. Existing manual comparison, what-if, repair confirmation and dynamic profiles were reused. Existing deterministic repair ranking already prioritises bounded, solver-checked changes by change count, must-visit loss, coverage and travel; no global-minimality claim is added. There was no evidence justifying an optimiser or ranking rewrite.

[Singapore source review](data-verification/COPILOT-SOURCE-REVIEW.md) keeps all four city packs explicitly in sample mode. Hotels and rates remain fictional. Travel matrices remain estimates. Singapore's existing source-checked fields now reach the interface; the other cities remain unchecked. Gardens by the Bay has an unresolved scope mismatch between the broad attraction name and Flower Dome hours/admission assumptions, now exposed in its source notes. No real hotel or routing integration is claimed. OneMap is a possible Singapore routing source, but account/token, mode, quota, caching and licensing work remains.

The [prepared usability study](user-test/TASKS-v2.md) adds copilot decision support, preference clarification, task completion, timing, errors, clarity, usefulness, trust and estimate-confusion measures. It counterbalances copilot/control order. **Not conducted: no participants, observations, feedback or user-value effect have been invented.**

## Safety evidence and its limits

The frozen development suite has 16 attack categories across repair, style and copilot. Deterministic tests force malicious out-of-schema model output and include schema-valid protected-action proposals, invented limits/prices/entities, locked hotels, stale/cross-scenario references, confirmation bypass, invalid and provisional plans, AI-off fallback and poisoned descriptions. Existing apply-time tests continue to cover fingerprints, expected previous values, hard changes and independent validation.

The new opt-in runner `backend/scripts/redteam_copilot.py` executes the actual API pipelines and records schema/action/confirmation/validator stages, full API responses, input-plan snapshots and scrubbed model responses. Null stages mean not exercised. Raw compliance remains an explicit semantic-review field; automated indicators alone do not establish compliance rates. Read-only proposal tests cannot establish committed-state apply safety, which is tested separately. Exact labelled user-input echoes are retained for inspection and distinguished from derived claims. Possible prompt/secret-bearing raw replies are inspected in memory and removed from persisted response text.

All safeguard mutations are in isolated test processes. The runner now selects each safeguard's relevant boundary tests, records those files per row, rejects process errors as evidence and returns failure if any mutation survives. [Mutation results](safety/mutation-results.md) are developer-authored evidence; mutation detection does not mean every exploit is covered. The copilot fingerprint mutation also changes valid requests, so its detection must be read with the specific stale-reference assertion, not merely the aggregate failure count.

Historical paid self-check, gold and red-team files retain their original code stamps. The Proof page correctly treats them as stale for the new AI code. No old result is presented as a live result for this copilot. The prior prompt-v4 results are historical: the self-check reports 19 of 20; the final gold file reports 37 of 37 fields in Tokyo, Singapore and Seoul and 35 of 37 in Kuala Lumpur; the old live red team records three raw-compliance indicators and zero final affected results across 31 attacks. Those findings do not extend to the new operations.

Paid execution is pending. The new suite's dry-run estimates 48 cases, at most 80 calls, and a planning envelope of 240,000 input / 160,000 output tokens. Estimated price is `0.24 × input price per million + 0.16 × output price per million`, excluding existing live smoke/gold/parser/explanation reruns and any provider-specific extra charges. No provider billing price or paid approval was assumed. The suite is frozen development material, not an unseen independent holdout; no tuning against an independent holdout occurred.

## Reproducible business-value evidence

The [rerun itinerary study](itinerary-study.md) uses fixed seeds, constraint-aware input-order and nearest-feasible baselines, the same sample data and the independent validator. Infeasible cases, ties, coverage, spending, generalised cost and runtime remain visible. The optimiser code and scenario definitions were not changed to improve these results.

| City | Trips | Input-order feasible | Nearest-feasible baseline | Optimiser feasible | Matched travel vs nearest: better / tied / worse |
|---|---:|---:|---:|---:|---|
| Tokyo | 60 | 42 | 46 | 53 | 31 / 15 / 0 |
| Singapore | 20 | 16 | 17 | 18 | 12 / 5 / 0 |
| Seoul | 20 | 14 | 13 | 15 | 12 / 1 / 0 |
| Kuala Lumpur | 20 | 14 | 14 | 15 | 12 / 2 / 0 |

Feasible means must-visits satisfied and no failed independent check. Each city's denominator is separate. The Tokyo optimiser's median optional coverage is lower than the nearest-feasible baseline (73.2% versus 85.7%); Kuala Lumpur's optimiser median known spending is higher (104 versus 96.5 in sample local-currency units). Comparing unmatched per-arm medians is descriptive, not a paired causal effect. The report also preserves per-trip paired generalised-score ties and matched-routing comparisons. The strongest supported value proposition is **finding feasible schedules under required visits and improving some matched routes on synthetic sample trips**. Reduced human planning effort, better trust and real cash savings remain unproved.

## Proposed scores (subjective, provisional)

| Criterion | Previous | Proposed | Target | Why the target is not claimed |
|---|---:|---:|---:|---|
| AI Integration Effectiveness | 8 | 8.5 | 9 | Questions now connect to checked evidence, bounded solver alternatives and existing workflows. Strict API/UI tests support integration; live intent accuracy and multi-turn task success remain unmeasured. |
| LLM Safety & Responsible AI | 9 | 9.2 | 9.7 | New intent output contains no prose or authority; typed evidence, stale-answer rejection, fail-closed repair application, adversarial mocks and additional mutations strengthen the boundary. No independent holdout, current live assessment or comprehensive semantic claim proof supports a near-perfect score. |
| Usefulness & Business Value | 7.5 | 8.0 | 9 | Contextual costs, alternatives, honest omissions, source notes and clarification improve decision support. Synthetic feasibility/routing evidence exists; genuine participant task completion, real prices/routes and preference-clarification benefit do not. |

These increases assess observable engineering capability and evidence quality, not code volume. No target is automatically awarded. Runtime and UI checks cannot substitute for a participant study or model evaluation.

## Final verification

*Counts refreshed on 2026-10-18 after later fixes; this report's original counts (1,103 / 391 / 70) were superseded by the current suites.*

Final committed-source verification: **1155 backend tests passed** (including both safety-invariant files and loopback disconnect tests), **400 Vitest tests passed**, **88 Playwright tests passed**, and **22 of 22 safeguard mutations detected**. No tests were skipped in the full backend or frontend suites. The backend emitted one existing Starlette/AnyIO deprecation warning. Claim checks: **zero unmatched numbers and zero conflicts**; tracked-import checks and `git diff --check` also passed. Existing publication placeholders remain; this is a local engineering result, not a published submission.

Playwright exercised the new panel at desktop and mobile widths, real API responses, cost evidence, workflow navigation and the existing browser flows. The in-app browser runtime had no available connection, so no manual in-app visual review is claimed. The full itinerary study was rerun after the apply-time fix. The separate [full evaluation](eval/copilot-local/eval-results.md) passed all 15 named scenarios and evaluated 60 generated trips, and the [city evaluation](eval/copilot-local/city-eval-results.md) reran the added cities; those outputs keep their original earlier code stamps because they preceded the isolated apply-route fix, which did not change optimisation. The main legacy evidence index remains explicitly stale where applicable.

The [machine-readable verification snapshot](QUALITY-UPGRADE-VERIFICATION.json) records the production source commit/hash, native suite metadata, command outcomes and artifact hashes. [Frozen mock API evidence](safety/copilot-redteam-mock.json) retains per-case stages and scrubbed scripted responses with explicit coverage limits. The frozen natural-language hotel-lock vector uses an out-of-dataset spelling, so its interpretation alone does not establish a valid-target lock attack; the separate schema-valid mock test uses the actual dataset property and exercises lock rejection.

Legitimate assertion updates are logged in the design audit: removal of unsupported omission causality, freshness derived from code stamps while retaining historical reports, and HTTP rejection with no replacement result for infeasible repair applies. Initial sandbox restrictions and the conflict-panel test-identifier regression were resolved before these final passing runs. No weakened production safeguard was committed, and no paid call, participant result, push, deployment or publication occurred.
