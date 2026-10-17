# User test protocol

**Status: not run.** This file is the protocol only. `results.csv` is an empty template. No result in this repository comes from a real participant until you add rows yourself.

It measures three things, informally: **planning time**, **decision confidence**, and **whether the hotel comparison changes the traveller's choice**. It is small-N. Never call a result significant and never quote a percentage saving that a script did not compute.

## Who and how many
- **5 to 10 target travellers**: budget-conscious travellers and students who plan their own trips. Not teammates. Do not coach.
- Anonymous ids **P1 to P10**. Record **no name, email, phone number, employer or photo**. The scripts refuse text that looks like an email or phone number.
- Read `TEST-CARD.md` aloud. It includes the consent line (permission to note answers and to quote them anonymously). Record the answer in `quote_ok`.
- Tell each person: it is the app being tested, not them; they can stop at any time; nothing they type is kept (the app holds it in memory only).

## Setup
- The live site or a local run. Fresh tab, no saved state, screen visible to the observer.
- City: their choice of the four, or the city's example. Record it in `city`.

## Steps
1. **Plan with no help.** The tester plans a trip (their own picks, or the city's example). The observer starts a timer at landing and stops it when the first plan appears: `time_to_first_plan_seconds`. Note hesitations in your own notes; do not coach.
2. **Before the comparison.** When the three hotels are on screen with nightly rates only (before opening the comparison), ask: "Which would you book?" (`hotel_before`) and "How confident are you, 1 to 5?" (`confidence_before`).
3. **After the comparison.** Show the comparison and ask again: final choice (`hotel_after`), confidence 1 to 5 (`confidence_after`), "Did the comparison change your choice?" yes or no (`changed_choice`), and why in a few words (`why_changed`).
   - Read `winner_changed_in_comparison` **from the app**, not from the tester: did the best-value hotel differ from the cheapest-rate hotel for this trip? yes or no.
4. **Without the app.** Ask: "How long would this planning take you without the app, in minutes?" (`self_estimated_manual_minutes`). This is **self-reported**, not measured.
5. **Ratings, 1 to 5** (1 = strongly disagree): `rating_clear` (clear what to do), `rating_trust` (trust in the result), `rating_use` (would use something like this), `rating_ai_helped` (the AI part helped), `rating_ai_findable` (easy to find the AI). Then one free-text question: "What confused you most?" (`confused_most`, verbatim, blank if nothing).

## Recording
```
python scripts/add_user_test_row.py      # prompts for each column; refuses names, emails and phone numbers; never pre-fills
python scripts/summarise_user_test.py    # writes docs/user-test/summary.md
```
The summary reports N, median time to first plan, median confidence before and after, how many of N changed their choice (and separately for trips where the best-value hotel differed from the cheapest-rate hotel and where it did not), the median self-estimated manual minutes next to the median app time (labelled self-reported), median ratings, and quotes only where `quote_ok` is yes. The Proof page "User test" card shows it only when rows exist; otherwise "Not run yet".

## What the results can and cannot show
- 5 to 10 people can reveal confusing steps and rough reactions. They are not a benchmark and prove nothing about travellers in general.
- The time comparison sets a measured time against a self-estimate; it is not a controlled comparison.
- Confidence and "changed my choice" are self-reported by people who knew they were being observed.
- Report people who struggled or did not change their mind exactly as they are.
