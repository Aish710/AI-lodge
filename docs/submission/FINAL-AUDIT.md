# Final Audit Checklist

## Devpost Requirements

- [ ] Project title: Fitinerary.
- [ ] Inspiration, what it does, build details, AI integration, safety, challenges, results, learning, next steps.
- [ ] Demo video link added.
- [ ] Live app link added.
- [ ] GitHub link added.

Strongest evidence: `docs/submission/devpost.md`, `README.md`, `docs/SUBMISSION-FACTS.md`.

## GitHub Repository Visibility

- [ ] Repository is public or shared as required by the hackathon.
- [ ] Final commit pushed to `origin/main`.
- [ ] No API keys or secrets committed.

## README Completeness

- [x] Problem statement.
- [x] Solution overview.
- [x] Key features.
- [x] AI integration.
- [x] External tools and datasets.
- [x] Installation and setup.
- [x] AI safety and limitations.

## Working Deployed URL

- [ ] Backend deployed.
- [ ] Frontend deployed.
- [ ] `ALLOWED_ORIGINS` matches frontend origin.
- [ ] `VITE_API_BASE_URL` points at HTTPS backend.
- [ ] Live smoke test passes.

Requires credentials/provider account/manual action.

## Demo Recording

- [ ] Recording reviewed.
- [ ] Devpost-compatible link uploaded.
- [ ] No secrets visible.

Existing artifact: `docs/screenshots/demo-core-flow.webm` when screenshots are regenerated.

## LinkedIn Post

- [ ] Fill personal placeholders in `docs/submission/linkedin.md`.
- [ ] Add final project/demo links.
- [ ] Post after submission is approved.

## AI Safety Evidence

Strongest artifacts:

- `docs/SAFETY_LOG.md`: risk, safeguard, test table.
- `docs/hardening-results.md`: API abuse battery.
- `docs/EVALUATION.md` and `docs/eval-results.md`: generated evaluation method/results.
- `backend/tests/test_llm_api_safety.py`: mocked LLM safety tests.

## Judging Criteria

- Innovation: hotel and itinerary are optimised together by true cost.
- Technical implementation: OR-Tools solver, independent validator, FastAPI hardening, Vue frontend.
- AI use: LLM reads natural language and explains computed results without making hidden planning decisions.
- Responsible AI: prompt-injection safeguards, grounding checks, sample mode, explicit limitations.
- Demo quality: screenshots, demo video, evidence page, local/live smoke tests.
- Measured impact: generated evaluation and replanning metrics in `docs/SUBMISSION-FACTS.md`.

## Remaining Manual Actions

- Deploy backend and frontend.
- Set provider spending cap before adding any LLM key.
- Verify Render proxy hops.
- Run live smoke tests.
- Run screenshot process with `--repeat=3` and inspect `docs/screenshots/screenshot-run-report.json`.
- Run final secret scan.
- Fill LinkedIn placeholders.
- Add final deployed/demo URLs to submission docs.
