# API hardening

## Principle
Assume the public demo URL will be hit by bots and curious judges. Nothing a client sends is trusted, nothing user-supplied is logged or stored, and the LLM-spending routes can never cost more than a bounded, configured amount.

## Controls and their knobs
| Control | What it does | Config (env var, default) |
|---|---|---|
| Body size cap | Rejected with 413 by `Content-Length` AND while reading (a client can lie about length; chunked bodies are counted) | `BODY_MAX_BYTES`, 65536 |
| Content type | POST must be `application/json`, else 415 | fixed |
| JSON sanity | Nesting deeper than 20 levels: 422 `json_too_deep`; `NaN`/`Infinity`: 422 `invalid_number`; invalid JSON: 422 `invalid_json` | depth fixed at 20 |
| Schema caps | `extra="forbid"` on every request model; days 1-7, hotels <= 3, operations <= 20, locks <= 12, must-visit/skip <= 50 ids, interests <= 20, stops per day <= 12, id/string max lengths, budget <= 100,000,000, value of time <= 100,000, nights <= 30; free text `/parse` <= 10,000 characters (then `MAX_INPUT_CHARS` with a clear `input_too_long` error) | `MAX_INPUT_CHARS`, 2000 |
| Rate limits (per client IP, in-memory sliding window, 60 s) | "expensive" = `/parse`, `/parse-replan`, any request with `explain: true`; "standard" = `/optimise`, `/compare-hotels`, `/replan`; "cheap" = `/health`, `/data/summary`. 429 with `Retry-After`. Rejected requests (413/415/422 at the gate) also consume a token | `RATE_LIMIT_EXPENSIVE_PER_MIN` 6, `RATE_LIMIT_PER_MIN` 30, `RATE_LIMIT_CHEAP_PER_MIN` 120 |
| Client IP | Socket address by default; `X-Forwarded-For` is honoured only up to N trusted hops, taking the entry N-th from the RIGHT (what the nearest trusted proxy appended), so a client-prepended value cannot spoof its way past the limit | `TRUSTED_PROXY_HOPS`, 0 |
| LLM circuit breaker | Counts every real model call (retries included) over a rolling 24 h; at the cap the LLM is disabled, routes answer in sample mode with a clear message, `/health` shows `llm_mode: "sample"` and `llm_limit_reached: true` | `LLM_DAILY_CALL_CAP`, 300 |
| Call caps | At most 2 calls per `/parse`/`/parse-replan` (one retry), 1 per explanation; SDK auto-retries off | `config.py` |
| Deadlines | Overall request deadline; model timeout 10 s; a call (or the retry) is skipped unless enough time remains; then sample mode answers (HTTP 200), never a hang or a 504 from our code | `REQUEST_DEADLINE_SECONDS` 25, `config.LLM_TIMEOUT_SECONDS` 10 |
| Untrusted client schedules | On `/replan` and `/parse-replan` the supplied schedule is validated, then REBUILT server-side from stop ids and start times only (travel, fares, admissions, flags, totals and missed sights recomputed), then checked by the independent validator. Altered durations, unknown ids, bad days, or any validator failure: 422 `invalid_schedule` with findings. Forged cost/total fields are ignored. Explanations are built only from server-computed results | fixed |
| CORS | Exact origins only; `*` and malformed origins refuse to start; GET/POST and `Content-Type` only; error responses (429, 413, ...) carry CORS headers too | `ALLOWED_ORIGINS`, localhost dev origins |
| Security headers | `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, `X-Frame-Options: DENY`, `X-Request-ID` on every response | fixed |
| Docs exposure | `/docs`, `/redoc`, `/openapi.json` are off unless enabled | `ENABLE_DOCS`, 0 |
| Errors | One format `{"error": {"code", "message", "details"?, "request_id"?}}` everywhere. Unhandled exceptions: generic 500 + request id; no trace, paths or values; the log gets exception type and frame locations only (never the exception message, which could contain user data) | fixed |
| Logging | Metadata only (see PRIVACY.md); every log record passes a redactor for keys/bearer tokens; uvicorn's access log (which can contain query strings) is disabled | fixed |
| Startup checks | Invalid config (CORS `*`, bad numbers, expensive limit above standard) or missing data files stop the app with a clear message; a secret-free config summary and startup time are logged | - |

`/optimise` runs the solver with a per-request time limit (`optimise_time_limit_seconds`, 10 s) and a bounded budget (8 s) for computing alternatives when infeasible. A plan that only reaches FEASIBLE carries `approximate: true` and a note. The independent validator runs on every result and a failing report is returned as-is.

## Known limits (be honest about these)
- Rate limits and the circuit breaker are **in memory, per process, per worker**; they reset on restart and are not shared between instances. Run one worker (the Dockerfile does).
- IP-based limiting is imperfect: users behind one NAT share a bucket; attackers with many IPs get many buckets. With `TRUSTED_PROXY_HOPS=0` behind a reverse proxy every user shares ONE bucket (the proxy's address): set the hops value for your host (see DEPLOY.md).
- The circuit breaker counts SDK calls, not tokens or money. **The provider's spending cap is the real cost backstop; set it.**
- Solver work is CPU-bound and not queued: many simultaneous solves on a small host will be slow. The rate limits are the protection.
- The body cap bounds memory per request but not the number of concurrent connections (host-level protection is out of scope here).
- Pydantic validation messages may echo the sender's own field value back to that sender in a 422; they are never logged.
