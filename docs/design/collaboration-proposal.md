# Collaboration design gate (Phase 8): proposal only, nothing built

Status: **proposal for your approval.** No storage, authentication or multi-user write capability has been added. The service is still stateless and stores nothing.

## 1. Recommended level
Level 1: a **read-only share link** to a saved itinerary. Level 2 (suggestions and votes) only afterwards. Level 3 (collaborative editing) is not recommended for this project.

## 2. Persistence
A saved trip needs server-side storage. Smallest reliable option consistent with the stack: one SQLite file (stdlib `sqlite3`) holding `{token_hash, city_id, preferences, hotel_id, plan (the server-produced result), fingerprint, dataset_version, created_at, expires_at, revoked_at}`. **Open question for you:** whether the host's disk survives redeploys. If it does not, a SQLite file will lose shares on every deploy and the feature should not ship.

## 3. Access model
Capability tokens: 128-bit random, URL-safe, shown once; only a hash is stored; a view-only scope; owner revoke (a second, separate owner token); fixed expiry (e.g. 7 days) with a hard maximum. No accounts. Anonymous viewing of a link is acceptable only because the content is the sample-data plan the owner chose to share.

## 4. Threat model (summary)
Guessable links (mitigated by entropy); link leakage via logs or referrers (token in the path only, `Referrer-Policy: no-referrer`, never logged); stored prompt injection (a shared plan stores only server-produced data and ids, no free text, so nothing stored is ever sent to a model); cross-trip leakage (lookup by token hash only); abuse and storage exhaustion (rate tier, per-IP cap, size cap, expiry sweep); stale plans (dataset version stored; the viewer is told when the data changed); deletion (owner revoke removes the row).

## 5. Level 2 additions (not proposed yet)
Suggestions as structured, validated change proposals (never free text rendered as HTML), owner approval, optimistic concurrency by revision number, server-side authorisation on every mutation, AI never an authorisation decision.

## 6. Effort and risk
Level 1: about one focused day including tests; risk is deployment storage. Level 2: several days. Risks to existing behaviour: none if kept additive (`/share` routes only), but it adds the first persistent personal data and changes the privacy statement ("nothing is stored"), which must then be rewritten.

## 7. Decisions needed
1. Approve Level 1 (yes / no / later).
2. Does the hosting disk persist across deploys?
3. Accept updating the privacy statement.
