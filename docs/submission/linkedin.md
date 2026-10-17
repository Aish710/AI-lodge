Choose a hotel based on the trip it makes possible, then build a feasible itinerary around it.

I built Fitinerary for a hackathon: a multi-city trip planner (Tokyo, Singapore, Seoul, Kuala Lumpur) where an OR-Tools optimiser plans the trip, an independent validator checks it, and an AI only reads your words and explains numbers that code already computed. [PLACEHOLDER: demo video or screenshot link]

**1. What I built.** A planner that picks the hotel and the itinerary together and shows its working. Every record is sample data with made-up hotels, and I say so on every page.

**2. What the AI does and does not do.** It never picks the schedule, prices or hours. It reads a request into an editable form, proposes changes you must apply, and words an explanation. Code checks every number and name in that explanation and falls back to a template.

**3. The challenge.** Running it against a real model found three things no mock had: a parameter the model rejected (HTTP 400), vague place words filed under the wrong field so the wish was silently dropped, and a faithful rewording ("2 hours 38 minutes" for "158 min (2:38)") that my own checker rejected. A 20-check smoke test went from stopping at the first call, to 16, 18, 19, 19, then 20 of 20 twice. I reproduced each failure with a mock before fixing it. That test was tuned on those checks, so I show the run history rather than only the last score. A live red team (27 attacks) then found a real bug of mine: a currency trick left a yen-scale default in a non-yen city. After the fix the same 27 attacks affected 0 of 27 final results (2 of 27 before), on one model, two runs.

**4. What I measured and what I did not.** Tests: 642 backend, 261 unit, 55 end-to-end. A simulated red team (48 attacks in English, Korean, Chinese and Malay, 744 runs, simulated models only) found and fixed two leaks. A gold set of 48 hand-written prompts scored 48 of 48 on one model through a third-party gateway, which I call optimistic because I wrote the prompts and tuned the pipeline on similar checks. I have not run a user study, a second model or any unseen-request test.

**5. What I would do next.** Cited explanations, an AI on/off comparison, and a real user test with the kit already in the repo.

[PLACEHOLDER: proudest moment]
Candidates: (a) the day the live runs found three bugs the mocks never would; (b) deleting my own stale "not run" claims with a script instead of by hand; (c) the red team finding a bug in my own code.

[PLACEHOLDER: personal takeaways]
Candidates: (a) a mock proves your code, only a live run tests your assumptions; (b) a high score on tuned checks is a smoke test, not a result; (c) refusing honestly beats guessing, in the product and in the write-up.

Code: https://github.com/Aish710/AI-lodge · Live: [PLACEHOLDER: live app URL]

#AI #LLM #ResponsibleAI #Optimization
