# Secrets and history audit

Run on the whole git history (52 commits on all refs) read-only; `backend/.env` was never opened. Only counts and masked prefixes are shown.

| Command | Result |
|---|---|
| `git rev-list --all \| wc -l` | 52 commits |
| `git log --all --name-only --format= \| grep -E '(^\|/)\.env$' \| sort -u \| wc -l` | **0** (a `.env` file was never committed) |
| `git log --all --name-only --format= \| grep -E '\.(pem\|key\|p12)$\|id_rsa\|credentials' \| sort -u \| wc -l` | **0** |
| `git log --all -p --format= \| grep -E "^\+" \| grep -cE "sk-[A-Za-z0-9_-]{20,}"` | 7 lines, **all test constants**: `FAKE_KEY`, `KEY = "sk-ant-FAKE…"` and `CANARY_KEY` in tests and in a release-gate test that proves the gate catches a key-shaped string. A filter that drops lines containing FAKE, CANARY, test, dist or assets.js leaves **0** |
| `git log --all -p --format= \| grep -E "^\+" \| grep -iE "(LLM_API_KEY\|API_KEY)[ ]*[=:][ ]*['\"]?[A-Za-z0-9_-]{16,}"` | **0** |
| `git log --all -p --format= \| grep -E "^\+" \| grep -cE "Bearer [A-Za-z0-9._-]{20,}"` | **0** |
| `git log --all -p --format= \| grep -E "^\+" \| grep -cE "eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"` (JWT-shaped tokens, e.g. a OneMap token) | **0** |
| `git check-ignore -v backend/.env` | `.gitignore:155:.env` (ignored) |
| `git ls-files \| grep -iE "\.env"` | `.env.example` and `frontend/.env.example` only (placeholders) |

Not covered: secrets in a form these patterns do not match (a key with no recognisable prefix assigned in code under another name). The release gate (`npm run build:release`) also scans the built assets for key-shaped strings. If you ever pasted a key anywhere outside the repository, rotate it.
