# Devpost Draft: Fitinerary

## Inspiration

Trip planners often optimise attractions after the hotel has already been chosen. Fitinerary started from the opposite question: what if the hotel and itinerary were planned together, with travel time and true cost visible?

## What it does

Fitinerary plans Tokyo sample trips. Users set days, budget, pace, value of time, must-visits, skips, and hotel choices. The app compares fictional hotels by true cost, generates an itinerary, validates the plan, shows an accessible map/list view, and supports disruption-aware replanning.

## How I built it

The backend is FastAPI with Pydantic schemas and OR-Tools CP-SAT optimisation. The frontend is Vue 3 with Vite, Leaflet maps, Vitest, Playwright, and generated evidence pages. Data is sample-labelled and the travel matrix is reproducible from a script.

## AI Integration

The optimiser makes planning decisions. The LLM interprets natural-language trip requests, proposes replanning operations, and writes explanations from computed facts. The app works in sample mode without live AI.

## AI Safety And Responsible Design

Validation checks computed schedules independently. Unknown prices/hours are disclosed. The LLM cannot execute changes on its own or confirm removal of must-visits. Explanations are grounded against server facts, with template fallback. The safety log tracks risks, safeguards, and tests.

## Challenges

- Keeping hotel comparison honest when different hotels can produce different optional sights.
- Preventing partial test runs from looking like full-suite evidence.
- Making generated evidence reproducible without creating circular Git-hash claims.
- Handling solver capacity on small hosting environments.

## Measured Results And Limitations

Use `docs/SUBMISSION-FACTS.md` for the latest verified numbers. Current generated evidence reports 60 seeded synthetic trips on Tokyo sample data, with travel-time comparisons, validator results, hotel-value rates, replanning disruption, hardening results, and Lighthouse scores. These are not claims about real trips, live prices, or real hotel markets.

## What I Learned

Planning products need honesty in the interface, not only in documentation. It is easy to build a demo that looks confident; it is harder and more valuable to show uncertainty, unknowns, and non-comparable results clearly.

## What's Next

- Replace sample data with verified/live sources.
- Add more cities and real hotel inventory.
- Measure real LLM parsing quality with an opt-in live evaluation.
- Add public holiday rules and walking-limit enforcement.
- Deploy and run live smoke tests after credentials and hosting are approved.

## Built With

Python, FastAPI, Pydantic, OR-Tools, Vue 3, Vite, Bootstrap, Leaflet, OpenStreetMap tiles, Vitest, Playwright, Lighthouse.

## Project And Demo Links

- GitHub: https://github.com/Aish710/AI-lodge
- Deployed app: `[ADD DEPLOYED FRONTEND URL]`
- Backend health URL: `[ADD DEPLOYED BACKEND /health URL]`
- Demo video: `[ADD DEVPOST/YOUTUBE/LOOM URL]`
