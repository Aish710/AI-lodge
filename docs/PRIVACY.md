# Privacy

This documents what the backend actually does today.

## What is processed
- Trip preferences, schedules and operations you send, to compute plans.
- Free text sent to `/parse` and `/parse-replan`, after sanitising (length cap, control and invisible characters removed, wrapped in data tags).
- Your IP address (or the proxy-reported client IP, if `TRUSTED_PROXY_HOPS` is set) is used in memory only, as the rate-limit key.

## What is stored
**Nothing persistent.** There is no database and no file output of user data. Plans are computed per request and returned; the replanning API is stateless (the client sends the current schedule each time). Server memory holds only: the sample dataset, rate-limit counters keyed by client IP (timestamps for at most 60 seconds), and a list of timestamps of LLM calls (for the 24-hour call cap). These disappear on restart.

## What is logged
Metadata only: request id, HTTP method, route name (unknown paths are logged as `unmatched`), status code, latency, rate-limit tier, whether the request was rate limited, number of LLM calls and token counts, and an outcome category. Server errors additionally log the exception type and source locations (not the message). **Never logged:** request bodies, query strings, headers, user text, prompts, model output, API keys, or the client IP. A redaction filter removes anything shaped like a key or bearer token from every log record; uvicorn's access log is disabled.

## What is sent to the LLM provider
Only when a key is configured and the LLM is available:
- `/parse`: the sanitised free text you typed.
- `/parse-replan`: the sanitised text plus the names of the attractions in your current itinerary.
- Explanations (`explain: true`): a block of computed facts about the result (names, JPY figures, minutes, solver status, warnings).
**Relay (third-party gateway).** If `LLM_BASE_URL` is set, those requests go to that gateway's host, not directly to the model provider: the gateway sees the sanitised text and the computed facts (and the API key, which it needs to authenticate you), and forwards them to the model provider. Both parties then process them under their own terms and retention, which this project does not control. `/health` shows the gateway's host (and `llm_relay: true`) so this is never hidden; the full URL and the key are never logged or returned. Never describe such a deployment as "direct to Anthropic".

**Never sent:** attraction descriptions, API keys, other users' data, or anything you did not submit for that call. The model has no tools or web access. The provider processes requests under its own terms and retention policy (see its documentation; this project does not control it).

## Retention
This service retains nothing. Logs on the host follow the host's log retention (for example Render's log streams); they contain only the metadata above. No analytics or cookies are used by the API.

## Sample data notice
All attraction, price, hours and travel figures are sample or estimated data; hotels are fictional.
