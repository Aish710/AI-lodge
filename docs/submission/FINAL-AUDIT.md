# Final audit (a tick-list; ticked only where a file or a run backs it)

No grades here: each line names the exact artifact a judge opens. `[ ]` means it needs you.

## Devpost requirements
- [x] Title, and the pitch line as the first line of the text: `docs/submission/devpost.md`
- [x] Inspiration, What it does, How I built it, AI safety and responsible design, Results with N, Challenges, What I learned, What's next, Built with, Links: `docs/submission/devpost.md`
- [ ] Fill every `[PLACEHOLDER: ...]` in `devpost.md` (inspiration sentence, takeaways, URLs, video, the optional live red-team re-run)
- [ ] Demo video link (script: `docs/submission/DEMO-SCRIPT-FINAL.md`)
- [ ] Live app link and backend link (checklist: `docs/DEPLOY.md`, top; smoke commands inside)
- [x] GitHub link: https://github.com/Aish710/AI-lodge
- [ ] LinkedIn post: `docs/submission/linkedin.md` (proudest moment and takeaways are yours to choose)

## GitHub requirements
- [x] README with the seven required headings in order: `README.md` (`python3 scripts/check_claims.py` also checks them)
- [x] Installs from a clean clone: `cd frontend && npm run verify:clean-clone` (passed at the last commit)
- [x] No secrets in the tree or the history: `docs/submission/SECRETS-AUDIT.md` (commands and results); `backend/.env` is gitignored
- [ ] Repository is public (or shared as the hackathon requires), and the final commit is pushed to `origin/main`
- [x] Evidence is generated, current and consistent: `docs/EVIDENCE-STATUS.md`, `python3 scripts/check_doc_consistency.py`, `python3 scripts/check_claims.py`

## Judging criterion: AI Integration Effectiveness
- Where the AI is used and where it is not: `README.md` section 4; the "How it works" page; `docs/LLM_DESIGN.md`
- The pipeline around it (optimiser, validator, grounding, leak guard, template fallback): `backend/app/llm/`, `backend/app/optimiser/`, `backend/app/validator/`
- Live behaviour with a real model, with its history of failures and fixes: `docs/ai-selfcheck.md`, `docs/ai-selfcheck-history.md`, `docs/eval/gold-results-live-first-run.md` beside the latest gold file, the Proof page "Live AI evidence"
- The AI is visible in the product: the first card on Plan, the change box and Explain button on Your trip, the "What the AI did" drawer (`docs/screenshots/steps/*-ai-canned-*` are interface pictures with canned responses, not evidence of model behaviour)
- Gaps stated: one model through a third-party gateway; tuned checks; the gold set was written by the builder; cited explanations and an AI on/off view are not built

## Judging criterion: LLM Safety & Responsible AI
- Risk, safeguard, test table: `docs/SAFETY_LOG.md`, `README.md` section 7, the Proof page risk table
- Red team, simulated: `docs/redteam-results.md`, `backend/tests/fixtures/redteam_attacks.json`, `backend/tests/test_redteam.py`; live: `docs/redteam-live.md` beside `docs/redteam-live-first-run.md`
- Hardening: `docs/hardening-results.md`; privacy: `docs/PRIVACY.md` (names the gateway)
- Honest data labelling: `docs/data-verification/counts.md`, `docs/data-verification/CHANGELOG.md`, the Proof page "Data verification"
- Gaps stated: the red-team counts are from simulated models; the live red team is one run; the gateway sees the cleaned text; all city data is sample data; no external security review

## Judging criterion: Usefulness & Business Value
- The problem and who it is for: `README.md` section 1; the verdict on Your trip
- Measured, with N and caveats: `docs/eval-results.md`, `docs/city-eval-results.md`, `docs/hotel-comparison-results.md`; `docs/ux-metrics.md` (machine-dependent)
- Real users: the kit is in `docs/user-test/` (protocol, test card, scripts) and the Proof page says "Not run yet" until rows exist. [ ] Run it if you can (5 to 10 people)
- Gaps stated: sample data and made-up hotels; no user study; the evaluation is on seeded synthetic trips; in most random trips the cheapest hotel is also the best
