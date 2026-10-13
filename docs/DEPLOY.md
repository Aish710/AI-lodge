# Deploying the backend (Render, free plan)

I could not deploy for you or build the Docker image locally (Docker is not installed on this machine). Everything below is prepared; the steps are for you.

## Why Render (one option only)
Checked against Render's current docs on 2026-10-13:
- Free web services support Docker (Blueprint `runtime: docker`, `plan: free`), so OR-Tools installs from the pinned wheels. Sources: [Render free tier](https://render.com/docs/free), [Blueprint spec](https://render.com/docs/blueprint-spec).
- Free plan: **512 MB RAM and 0.1 CPU** ([compute plans](https://render.com/docs/compute-plans)), 750 free instance hours per month per workspace, one instance, ephemeral disk.
- **Sleeps after 15 minutes without traffic; waking takes about a minute** ("a spun-down service restarts when it gets an HTTP request ... about one minute").
- If a workspace has no payment method and uses up included bandwidth or hours, free services are suspended until the next month.
- Hugging Face Docker Spaces were rejected: Docker Spaces now require a paid plan to create ([Spaces overview](https://huggingface.co/docs/hub/spaces-overview)).

Measured locally (not on Render): process start to first `/health` 200 in about 1.4 s; resident memory about 120 MB after the smoke test and after a 7-day solve (comfortably inside 512 MB). **Unknown until you deploy:** 0.1 CPU is a small share. Solves that take 0.1-2 s here (and about 5 s for a 7-day trip) may be several times slower there; the solver has wall-clock limits (`/optimise` 10 s) so it returns a labelled approximate plan rather than hanging, but expect slower and less optimal results on long trips. If that is a problem, the paid Starter plan is the next step.

## Steps
1. Push the repo to GitHub (never commit `.env`; `.gitignore` already excludes it).
2. Render dashboard: **New > Blueprint**, select the repo. It reads `render.yaml` (service `tokyo-trip-planner-api`, region Singapore, Docker, free plan, health check `/health`).
3. When prompted for `sync: false` variables, enter them (see table). Leave `LLM_API_KEY` empty to launch in sample mode first (recommended).
4. Wait for the build. Note the service URL (`https://tokyo-trip-planner-api.onrender.com` or similar).
5. **Set a spending cap at your LLM provider before putting a key on the host** (provider console > billing/usage limits). The in-app `LLM_DAILY_CALL_CAP` is per process and resets on restart; the provider cap is the real backstop.
6. Verify: `python backend/scripts/smoke_test.py https://<your-service>.onrender.com` (waits up to 150 s for the cold start; exits non-zero on any failure).
7. Later, when the frontend is deployed (e.g. Vercel/Netlify), set `ALLOWED_ORIGINS` to its exact origin (e.g. `https://your-app.vercel.app`, no trailing path; several origins comma-separated) and redeploy/restart. Do not use `*`: the app refuses to start.

## Environment variables
| Variable | Secret? | Recommended | Notes |
|---|---|---|---|
| `LLM_API_KEY` | **YES** | empty first, then your key | Dashboard only. Never in git. |
| `LLM_MODEL` | no | e.g. `claude-opus-5-5` or a cheaper model of your choice | Required together with the key. |
| `LLM_EFFORT` | no | `low` (default) | Empty = do not send the parameter (for models that reject it). |
| `ALLOWED_ORIGINS` | no | frontend origin | Exact origins only. |
| `TRUSTED_PROXY_HOPS` | no | `1` to start, then verify | See below. |
| `RATE_LIMIT_EXPENSIVE_PER_MIN` | no | `6` | `/parse`, `/parse-replan`, `explain: true`. Must be <= the standard limit. |
| `RATE_LIMIT_PER_MIN` | no | `30` | Standard tier. |
| `RATE_LIMIT_CHEAP_PER_MIN` | no | `120` | `/health`, `/data/summary`. |
| `LLM_DAILY_CALL_CAP` | no | `300` | Per process, rolling 24 h. |
| `REQUEST_DEADLINE_SECONDS` | no | `25` | Model timeout is 10 s. |
| `BODY_MAX_BYTES` | no | `65536` | |
| `MAX_INPUT_CHARS` | no | `2000` | Free-text limit. |
| `ENABLE_DOCS` | no | `0` | Never `1` in production. |
| `PORT` | no | set by Render (default 10000) | Do not set it yourself. |

### Choosing `TRUSTED_PROXY_HOPS` (verify, do not guess)
Render's docs I could reach do not state how many `X-Forwarded-For` entries its proxies add, so check empirically.
- If you leave it at `0` behind a proxy, every visitor shares ONE rate-limit bucket (the proxy's address): a handful of judges could lock each other out.
- If it is too high, the entry read from the right is one a client can influence, and rate limiting can be bypassed.
Procedure after the first deploy: from your laptop, send 40 quick `GET /health` requests (limit 120/min, so lower `RATE_LIMIT_CHEAP_PER_MIN` to `20` temporarily), each with a different fake `X-Forwarded-For: 10.0.0.<n>` header. If you receive 429s after the 20th, the setting reads a proxy-appended entry (spoofing is ineffective): good. If you never get a 429, the value is too high: reduce it. Then, from a second network (phone on mobile data), confirm you are NOT limited by the laptop's traffic (separate buckets); if you are, the value is too low. Restore the limit.

## Cold start
The first request after 15 idle minutes takes about a minute while Render wakes the container; the app itself starts in about 1-2 seconds. The frontend must show a "waking the server, this can take about a minute" message and retry `/health`. `smoke_test.py` already waits for it. Optional: an external uptime pinger every 10 minutes keeps it awake but uses the 750 free hours (about 744 hours in a month: it would just fit one service).

## Checking the logs for leakage
Render dashboard > service > Logs. After a smoke test, search for: your key prefix (`sk-ant`), a test phrase you sent in a `/parse` request, `Bearer`, and a query string you appended (`/health?q=SECRET123`). None of them should appear: lines are JSON objects with request id, route, status, latency, tier, LLM call and token counts. Server errors show the exception type and frame locations only.

## If you run the container yourself
`docker build -t tokyo-planner ./backend && docker run -p 8000:8000 -e ALLOWED_ORIGINS=http://localhost:5173 tokyo-planner`. The Dockerfile uses a slim Python image, a non-root user, pinned runtime dependencies (`requirements.txt`; test dependencies are in `requirements-dev.txt`), and a health check. Not built here (no Docker available); the same commands were verified outside Docker with uvicorn.
