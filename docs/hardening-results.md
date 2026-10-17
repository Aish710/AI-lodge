# Hardening results (in-process abuse battery)

Generated 2026-10-17 20:39 UTC by `backend/scripts/run_hardening_checks.py`. In-process app, scripted fake LLM, no network. Result: **33/33 cases passed**.

| Case | Expected | Observed | Result |
|---|---|---|---|
| Malformed JSON body | 422 invalid_json | HTTP 422, invalid_json | PASS |
| Empty body | 422 validation_error | HTTP 422, validation_error | PASS |
| Wrong content type | 415 | HTTP 415, unsupported_media_type | PASS |
| Missing content type | 415 | HTTP 415, unsupported_media_type | PASS |
| Unknown top-level field | 422 | HTTP 422, validation_error | PASS |
| Unknown nested field (allow_everything) | 422 | HTTP 422, validation_error | PASS |
| NaN in body | 422 invalid_number | HTTP 422, invalid_number | PASS |
| Infinity in body | 422 invalid_number | HTTP 422, invalid_number | PASS |
| JSON nested 40 levels | 422 json_too_deep | HTTP 422, json_too_deep | PASS |
| Oversize body (200 KB) | 413 | HTTP 413, payload_too_large | PASS |
| Negative budget | 422 | HTTP 422, validation_error | PASS |
| Absurd value of time (10^9) | 422 | HTTP 422, validation_error | PASS |
| 101-character interest strings x21 | 422 | HTTP 422, validation_error | PASS |
| 4 hotels in a comparison | 422 | HTTP 422, validation_error | PASS |
| Unknown hotel id | 422 unknown_hotel | HTTP 422, unknown_hotel | PASS |
| Unknown route | 404 not_found | HTTP 404, not_found | PASS |
| Wrong method | 405 | HTTP 405, method_not_allowed | PASS |
| Docs hidden by default (/docs) | 404 | HTTP 404, not_found | PASS |
| OpenAPI hidden by default | 404 | HTTP 404, not_found | PASS |
| Injection strings to /parse (sample mode) | 200 llm_unavailable or clean 422; no 5xx | statuses [200, 422] | PASS |
| Injection string as hotel id | 422 unknown_hotel, no echo of internals | HTTP 422 | PASS |
| Tampered schedule: negative duration | 422 invalid_schedule | HTTP 422, invalid_schedule | PASS |
| Tampered schedule: unknown attraction | 422 invalid_schedule | HTTP 422, invalid_schedule | PASS |
| Tampered schedule: missing must-visit | 422 invalid_schedule | HTTP 422, invalid_schedule | PASS |
| Tampered schedule: day out of range | 422 invalid_schedule | HTTP 422, invalid_schedule | PASS |
| Forged costs in a valid schedule | 200, forged figures ignored | HTTP 200, admissions recomputed = 2100 | PASS |
| CORS: disallowed origin | no Access-Control-Allow-Origin | header absent | PASS |
| CORS wildcard at startup | refused (ConfigError) | ConfigError raised | PASS |
| 30 requests with rotating spoofed X-Forwarded-For (0 trusted hops) | 20 x 200 then 429s | 20 x 200, 10 x 429 | PASS |
| Burst of 10 /parse (expensive tier, limit 5) | 5 x 200 then 429s | 5 x 200, 5 x 429 | PASS |
| 429 carries Retry-After and unified error | Retry-After header, error.code rate_limited | Retry-After 60 | PASS |
| Fake API key across 3 GET + 20 malformed POST responses | key never in any response | not found in any response body | PASS |
| Forced internal exception | generic 500 with request id, no internals | HTTP 500, body keys ['code', 'message', 'request_id'] | PASS |

## Latency of normal requests (this machine, in-process, N=40 each)

| Request | p50 (ms) | p95 (ms) |
|---|---|---|
| GET /health | 0.3 | 0.4 |
| GET /data/summary | 0.6 | 0.7 |
| POST /optimise | 1.4 | 1.8 |
| POST /compare-hotels (2 hotels) | 2.2 | 2.5 |
| POST /replan (lock) | 2.0 | 2.3 |
| POST /parse (sample mode) | 0.5 | 0.6 |

In-process latency excludes network and TLS. A free host with a fraction of a CPU will be slower (see docs/DEPLOY.md).
Limits shown are the test configuration (small values so bursts are visible), not the production defaults.
