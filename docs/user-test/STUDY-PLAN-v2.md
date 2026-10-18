# Usefulness study, version 2: ready to run, NOT CONDUCTED

**Status: not conducted. No participant has taken part. No result, quote or percentage in this repository comes from a real person.** This file, `study-v2-results.csv` (empty template) and `scripts/summarise_study_v2.py` are the kit. If you run it, add rows only from real sessions.

## Design (5 to 8 target travellers, about 30 minutes each)
- **Participants:** budget-conscious travellers or students who plan their own trips. Not teammates, no coaching. Anonymous ids P1 to P8; record no name, email, phone, employer or photo; ask for the consent line in `TEST-CARD.md`.
- **Within-subject comparison of two builder workflows, same planner behind both:**
  - **Classic**: open the app with `?builder=classic` (for example `https://<site>/?builder=classic`): arrow buttons and "Move to" only, no dragging, no live feedback.
  - **New**: the normal app: drag between days, live "your draft works / has a problem" feedback, keyboard moves.
  - **Counterbalance:** odd participants do Classic then New, even participants New then Classic. Use a different city and a different set of must-visits for the two halves (say which in `city_a` / `city_b`) so learning does not carry over; swap which city comes first between pairs.
- **Tasks** (from `TASKS-v2.md`): T1 generate a trip; T2 explain why this hotel; T3 identify which constraints are satisfied; T4 repair an infeasible itinerary; T5 arrange your own itinerary and compare with the optimiser (the two workflows differ here); T6 change a travel style; T7 what-if "2 days only" and go back; T8 name the cheapest and the least-travel alternative; T9 name what is made-up or estimated.
- Read each task aloud; no hints. Stop a task after 5 minutes and record "not completed".

## Measures (per task and workflow)
| Measure | How |
|---|---|
| Task completion | observer: completed unaided yes/no |
| Completion time | observer stopwatch, seconds |
| Errors | observer count of wrong turns or invalid drafts the person had to undo |
| Ease of editing (T5) | participant, 1 to 5 |
| Understanding of costs (T2, T8) | observer scores the answer to "what do you pay in cash, and what is the score?" as right / partly / wrong; spending includes rooms; the score is not money |
| Ability to resolve conflicts (T4) | completed with a valid plan yes/no; used the repair cards, the AI box or neither |
| Decision confidence | participant, 1 to 5, after each workflow |
| Perceived usefulness | participant, 1 to 5, after each workflow; one free-text sentence |
| Trust calibration (T9) | how many of the three limits (fictional hotels, estimated travel, unverified prices) the person names |

## Reporting rules
Report N, counts and medians per workflow, the paired differences, and every participant who struggled, exactly as it happened. At N of 5 to 8 nothing is significant: do not state percentages as findings. Say who the participants were and that the observer was the developer unless it was not.
`python scripts/summarise_study_v2.py` writes `docs/user-test/study-v2-summary.md`; with no rows it says "No results yet (N = 0)".
