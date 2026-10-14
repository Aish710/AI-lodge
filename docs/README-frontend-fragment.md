<!-- Fragment for the README. Facts below were checked against the repository; figures live in the generated files named in brackets. -->

## Frontend: installation

Requirements: Node 22 or newer (developed on Node 24), and the backend running (see the backend steps).

```bash
cd frontend
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000 (a public URL; never put a key here)
npm install
# in another terminal, from backend/:  .venv/bin/uvicorn app.main:app --port 8000
npm run dev                   # http://localhost:5173 (the backend allows this origin by default)
```

Useful commands (run from `frontend/`):

| Command | What it does |
|---|---|
| `npm run build` | Copies the generated evidence files into the build, builds, and writes `_headers` (CSP etc.) and `_redirects` for a static host. Set `VITE_API_BASE_URL` for the build. |
| `npm test` | Unit and component tests (Vitest). |
| `npm run e2e` | End-to-end tests (Playwright) against the real backend in sample mode, plus a CSP check on the real build. Needs `npx playwright install chromium` once. |
| `npm run test:report` | Runs both and writes the JSON summaries the Proof page reads. Run the full backend `pytest` first or last, never only a subset. |
| `npm run lighthouse` | Lighthouse on the built app; writes `docs/lighthouse-results.md`. |
| `node scripts/take-screenshots.mjs` | The named screenshots and the recording in `docs/screenshots/`. |
| `node scripts/live-smoke.mjs <frontend_url> <backend_url>` | Checks a deployed pair; exits non-zero on failure. |

Deployment (Netlify, with the backend on Render): see `docs/DEPLOY.md`.

## What the interface shows

- **Plan your trip, choose sights, compare hotels, itinerary:** a form (days, budget in JPY or SGD with the labelled sample rate, strict budget, pace, day window, value of time, nights, unknown hours off by default), wishlist cards (Must visit / Nice to have / Not interested), a hotel comparison with every line of the true-cost calculation, and an itinerary with a map (numbered pins, colour plus shape per day), a day-by-day timeline, totals and the independent validator's Trip Feasibility Report.
- **Honest about the data:** a persistent "Sample data" banner, source badges on prices, hours and travel times, and "unknown" (never 0 or blank) for missing values. The "AI assistant on / Sample mode (AI unavailable)" indicator comes from `/health`.
- **Decisions are visible:** the "cheapest rate is not the best value" callout appears only when the planner says so; optional sights the planner skipped are listed with the reason; an impossible request shows a conflict panel with alternatives that were actually solved, not an error page.
- **Changing a plan:** lock, unlock, remove or move stops, change the budget or hotel, queue the changes, and apply them in one call. The diff shows before, after and change for every line, with all warnings verbatim. Removing a must-visit needs an explicit confirmation. The previous plan can be restored.
- **AI, optionally:** free text can fill the form or propose changes (always as a proposal you accept or discard), and "Explain this result" gives a number-checked or template summary. Without the AI everything else works.
- **Proof and How it works pages:** measured results with their N and caveats, the risk, safeguard and test table, hardening results and generated claim sentences (all read from files produced by scripts), and an explanation of how the AI is and is not used. [docs/eval-results.md, docs/SAFETY_LOG.md, docs/hardening-results.md, docs/README-claims.md]
- **Privacy:** state lives in the page's memory only (no cookies or local storage); no analytics or third-party scripts; the map loads OpenStreetMap tiles.
- **Accessibility and speed:** keyboard-operable, labelled controls, status never by colour alone; Lighthouse scores as measured are in `docs/lighthouse-results.md`.
