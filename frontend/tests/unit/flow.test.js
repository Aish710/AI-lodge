import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { chooseHotel, rateLimited, rateLimitSeconds, resetAll, runOptimise, store, boot, loadExample } from '../../src/store.js'
import { setRateLimitHandler } from '../../src/api/client.js'
import { errBody, res } from './helpers.js'
import infeasible from '../fixtures/optimise-infeasible.json'
import feasible from '../fixtures/optimise-feasible.json'
import places from '../fixtures/places.json'

beforeEach(() => { resetAll(); store.planError = null; chooseHotel('hotel_lantern_asakusa') })
afterEach(() => { vi.unstubAllGlobals(); store.rateLimitUntil = 0 })

describe('responses are routed to the right UI path', () => {
  it('an HTTP 200 with status "infeasible" is stored as a plan (conflict panel), NOT as an error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, infeasible)))
    await runOptimise()
    expect(store.planError).toBeNull()
    expect(store.plan.result.status).toBe('infeasible')
    expect(store.plan.result.conflicts.length).toBeGreaterThan(0)
  })
  it('a feasible response is stored as a plan', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, feasible)))
    await runOptimise()
    expect(store.plan.result.status).toBe('feasible')
    expect(store.planError).toBeNull()
  })
  it('a real error ({error:{...}}) becomes planError (error component) and leaves no plan', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(422, errBody('invalid_request', 'days must be at most 7', {}, 'r1'))))
    await runOptimise()
    expect(store.plan).toBeNull()
    expect(store.planError).toMatchObject({ code: 'invalid_request', requestId: 'r1' })
  })
  it('a failed re-run keeps the previous plan on screen', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, feasible)))
    await runOptimise()
    vi.stubGlobal('fetch', vi.fn(async () => res(500, errBody('internal_error', 'Internal error.'))))
    await runOptimise()
    expect(store.plan.result.status).toBe('feasible')
    expect(store.planError.code).toBe('internal_error')
  })
  it('invalid form input never reaches the network', async () => {
    const f = vi.fn()
    vi.stubGlobal('fetch', f)
    store.form.days = 12
    await runOptimise()
    expect(f).not.toHaveBeenCalled()
    expect(store.planError.code).toBe('invalid_input')
  })
})

describe('429 handling (decision 9)', () => {
  it('starts a visible countdown from the server-provided seconds', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(429, errBody('rate_limited', 'Too many requests. Please slow down.', { retry_after_seconds: 12 }))))
    await runOptimise()
    expect(store.planError.code).toBe('rate_limited')
    expect(rateLimited.value).toBe(true)
    expect(rateLimitSeconds.value).toBeGreaterThanOrEqual(11)
    expect(rateLimitSeconds.value).toBeLessThanOrEqual(12)
  })
})

describe('cold start at boot (decision 9)', () => {
  it('shows "waking" while /health is slow or failing, then becomes ready and loads the places', async () => {
    let n = 0
    const f = vi.fn(async (url) => {
      if (String(url).endsWith('/health')) { n += 1; if (n < 2) throw new TypeError('Failed to fetch'); return res(200, { status: 'ok', mode: 'sample', llm_configured: false, llm_mode: 'sample', llm_limit_reached: false }) }
      return res(200, places)
    })
    vi.stubGlobal('fetch', f)
    const states = []
    const stop = setInterval(() => states.push(store.server), 1)
    const p = boot({ ping: async () => (await import('../../src/api/routes.js')).getHealth() })
    // fast-forward the 1 s backoff by letting real time pass
    await p
    clearInterval(stop)
    expect(states).toContain('waking')
    expect(store.server).toBe('ready')
    expect(store.places).toHaveLength(12)
    expect(store.hotelsById.hotel_lantern_asakusa.name).toBeTruthy()
  }, 10000)
})

describe('demo helpers', () => {
  it('load the pre-tested requests', () => {
    loadExample('impossible')
    expect(store.wishlist).toMatchObject({ akihabara: 'must', senso_ji: 'must' })
    expect(store.chosenHotel).toBe('hotel_lantern_asakusa')
    loadExample('valid')
    expect(store.form.days).toBe(3)
    expect(store.hotelIds).toHaveLength(3)
  })
})
