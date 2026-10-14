# User test protocol

**Status: not run.** This file is the protocol only. `results.csv` is an empty template. No result in this repository comes from a real participant until you add rows yourself.

## Who and how many
- **5 participants**, adults who plan their own trips. Not teammates. Do not coach them.
- Anonymous: record **no name, email, phone number, employer or photo**. Use ids `P1` to `P5`. The summary script refuses a quote that looks like an email address or phone number.
- Tell each person: it is the app being tested, not them; they can stop at any time; nothing they type is kept (the app holds it in memory only).

## Setup (the same for everyone)
- The live site (or a local run) in sample mode or AI mode; note which in the `date` row notes if you like, but not in the CSV.
- City: **Tokyo** for all five (so results are comparable). A different city is allowed only if you record it in the `city` column.
- Fresh browser tab, no saved state. Screen visible to the facilitator.

## The task (fixed, 5 minutes maximum)
Read this aloud, then start a timer:

> "Plan a 3-day trip to Tokyo. You want to see at least two places you choose, you have a budget in mind, and you want to pick a hotel. Stop when you have an itinerary you would be happy to follow."

- Stop the timer when the participant says they have an itinerary, or at 5:00.
- `completed_task` = `yes` if they reached an itinerary they accepted within 5 minutes, else `no`.
- `task_seconds` = the facilitator's stopwatch time in whole seconds (leave blank if not completed).
- Do not explain the screens. If they are stuck for more than 60 seconds, note it, give a neutral prompt ("what would you do next?"), and write the stuck point in your own notes (not in the CSV).

## Estimate for the manual way (after the task)
Ask: **"How long would the same task take you without this app, in minutes?"** Write the number in `manual_estimate_minutes`. This is the participant's own estimate, not a measured time. The summary labels it that way.

## Five questions (1 = strongly disagree, 5 = strongly agree)
1. `q1_clear`: "It was clear what to do at each step."
2. `q2_trust`: "I trust the costs shown."
3. `q3_understood`: "I understand why the plan looks the way it does."
4. `q4_useful`: "This would save me effort when planning a trip."
5. `q5_would_use`: "I would use something like this for a real trip."

Then ask one open question: **"What one thing would you change?"** Write a short verbatim quote in `quote` (leave blank if they have none). Quote exactly; do not tidy or choose only flattering ones.

## Recording
Add one row per participant to `docs/user-test/results.csv` (columns are fixed; extra columns are refused so personal data cannot slip in). Then run:

```
python scripts/summarise_user_test.py
```

It writes `docs/user-test/summary.md` (N, medians, and your quotes verbatim). The Proof page shows a "User test" card with these figures only when the CSV has rows; otherwise it says "Not run yet".

## What the results can and cannot show
- N = 5 is a small sample: it can reveal confusing steps and rough reactions. It is not a benchmark and does not prove time savings.
- Time saved compares a measured time with a self-estimate; it is not a controlled comparison.
- Report failures (people who did not complete the task) as they are.
