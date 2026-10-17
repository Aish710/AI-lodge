# UI copy changes (Phase 9c, Part 4)

Generated from the edits actually made (a log kept while changing the screens), plus the rules they follow. Every row is a string that changed in the interface.

## Rules applied

- **Verdict first, details second.** Each step opens with one headline (hotels: "Best value: <hotel>, <amount> cheaper overall" or "The cheapest hotel is also the best for this trip"; itinerary: four tiles and a status chip).
- **One short line of helper text.** Anything longer moved into an (i) hint (keyboard focusable, announced with aria-describedby) or a collapsed "Why?" / "Show N more".
- **Define a term once**, in an (i) hint where it is first needed: true cost, value of an hour, total cost, sights covered, checks, sample data. "Not like-for-like" keeps its explanation next to the figure it qualifies.
- **Warnings: the 3 most important first** (must-visit problems, budget, unknown data), then "Show N more". Nothing is removed from the page, and failed checks are always shown, never collapsed.
- **Status = icon + word + colour**, never colour alone (✓ Feasible, ! Feasible with warnings, ✕ Not possible).
- **How this was made:** a chip row (Planned by the optimiser › Checked by the validator › Explained by AI, number-checked). The AI step appears only when an AI-written explanation is actually on screen; a template summary never shows it.

## Currency style

- **Server-built sentences** put the city's ISO code after the number: `1,500 JPY`, `135,000 KRW`, `120 MYR`, `40 SGD`. They never hardcode a currency (`backend/app/money.py`).
- **Interface amounts** use a symbol only when that symbol is unique among the currencies of ALL supported cities: `₩135,000`, `S$40`, `RM120`, `¥1,500`. If a symbol would be shared (the yen sign is both JPY and CNY), the ISO code is printed instead: `JPY 1,500`, `CNY 1,500`. The supported set is read from the cities the server lists, so adding a CNY city switches Tokyo to `JPY 1,500` automatically (pinned by `frontend/tests/unit/currency-style.test.js`, which registers a temporary CNY test city next to Tokyo and reverts it).
- A currency with no known symbol prints `1,500 XYZ`.
- The city chip always shows the code: `Tokyo · JPY`.

## Every string changed (before → after)

| # | Where | Before | After |
|---|---|---|---|
| 1 | Navigation | Evidence \| About | Proof \| How it works (old /evidence and /about addresses redirect, keeping the #section) |
| 2 | Proof page: heading and states | Evidence / Evidence is not available in this build. | Proof / Proof is not available in this build. |
| 3 | Proof page: new card | (none) | User test: shows 'Not run yet' until results.csv has participant rows; then N and the generated summary |
| 4 | How it works: heading | About Fitinerary | How Fitinerary works |
| 5 | How it works: intro | Fitinerary plans Tokyo trips by choosing the hotel and the itinerary together, then showing its working. | Fitinerary plans a trip to one city at a time (Kuala Lumpur, Seoul, Singapore, Tokyo) by choosing the hotel and the itinerary together, then showing its working. (city list read from the app) |
| 6 | How it works: what it is | ...built on sample data: 12 Tokyo attractions, 3 fictional hotels... | ...built on sample data: 10 to 12 sights and 3 made-up demo hotels per city... |
| 7 | How it works: limitations | 4 items: sample data (12 attractions, 3 fictional hotels...); no bookings/live availability/walking limit; measured results; free host sleeps | 5 items: sample data + no bookings merged into one; measured results; unsupported-city detection depends on the AI (new); AI quality on real requests not measured (new); free host sleeps |
| 8 | City chip | Tokyo · Japan · JPY | Tokyo · JPY (country in the tooltip) |
| 9 | Hotels: names and badges (Checkpoint 1) | Hotel Kitsune Shinjuku (fictional) + a 'sample' badge per hotel | Hotel Kitsune Shinjuku + a 'Demo hotel' tag; one line above the list: Hotels are made-up examples with sample prices. |
| 10 | Banner (every page) | Sample data: Tokyo only, fictional hotels, estimated prices and travel times. Not live quotes. | Sample data · Tokyo · JPY · prices are examples  (+ (i) tooltip with the full sentence) |
| 11 | Footer: privacy line | Privacy: what you type stays in this page's memory. It is sent to the planner's server only to compute results, and the server does not store it. No cookies, no analytics, no third-party scripts. The map loads tiles from OpenStreetMap, which sees your IP address and the map area you view. | Privacy: nothing is stored; no cookies or analytics. Map tiles come from OpenStreetMap. Details (the full text is on How it works) |
| 12 | Footer: sample-data line | All places, prices, hours and travel times are samples or estimates. Hotels are fictional. Details: How it works and privacy · Proof | (removed: now in the banner tooltip) |
| 13 | Footer: links and reset | Fitinerary · Source on GitHub · Reset (clear everything held in this page) | Fitinerary · Proof · Source · Reset (tooltip: Clear everything held in this page) |
| 14 | Trip: intro | Choose the hotel and the itinerary together: a hotel that looks cheap can cost more once travel time and fares are counted. | Pick the hotel and the plan together. (i: A hotel that looks cheap can cost more once travel time and fares are counted.) |
| 15 | Trip: city picker note | All city packs are sample data. Prices, hours, exchange rates and fictional hotel rates must be verified before real travel. | Sample data: verify before real travel. |
| 16 | Trip: example note | About this example: it uses a high value of time (¥3,000 an hour) so that the hotel trade-off is visible. It is not typical: on random trips the cheapest hotel was usually also the best. See the measured result on the Proof page. | About this example: it values an hour at ¥3,000 so the hotel trade-off shows. It is not typical: on random trips the cheapest hotel was usually the best. See the Proof page. |
| 17 | Trip: budget help | Covers admissions and estimated transport only, not rooms or food. | Sights and transport only (no rooms or food). |
| 18 | Trip: strict budget label | Strict budget: never exceed it (otherwise it is a target) | Strict: never exceed it (otherwise a target) |
| 19 | Trip: pace help | A hard cap on sights per day. | (removed: the options already say 'up to 2 sights a day') |
| 20 | Trip: value of time label and help | How much is an hour of your time worth? + 'Used to compare hotels by true cost in JPY.' | Value of an hour of your time (i: Travel time is priced at this rate when hotels are compared by true cost.) |
| 21 | Trip: nights help | Nights used for room cost: 2 (default: days − 1) | Rooms are priced for 2 night(s) (default: days − 1). Now under Advanced. |
| 22 | Trip: unknown-hours help | Off by default: if we do not know when a place is open, we never assume it is. If you turn this on, such stops are scheduled but flagged. | Off: unknown hours are never assumed open. On: such stops are scheduled but flagged. Now under Advanced. |
| 23 | Trip: field layout | One flat grid of 10 controls | Groups When / Money / Style, plus a collapsed Advanced section |
| 24 | Trip: describe-in-words helper | The AI assistant only proposes values for the form below. You review and edit everything. Your text is cleaned before it is sent; place descriptions are never sent. | The AI only proposes values for the form below; you review everything. (i: Your text is cleaned before it is sent. Place descriptions are never sent.) |
| 25 | Sights: intro | Mark must-sees, nice-to-haves and places you do not want. Optional sights may still be left out of the plan if they would cost more than they are worth; you will see which ones and why. | Mark must-sees, nice-to-haves and places you do not want. (i: Optional sights may still be left out ... which ones and why.) |
| 26 | Hotels: heading and intro | Compare hotels by true cost / True cost = rooms + admissions + estimated transport + travel time × the value you put on an hour + a charge for each optional sight left out. | Compare hotels / Ranked by true cost. (i: the full definition) |
| 27 | Hotels: verdict | (none: the result opened with a notice box and a long sentence) | Large headline: 'Best value: <hotel>, <amount> cheaper overall' or 'The cheapest hotel is also the best for this trip', then the how-this-was-made chips |
| 28 | Hotels: callout | The cheapest rate is not the best value for this trip. Hotel A has the lowest nightly rate, but Hotel B has the lowest true cost. | The cheapest rate is not the best value for this trip. (the hotel names moved into the verdict) |
| 29 | Hotels: insight sentence | (always-visible paragraph) | Collapsed under 'Why?' |
| 30 | Hotels: warnings | Warnings from the planner (verbatim): all of them | Warnings from the planner: the 3 most important (must-visit, budget, unknown data) + 'Show N more' |
| 31 | Hotels: sensitivity progress | The comparison above is ready. Now working out how the ranking changes with your value of time. This uses the solver capacity, so choosing a hotel is paused until it finishes or you cancel. This can take up to about 10 seconds or more on a slow server (3 s so far). | Comparison ready. Checking how the ranking changes with your value of time… 3 s (i: ...) |
| 32 | Hotels: sensitivity note | This uses values the server already computed (N solves); moving the slider sends no request. | Uses values already computed (N solves); the slider sends no request. |
| 33 | Itinerary: totals | Sights scheduled / Travel time / Admissions / Transport tiles, then a paragraph: 'Sights + transport: ¥x. Rooms are not included here (2 night(s), default (days - 1)); see the hotel comparison. Solver: OPTIMAL.' | Header band of 4 big tiles (Total cost, Travel time, Sights covered x of y, Checks passed n of n) with a status chip (Feasible / Feasible with warnings / Not possible) and the how-this-was-made chips; one small line for admissions, transport, rooms note and solver status |
| 34 | Feasibility report: warnings | Every data-quality warning listed | The 3 most important (must-visit, budget, unknown data) then 'Show N more' (all still on the page); failed checks are always listed first, never collapsed |
| 35 | Explain: helper | Optional. Each request may use the AI assistant; without it you get a template summary of the same numbers. | Optional. Uses the AI if available; otherwise a template summary. |
| 36 | Explain: footnote | Supporting text only. The numbers in the tables on this page come from the structured result and are the source of truth. | Supporting text only; the tables are the source of truth. |
| 37 | Explain: how was this checked | The AI only receives the computed numbers and names from this result, never place descriptions. Every number, time and name in its text is compared with those computed facts; if anything does not match, its text is discarded and a template summary of the same facts is shown instead. | The AI gets only this result's computed numbers and names, never place descriptions. Every number, time and name in its text is compared with them; on any mismatch its text is discarded and a template summary is shown. |
| 37 | Hotels: 'same winner' notice | For this trip the cheapest hotel is also the best overall. (Guro River Inn) | (removed: the verdict headline says it) |

## Existing test assertions that changed

See the "Part 4: existing assertions that changed" entry in `docs/BUILD_NOTES.md`: two e2e assertions (banner text; "Sights scheduled" to "Sights covered") and the Evidence/About to Proof/How it works renames in tests. No other assertion text changed.


## Phase 9f: two-screen flow (Plan, Your trip)

| # | Where | Before | After |
|---|---|---|---|
| 39 | Navigation | 1 Trip, 2 Sights, 3 Hotels, 4 Itinerary | Plan, Your trip (the old addresses redirect: /wishlist to Plan, /hotels and /itinerary to Your trip) |
| 40 | Sight choice | Nice to have | Include if it fits (tooltip: "Left out if it adds too much travel") |
| 41 | Sight count line | N must visit · N nice to have · N not interested | N must visit · N include if it fits · N not interested |
| 42 | Plan: city | Four large city cards under "Choose a city" | Compact city chips (name and currency); switching still asks first and lists what clears |
| 43 | Plan: demo | "Quick demo:" | "Try an example:" (one per city) and "Try an impossible <city> trip" |
| 44 | Plan: form | When / Money / Style groups plus a collapsed "Advanced" | "Essentials" (days, first day, pace, budget) plus a collapsed "Advanced options" (day start/end, value of an hour, nights, unknown opening hours) |
| 45 | Plan: primary button | "Next: choose sights", then "Next: compare hotels", then "Use this hotel" | One sticky "Plan my trip" ("Plan my trip again" once a plan exists); the plain reason appears beside it when it is disabled |
| 46 | Plan: progress | (none) | "Comparing hotels…" then "Planning your days and checking the plan…" with Cancel |
| 47 | Plan: preview | (none) | "Rough preview: not a plan": counts, known admissions (unknown prices listed, never counted as zero), areas, and "at most N sights fit" |
| 48 | Your trip: hotel | A separate Hotels step with checkboxes and "Use this hotel" | A hotel switch at the top ("Best value" pre-selected); the full table is under "Compare hotels: the full true-cost breakdown" |
| 49 | Your trip: tile | Travel time | Travel time, all days (estimated), with the hint "Time moving between places, not time at sights." (stored values and API fields are unchanged) |
| 50 | Your trip: slow analysis | Started by itself after the comparison | A button: "See how your value of time changes the winner", with elapsed time and Cancel |
| 51 | Busy server | "Solver is busy. No request was started." | "Another plan is still being calculated. Try again in a few seconds." with a countdown and a manual Retry button |
| 52 | Map without tiles | "Access blocked" pictures from the tile server | Pins on a plain background and "Map tiles unavailable. The pins are still in the right places, and the list next to the map has the same information." |
| 53 | Navigation buttons | Back / Change hotel / Next | "Edit trip" (keeps everything), "Start over" (asks first), "Back to my trip" |
| 54 | Prices | "¥0 (≈ S$0.00)" / "unknown" | A zero price shows "Free"; a missing price shows "Price unknown" (and "not in the total" on a trip card); never "RM0 (~$0.00)" |
| 55 | Plan: themes | (none) | Tabs All / Sightseeing / Shopping / Food & drink, each with an icon, a text label and a count; a theme with fewer than 2 sights shows "Limited in the sample data" |
| 56 | Plan: interests | (none) | "Most interested in:" chips; hint "This only highlights. The planner uses your Must / Include / Skip choices."; matching sights get "Matches your interests" |
| 57 | Your trip: getting around | (none) | A "Getting around (estimated)" card: travel time all days, average per day, transport cost, hotel area |
| 58 | Your trip: costs | Admissions + transport paragraph | A cost panel: one row per day, a Rooms row, "Trip total in cash", unknown prices listed, a budget meter, and two separate figures: "Cash cost" (money) and "True cost" ("a comparison figure, not money") |
| 59 | Your trip: days | Day blocks of text lines | Day chips (Day 1 | Day 2 | All days), a day card (stops, time at sights, travel, cash, theme mix, one-line status), event cards with tags (Must visit, Include if it fits, Needs booking, Unknown hours, Locked) and one-line travel connectors ("Travel 18 min · RM3 · estimated"; no transport mode is named because the data has none) |
| 60 | Stop actions | Lock / Move / Remove buttons | A visible Lock button and a "…" menu with Move and "Skip this (remove)" (still queued through the pending-changes tray) |
| 61 | Map | Pins only | Filter chips with icon, text and count (Attractions, Food, Shopping, Hotels, Saved = your Must visit picks, Needs booking); overlapping pins are spread apart; hovering a card highlights its pin and the other way round |
| 62 | Plan: describe card | "Describe your trip in words (optional)" below the example buttons | First card on the page, titled "Ask the AI to set up your trip" with an AI marker and the subtitle "The AI fills the form below. You check everything before anything is planned."; button "Extract" is now "Ask the AI"; "(optional)" removed |
| 63 | Plan: example prompts | (none) | Three fill-only chips per city (a typical request, "Try a wrong-city request", "Try a vague place"). They put text in the box and send nothing |
| 64 | Plan: result | Raw input, extracted JSON, defaults, assumptions | "What the AI understood": your sentence beside one row per field with an "AI read" marker, an "I assumed" list with Change links, choose-one buttons for ambiguous names (optional, never block), "not in this city's data" for unknown places, a "Switch to <city>" button for another city, and "Apply to my trip" (fills the form, never plans). The raw model JSON moved into a closed "What the assistant extracted (before checking)" section |
| 65 | Markers | (none) | "AI" (tooltip: "Interpreted or written by the AI. Checked by code before it was shown.") on AI-influenced elements and "Calculated" on computed ones, with a one-line legend. Text, never colour alone |
| 66 | Header chip | "AI assistant on" (static) | A button opening a popover: "What the AI does here" / "What it never does", "Every AI answer is checked by code before you see it.", and the gateway host from /health. When off: "AI off: the form works the same." |
| 67 | Your trip: replan box | "Ask for a change in words (optional)" at the bottom | "Ask the AI to change your plan" near the top, with example chips built from the current plan ("Move <first stop> to the morning", "Skip <an optional stop>") that fill and send nothing; button "Ask the AI"; "Add to pending changes" is now "Add to my changes" and a line says how many were added, with a Review and apply link |
| 68 | Your trip: explain | "Explain this result" at the bottom | "Explain this plan", a primary button next to the verdict (one AI call per click), badge "AI-written, numbers checked" or "Template summary", warnings from the planner added by code, and the existing two-sentence "How was this checked?" |
| 69 | Plan and How it works | "Choose the hotel and the itinerary together." (not shown on screen) | The pitch line, exactly: "Choose a hotel based on the trip it makes possible, then build a feasible itinerary around it." Under the Plan heading and as the lead of How it works; also the first line under the README title |
| 70 | Plan: Apply line | "Fills the form below with this reading. It never plans anything." | "The form below is already filled in from this reading. Nothing is planned until you click "Plan my trip". Apply again after editing to restore it." |
| 71 | Header popover | gateway host only | adds "Model: <name>" from /health (`llm_model`, model name only) |
| 72 | How it works: limitations | "How well the AI reads real requests has not been measured yet: that evaluation is opt-in and has not been run." | "The live AI evidence is small: a 20-check smoke test on one model, tuned on those checks (see the Proof page for the run history). It is not a benchmark of how well the AI reads real requests." (found by `scripts/check_doc_consistency.py`) |
| 73 | Plan / Your trip | (none) | A closed "What the AI did" drawer under each AI result (parse, change proposal, explanation): AI calls, model and gateway host, raw model output beside what code rejected or changed and why, the parts done by code. Rendered only when opened; never shows the system prompt, place descriptions or a key |
| 74 | Proof page, section 7 | "Live AI evaluation: Not run yet" (an old statement) | "Live AI evidence": framing "Tuned on these checks; small sample; one model, through a third-party gateway"; the 20-check smoke test with its full run history (every run, root cause, fix); the gold set as First run and After fixes side by side ("Not run yet" or "Not run on this version" when missing or made with another prompt version); the rule-based baseline labelled "not a model" and "not AI accuracy" |
