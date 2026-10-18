# Usefulness study tasks (version 2): small, informal, not yet run

**Status: not run. No result in this repository comes from a real participant.** These tasks extend `PROTOCOL.md`; record results with the same scripts and never invent a row. Aim for 5 to 8 target travellers, about 25 minutes each, no coaching, anonymous ids.

Measure per task: **completed unaided (yes/no)**, **time**, **errors or wrong turns** (observer notes), then one question. Report people who struggled exactly as they are.

| # | Task (read aloud) | What it measures | Question afterwards |
|---|---|---|---|
| 1 | "Plan a 3-day trip to <city> with these two must-visits." | Time to first plan; decision confidence | "How sure are you this plan works, 1 to 5?" |
| 2 | "Why does the app recommend this hotel?" (no hint) | Decision clarity | "In your own words, what was the reason?" Score against the facts on screen: right / partly / wrong |
| 3 | "Which of these checks does your plan satisfy? Point to one it does not claim." | Understanding of what is validated and what is estimated | Observer notes whether they mention estimated travel or sample data |
| 4 | "Make the plan impossible (more must-visits than fit), then fix it." | Conflict resolver | "Did you understand why it could not work?" and whether they chose a repair |
| 5 | "You already have an order in mind. Compare it with the app's plan." | Compare with my itinerary | "Which plan visits the same sights? What does the app say about travel time?" (checks they notice 'same sights') |
| 6 | "Pick the travel style closest to you, then change one value." | Profiles | "Which value is yours and which is the style's?" |
| 7 | "What if you only had 2 days? Try it, then go back to what you had." | What-if; replanning success | Did the original plan stay intact? completed yes/no |
| 8 | "Which alternative spends least? Which travels least?" | Trade-off comprehension | Whether they separate spending from the score |
| 9 | End: "What here is made-up or estimated?" | Trust calibration | Hotels fictional, travel estimated, prices unverified: how many did they name? |

| 11 | "You have just opened the app. Start the sample trip and tell me what you see and what you can do here." | First-use understanding (one-click sample, itinerary, drag editing, assistant) | Count how many of 3 the person names unprompted: the day-by-day itinerary, moving sights between days, asking the assistant for a change |
| 12 | "Move <named sight> to day 3." Once by dragging or Move, once by asking the assistant ("Move <sight> to Day 3"), order counterbalanced | Editing speed and errors, manual vs AI-assisted | Seconds, errors, whether the person looked at the preview/check before applying; "Which was easier, 1 to 5?" |
| 13 | "Apply a change you do not like, then get back to the plan you had." | Error recovery (Undo, reject, discard preview) | Recovered unaided yes/no; seconds; did they believe the earlier plan was truly restored? |
| 14 | "What is the total cash this plan is modelled to cost including rooms? Which number on screen is a score rather than money?" | Cost comprehension | Right / partly / wrong against the screen; notes whether they mention that unknown admissions are excluded |
| 15 | "This plan has a free day. What would you do about it?" (use a plan with empty days) | Empty-day help | Which option they chose (keep, spread, add); did they expect a preview to always work? |

Do not report percentages as findings at this N; report counts and quotes (with permission).

## Copilot addendum (prepared, not conducted)

No genuine participants were available during this local engineering pass. Do not count developer walkthroughs or automated browser tests as participants.

Add task 10: "Use Understand your trip to explain why the trip is expensive, then choose a way to investigate a cheaper plan without losing your must-visits." Record whether the person identifies the fictional room component, excluded unknown admissions, and the difference between a suggestion, a preview and Apply. Ask for decision clarity, usefulness and trust (each 1–5) and any confusion about estimates.

Add preference task: "Describe a relaxed trip that still sees everything." Observe whether clarification helps them choose a priority, whether explicit limits survive, and whether they can reject suggestions. Compare task completion, time and errors with the preset/manual-controls condition, not number of AI interactions.

Counterbalance order: odd anonymous ids use controls first, even ids use copilot first. Give equivalent scenarios, do not reveal the expected answer, and report learning/order effects. Collect one row per task in a separate task-level file with these fields: anonymous participant id, condition, task, city, completed unaided, seconds, errors, decision clarity, usefulness, trust, estimate confusion, observer notes. Obtain consent before quotes; never record sensitive travel details. Keep existing historical CSV formats intact. Report counts and individual failures at small N; no causal or statistical significance claim.
