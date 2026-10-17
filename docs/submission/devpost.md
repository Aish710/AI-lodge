Choose a hotel based on the trip it makes possible, then build a feasible itinerary around it.

# Fitinerary

## Inspiration

A hotel that looks cheap per night can cost more once you count the travel time and fares it adds to every day, yet most trip planners treat the hotel and the itinerary as two separate decisions. I wanted one tool that chooses them together and shows its working. [PLACEHOLDER: one personal sentence on what made you care about this]

## What it does

Fitinerary plans a short city trip for Tokyo, Singapore, Seoul or Kuala Lumpur (one city per trip). You describe the trip in words or fill a form, press one button, and it compares three hotels by true cost (room, admissions, estimated transport and the value of your travel time), plans the days around the best one, and runs an independent validator over the result. You can ask for changes in words, get a short explanation, and open a "What the AI did" drawer under every AI result. **All data is sample data**: the hotels are made up, travel times are estimates, prices are not live, and no record is human-verified.

## How I built it

The planning is not done by the language model. An OR-Tools CP-SAT optimiser (fixed seed) decides the hotel, the sights and the order; a separately written validator re-checks every rule on the finished plan. The AI works only at the edges and only when you click: it reads your words into an editable form, proposes plan changes that you must apply yourself, and words an explanation of numbers the code already computed. Code decides what reaches the screen: it resolves names, checks the destination city, converts currencies, checks every number and name in an explanation against the computed facts, and falls back to a template. With no AI key the whole app still works. The frontend is Vue 3 with a plain in-memory store (nothing is stored in the browser); the backend is FastAPI with strict Pydantic models. A Proof page is generated from repository files.

## AI safety and responsible design

- The model has no tools and cannot set a safety flag; removing a must-visit needs your confirmation dialog. User text is data inside one delimited block, and the system prompt is a fixed constant.
- A leak guard removes any model text that quotes the system prompt or holds a key, an email address or a phone number. Place descriptions are never sent to the model.
- Per-call caps, a daily circuit breaker, rate limits, and a solver slot that frees when a client disconnects.
- **Red team.** 60 attacks in English, Korean, Chinese and Malay across 10 categories were run through the real pipeline for every city against two simulated models, one gullible and one harmless (840 runs). The simulated red team found three problems before the fixes (model notes quoting the prompt, 228 runs affected; an explanation quoting the prompt, 4 runs; explanations claiming accessibility, safety, weather and similar, 48 runs); all are fixed and the final result was affected in 0 runs. This is a test of the code around the model, not of a real model. Against a real model (27 attacks) the raw reply tried to comply in 3 and the final result was affected in 2: a currency attack left a yen-scale default value of time in the form. I fixed it, reproduced it with a mock first, and re-ran the same 27 attacks: the raw reply again tried to comply in 3 and the final result was affected in 0 of 27. Two runs on one model is indicative, not a guarantee.
- A request the AI cannot honestly serve is refused rather than guessed: another city offers a switch, a vague place name becomes a choose-one question, an ambiguous currency symbol is always confirmed.
- Privacy: nothing is stored. If the AI is on, your cleaned request text and the computed facts pass through the third-party gateway `api.apiyi.com` to the model provider.

## Results (with N and caveats)

- **No language model involved (seeded synthetic trips, sample data):** 15 of 15 named scenarios pass; across 15 comparable trips of 60 the optimised routes used a mean of 14.1% less travel time than an input-order baseline; the validator passed 53 of 53 plans; the lowest-rate hotel was not the best by true cost in 4 of 52 trips at the default value of time and in 10 of 52 at 2,000 yen an hour. The hotels and rates are fictional and were tuned for the demo; this is not a claim about real hotel markets.
- **Live AI (one model, `claude-haiku-4-5-20251001`, through a third-party gateway):** a 20-check smoke test passed 20 of 20 in the latest run (earlier runs failed 4, 2 and 1 checks while problems were found and fixed, so it was tuned on these checks); a gold set of 48 hand-written prompts, 12 per city, scored 48 of 48 exact on the first run and again on two later runs. Treat these as optimistic: the prompts were written by me, the pipeline had been tuned on similar checks, and many fields are decided by code. Not measured: a second model, unseen requests, any user study.
**User test (informal, small N):** Not run yet.

**Human red team (informal, small N):** Not run yet.

- Tests: 859 backend, 295 Vitest and 55 Playwright tests pass. Lighthouse (mobile, local): performance 93 on the Plan page and 86 on the Proof page, accessibility 100 and best practices 100 on both.
- Not run: a user test (the kit is in the repository, with no results), a second model, and any unseen-request test. [PLACEHOLDER: replace the user-test line if you run the user test]

## Challenges

Running the AI for real found problems no mock had: the model rejected a parameter the app always sent (HTTP 400), it filed vague place words such as "the museum" under interests so the wish was silently dropped, and one explanation was rejected because the model wrote "2 hours 38 minutes" for "158 min (2:38)". Each was reproduced with a mock test before it was fixed, and the run history is on the Proof page. The live red team then found a real bug of mine (a wrong default in a non-yen city). Making the evidence honest was its own challenge: stale "not run" claims kept surviving next to results, so I wrote a script that compares every claim with the generated files.

## What I learned

[PLACEHOLDER: your personal takeaways]

## What's next

Cited explanations (each sentence tied to its supporting facts), an AI on/off comparison view, a user test with the kit already in the repository, human verification of the data sheets, and a second model for the live checks.

## Built with

Python, FastAPI, Pydantic, OR-Tools CP-SAT, Vue 3, Vite, Bootstrap, Leaflet and OpenStreetMap, Vitest, Playwright, Lighthouse, Render and Netlify, a Claude model through a third-party gateway.

## Links

- Live app: [PLACEHOLDER: deployed frontend URL]
- Backend: [PLACEHOLDER: deployed backend URL]
- Demo video: [PLACEHOLDER: video link]
- Code: https://github.com/Aish710/AI-lodge
