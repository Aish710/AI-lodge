// Single HTTP client. Everything the UI knows about the network lives here:
//  * one error normaliser for {error:{code,message,details,request_id}} (plus non-JSON proxy/host failures)
//  * abort-by-key so a stale response can never overwrite a newer one
//  * timeouts LONGER than the server's 25 s request deadline (so the server's own answer wins)
//  * retry ONLY for the cold-start /health probe. POSTs are never retried (a retry could double-spend LLM calls)
//  * HTTP 429: the Retry-After value is read from the error body (the browser cannot read the header cross-origin: CORS does not expose it)
// No cookies, no storage, no credentials are ever sent.

export const API_BASE = (import.meta.env?.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')
export const SERVER_DEADLINE_S = 25
export const SOLVE_TIMEOUT_MS = (SERVER_DEADLINE_S + 15) * 1000

export class ApiError extends Error {
  constructor({ code, message, details = {}, status = 0, requestId = null, retryAfter = null }) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.details = details
    this.status = status
    this.requestId = requestId
    this.retryAfter = retryAfter // seconds, only for 429
  }
  /** Message for display, with the request id so a failure can be traced in the server log. */
  get display() {
    return this.requestId ? `${this.message} (request id ${this.requestId})` : this.message
  }
}

export const isAborted = (e) => e instanceof ApiError && e.code === 'aborted'

/** Turn any failed response into an ApiError. `body` is the parsed JSON, a string, or null. */
export function normaliseError({ status, body, requestId = null }) {
  const err = body && typeof body === 'object' ? body.error : null
  if (err && typeof err === 'object' && typeof err.code === 'string') {
    const details = err.details && typeof err.details === 'object' ? err.details : {}
    const retry = status === 429 ? Number(details.retry_after_seconds) : NaN
    return new ApiError({
      code: err.code, message: String(err.message ?? 'The server reported an error.'), details, status,
      requestId: err.request_id ?? requestId, retryAfter: status === 429 ? (Number.isFinite(retry) && retry > 0 ? Math.ceil(retry) : 10) : null,
    })
  }
  if (status === 429) return new ApiError({ code: 'rate_limited', message: 'Too many requests. Please wait a moment.', status, requestId, retryAfter: 10 })
  if (status >= 500 || status === 0) {
    return new ApiError({ code: 'server_unavailable', message: 'The server is not answering properly right now (it may still be waking up).', status, requestId })
  }
  return new ApiError({ code: 'unexpected_response', message: `Unexpected response from the server (HTTP ${status}).`, status, requestId })
}

let rateLimitHandler = () => {}
/** The store registers a function that starts a visible countdown when the server answers 429. */
export function setRateLimitHandler(fn) { rateLimitHandler = fn }

const inflight = new Map()
/** Cancel whatever request is currently in flight for a key (used when inputs change). */
export function abortKey(key) { inflight.get(key)?.abort() }

/**
 * @param {'GET'|'POST'} method
 * @param {string} path
 * @param {{body?: object, key?: string, timeoutMs?: number, fetchImpl?: typeof fetch}} [opts]
 *   key: a newer request with the same key aborts the older one (its caller gets an 'aborted' ApiError and must ignore it)
 */
export async function request(method, path, { body, key, timeoutMs = SOLVE_TIMEOUT_MS, fetchImpl } = {}) {
  const doFetch = fetchImpl ?? ((...a) => fetch(...a))
  const controller = new AbortController()
  if (key) {
    inflight.get(key)?.abort()
    inflight.set(key, controller)
  }
  let timedOut = false
  const timer = setTimeout(() => { timedOut = true; controller.abort() }, timeoutMs)
  const stale = () => key && inflight.get(key) !== controller
  try {
    let res
    try {
      res = await doFetch(API_BASE + path, {
        method, signal: controller.signal, cache: 'no-store', credentials: 'omit', referrerPolicy: 'no-referrer',
        headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      })
    } catch (e) {
      if (timedOut) throw new ApiError({ code: 'timeout', message: 'The server took too long to answer. The request was cancelled; your input is still here.' })
      if (controller.signal.aborted || e?.name === 'AbortError') throw new ApiError({ code: 'aborted', message: 'Superseded by a newer request.' })
      throw new ApiError({ code: 'network', message: 'Could not reach the server. Check your connection, or the server may be waking up.' })
    }
    const text = await res.text().catch(() => '')
    if (stale()) throw new ApiError({ code: 'aborted', message: 'Superseded by a newer request.' })
    let parsed = null
    try { parsed = text ? JSON.parse(text) : null } catch { parsed = text }
    if (!res.ok) {
      const err = normaliseError({ status: res.status, body: parsed, requestId: res.headers?.get?.('x-request-id') ?? null })
      if (err.code === 'rate_limited' || res.status === 429) rateLimitHandler(err.retryAfter ?? 10)
      throw err
    }
    if (parsed === null || typeof parsed !== 'object') throw new ApiError({ code: 'unexpected_response', message: 'The server sent a response the app could not read.', status: res.status })
    return parsed
  } finally {
    clearTimeout(timer)
    if (key && inflight.get(key) === controller) inflight.delete(key)
  }
}

const defaultSleep = (ms) => new Promise((r) => setTimeout(r, ms))

/**
 * Cold-start probe. A free host sleeps when idle, so the first request can hang or fail for about a minute. Retries GET /health with
 * backoff for up to `maxMs`, calling `onWaking` once as soon as the first attempt is slow or fails. Never throws for "slow"; throws
 * server_unreachable only after `maxMs`. A 429 means the server is awake, so it counts as success.
 */
export async function waitForServer({
  ping = () => request('GET', '/health', { timeoutMs: 8000 }), sleep = defaultSleep, now = () => Date.now(),
  maxMs = 90_000, slowAfterMs = 2500, onWaking = () => {}, backoff = [1000, 2000, 4000, 8000],
} = {}) {
  const start = now()
  let attempt = 0
  let waking = false
  const markWaking = () => { if (!waking) { waking = true; onWaking() } }
  for (;;) {
    const slow = setTimeout(markWaking, slowAfterMs)
    try {
      const health = await ping()
      return { health, waited: waking }
    } catch (e) {
      if (e instanceof ApiError && e.code === 'rate_limited') return { health: null, waited: waking }
      if (isAborted(e)) throw e
      markWaking()
      if (now() - start >= maxMs) {
        throw new ApiError({ code: 'server_unreachable', message: 'The server did not wake up in time. Please try again in a minute.' })
      }
      await sleep(backoff[Math.min(attempt, backoff.length - 1)])
      attempt += 1
    } finally {
      clearTimeout(slow)
    }
  }
}
