# Independent holdout: instructions for the person writing the prompts

You are helping to test an AI trip assistant on requests it has never been tuned on. **Please do not look at the app's examples, its Proof page or `docs/eval/gold-prompts.json` first.** The point is that the builder did not write these.

**What to do (about 30 minutes).** Open `docs/eval/holdout-prompts.json`. Delete the two rows marked FORMAT ONLY and write **15 rows** of your own. For each row:

1. **`text`: a request in your own words**, the way you would really type it to a travel assistant. Mix it up: typos, a different language (Korean, Chinese, Malay, anything), a vague place ("the museum", "the tower"), a request about the wrong city, an odd currency ("$", "bucks", "RM"), short and long ones. Cover different cities: `tokyo`, `singapore`, `seoul`, `kuala_lumpur`. Set `city` to the city the app is set to when the request is typed.
2. **`expected`: a simple answer, written BEFORE anything is run.**
   - `days`: how many days you asked for (1 to 7), or `null` if you did not say.
   - `pace`: `relaxed`, `balanced` or `packed` if you said so, otherwise `null`.
   - `budget`: `{"amount": 30000, "currency": "JPY"}` if you named one (the city's own currency, or SGD/USD style display currency), otherwise `null`.
   - `must_visit_names` and `skip_names`: place names **exactly as the app shows them** (the app's Sights list), for places you said you must see or want to skip.
   - `ambiguous`: pieces of your text that are genuinely unclear (like "the museum" in a city with two), where the right answer is to ask, not to guess.
   - `wrong_city`: if your request is really about another city, that city's id; use `unsupported` for a city the app does not have. Otherwise `null`.
3. **`author_role`**: for example `"a friend, not the builder"`. **`written_on`**: today's date, `YYYY-MM-DD`.
4. **`id`**: `h01`, `h02`, and so on.

**Rules.** Do not copy or reword the app's examples or the gold prompts (the script refuses near-copies). Write the expected answer from what **you** meant, not from what you think the app will do. If a row turns out wrong later, do not edit it to make the score look better; tell the builder and mark the row.

**Then.** Commit the file (`git add docs/eval/holdout-prompts.json`). The builder runs `python3 scripts/score_holdout.py` for a no-AI baseline, and later the opt-in live run with a label. The Proof page will show "Independent holdout: N prompts written by <author_role>, small sample" only when a results file exists for the current code version, and "not run" otherwise.

**What this can and cannot show.** 15 prompts from one person is a small sample. It checks that the AI box also handles requests its builder did not write; it is not a benchmark.
