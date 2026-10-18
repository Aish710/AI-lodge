# User-journey audit (2026-10-18)

Method: I ran the real built app against the real backend (Playwright, Chromium, Kuala Lumpur and Tokyo samples, desktop and 375 px) and walked the journey in the brief. The observer was the developer, not a target traveller; nothing here is user-study evidence.

## Findings and what was done

| # | Problem found | Fix | Status |
|---|---|---|---|
| 1 | No one-click way in. A first-time visitor met a long form; the only shortcut was labelled "Load a Kuala Lumpur example (high value of time, RM…/h)". | "New here?" card with **Try a sample trip**: loads the city's tested example sights at a balanced value of time and plans it (same code path as "Plan my trip"). The technical examples stay, relabelled "Or load a worked example". | Done |
| 2 | The day-by-day itinerary was below the assistant, the totals, What-if, Compare, Explorer and the cost panel. | Itinerary (day chips, map, timeline) now follows the plan summary and totals directly. | Done |
| 3 | Three separate AI text boxes on one page (the question box, the repair assistant, the "describe a change" box). | One front door ("Understand your trip") stays open. The other two sit in one closed disclosure, "More ways to ask for a change". Hand-offs open it. | Done |
| 4 | The copilot could explain but not edit: "Make Day 2 less crowded", "Move X to Day 4", "Can I finish earlier?" fell to UNSUPPORTED/CLARIFY. | Three new bounded intents. The model chooses the operation and copies a day number/name that must appear in the text. Code builds the proposal from the validated schedule. It is a **preview request**: What-if (re-solved, independently validated) or a queued replan move (needs the existing confirm step). A proposal is itself checked by `verify_evidence`. | Done |
| 5 | "Why wasn't X included?" gave a text answer only. | Same answer, plus a **Preview X as a must-visit** button. No cause is claimed. | Done |
| 6 | Empty days were silent. | Panel with plan-derived evidence (active days of N; how many dataset sights are unscheduled) and three choices: keep, preview spreading, preview adding a named dataset sight. No promise of feasibility; previews can report "nothing fits". | Done |
| 7 | Undo existed only far down as "Restore previous plan"/history. | Undo bar under the header: "Last change: … Undo (back to …)". A swap of server results already in memory. | Done |
| 8 | Duplicate "restored" confirmation (top bar and lower notice). | Left as is; minor. | Open (minor) |
| 9 | What-if panel did not open when started from elsewhere. | Panel now opens when a draft exists. | Done |
| 10 | "Keep all must-visits but reduce travel" / "Can I reduce travel?" | Already handled by the existing ANALYSE_TRADEOFF path (bounded, validated Explorer alternatives that keep must-visits). Not rebuilt. | Existing |

## Things that already worked and were not touched
Drag between days with live validation, manual vs optimised comparison, the cash-cost tiles, What-if validation and Apply gating, the explanation block.

## Limits
- Drag-and-drop is mouse/pen only; touch uses the arrow buttons.
- Playwright runs without a model, so the AI-selected path (model picks REBALANCE_DAY etc.) is covered by scripted-model API tests, not a live model. Changing `app/llm/copilot.py` changes the LLM code fingerprint: earlier live reports are now shown as "Not run on this version" until a paid re-run, which has **not** been run.
- The "Move" proposal reuses the current start time; if that does not fit the target day, the replan says so rather than moving it.
