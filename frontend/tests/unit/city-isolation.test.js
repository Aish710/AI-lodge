// One trip covers one city. These tests pin the frontend side: every payload carries the store's city and only that city's ids,
// a switch leaves nothing behind, and a late answer for the old city is discarded.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { applyQueue, chooseHotel, resetAll, runCompare, runOptimise, runParse, runProposal, selectCity, store } from '../../src/store.js'
import { clearedOnCitySwitch, cleanHotelText } from '../../src/lib/names.js'
import { res } from './helpers.js'
import tokyo from '../fixtures/places-tokyo.json'
import singapore from '../fixtures/places-singapore.json'
import seoul from '../fixtures/places-seoul.json'
import kl from '../fixtures/places-kuala_lumpur.json'

const PLACES = { tokyo, singapore, seoul, kuala_lumpur: kl }
const CITIES = Object.keys(PLACES)
const ids = (c) => ({ att: new Set(PLACES[c].attractions.map((a) => a.id)), hotel: new Set(PLACES[c].hotels.map((h) => h.id)) })

function planFor(city) {
  const a = PLACES[city].attractions
  const stop = (id, start, end) => ({ attraction_id: id, start, end, travel_minutes_from_previous: 10, transport_jpy_from_previous: 0, cost: 0, cost_status: 'known', is_must_visit: false, uncertainty_flags: [] })
  return { status: 'feasible', hotel_id: PLACES[city].hotels[0].id, days: [{ day: 1, weekday: 'mon', stops: [stop(a[0].id, '10:00', '11:00'), stop(a[1].id, '12:00', '13:00')], hotel_departure: '09:30', hotel_return: '18:00', return_travel_minutes: 10, return_transport_jpy: 0 }],
    totals: {}, conflicts: [], alternatives: [], notes: [], missed_preferences: [], solver_meta: {} }
}

/** A fetch that answers from the city named in the request, recording every request body. */
function recordingFetch(sent) {
  return vi.fn(async (url, init) => {
    const body = init?.body ? JSON.parse(init.body) : null
    sent.push({ url, body })
    const city = body?.city_id ?? new URL(`http://x${url}`).searchParams.get('city_id')
    if (url.includes('/data/places')) return res(200, PLACES[city])
    if (url.includes('/health')) return res(200, { status: 'ok', mode: 'sample', llm_configured: false, llm_mode: 'sample', llm_limit_reached: false })
    if (url.includes('/optimise')) return res(200, { city_id: city, result: planFor(city), feasibility_report: { overall: 'pass', checks: [], data_quality_warnings: [], summary: '' }, approximate: false, nights_used: 1, nights_source: 'x' })
    if (url.includes('/compare-hotels')) return res(200, { city_id: city, results: [], ranking: [], warnings: [] })
    if (url.includes('/parse-replan')) return res(200, { city_id: city, status: 'ok', operations: [] })
    if (url.includes('/parse')) return res(200, { city_id: city, status: 'llm_unavailable' })
    if (url.includes('/replan')) return res(200, { city_id: city, status: 'rejected', warnings: [] })
    return res(404, { error: { code: 'not_found', message: 'x' } })
  })
}

async function setUpCity(city) {
  store.cities = CITIES.map((c) => PLACES[c].city)
  store.cityId = 'tokyo'
  store.city = PLACES.tokyo.city
  if (city !== 'tokyo') await selectCity(city)
  else { store.places = PLACES.tokyo.attractions; store.placesById = Object.fromEntries(tokyo.attractions.map((a) => [a.id, a])); store.hotelsById = Object.fromEntries(tokyo.hotels.map((h) => [h.id, h])) }
}

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); resetAll() })

describe('payloads carry the store city and only that city\'s ids (every city)', () => {
  for (const city of CITIES) {
    it(`${city}: optimise, compare, parse, replan and parse-replan`, async () => {
      const sent = []
      vi.stubGlobal('fetch', recordingFetch(sent))
      await setUpCity(city)
      const a = PLACES[city].attractions
      store.wishlist = { [a[0].id]: 'must', [a[1].id]: 'skip' }
      store.hotelIds = PLACES[city].hotels.slice(0, 2).map((h) => h.id)
      chooseHotel(PLACES[city].hotels[0].id)
      sent.length = 0
      await runCompare()
      await runOptimise()
      await runParse('two relaxed days')
      store.queue = [{ op: 'remove', attraction_id: a[1].id }, { op: 'switch_hotel', hotel_id: PLACES[city].hotels[1].id }]
      await runProposal('make it cheaper')
      await applyQueue()
      const posts = sent.filter((s) => s.body)
      expect(posts.length).toBeGreaterThanOrEqual(5)
      const own = ids(city)
      for (const { url, body } of posts) {
        expect(body.city_id, url).toBe(city)
        const att = [...(body.preferences?.must_visit ?? []), ...(body.preferences?.skip ?? []), ...(body.preferences?.locked ?? []).map((l) => l.attraction_id),
          ...(body.operations ?? []).map((o) => o.attraction_id).filter(Boolean),
          ...(body.current_result?.days ?? []).flatMap((d) => d.stops.map((s) => s.attraction_id))]
        const hot = [body.hotel_id, ...(body.hotel_ids ?? []), body.current_result?.hotel_id, ...(body.operations ?? []).map((o) => o.hotel_id)].filter(Boolean)
        for (const id of att) expect(own.att.has(id), `${url}: ${id} is not a ${city} sight`).toBe(true)
        for (const id of hot) expect(own.hotel.has(id), `${url}: ${id} is not a ${city} hotel`).toBe(true)
      }
    })
  }
})

describe('switching city', () => {
  it('leaves nothing from the old city behind and aborts what was in flight', async () => {
    const sent = []
    vi.stubGlobal('fetch', recordingFetch(sent))
    await setUpCity('seoul')
    const a = PLACES.seoul.attractions
    Object.assign(store, { wishlist: { [a[0].id]: 'must' }, hotelIds: PLACES.seoul.hotels.slice(0, 2).map((h) => h.id), chosenHotel: PLACES.seoul.hotels[0].id,
      comparison: { results: [] }, comparisonKey: 'k', plan: { result: planFor('seoul') }, planPrefs: { days: 1 }, planKey: 'k', queue: [{ op: 'remove', attraction_id: a[0].id }],
      previous: { plan: {} }, lastReplan: { status: 'applied' }, parseResult: { status: 'ok' }, proposal: { status: 'ok' } })
    store.explanations.compare = { text: 'x' }
    const before = clearedOnCitySwitch(store)
    expect(before.join('|')).toMatch(/wishlist.*hotel selection.*comparison.*itinerary.*pending changes.*replan history/)

    await selectCity('tokyo')

    expect(store.cityId).toBe('tokyo')
    expect(store.city.id).toBe('tokyo')
    expect(store.wishlist).toEqual({})
    expect(store.hotelIds).toEqual([])
    expect(store.chosenHotel).toBeNull()
    expect(store.comparison).toBeNull()
    expect(store.plan).toBeNull()
    expect(store.queue).toEqual([])
    expect(store.previous).toBeNull()
    expect(store.lastReplan).toBeNull()
    expect(store.parseResult).toBeNull()
    expect(store.proposal).toBeNull()
    expect(store.explanations).toEqual({ optimise: null, compare: null, replan: null })
    expect(Object.keys(store.hotelsById).sort()).toEqual(PLACES.tokyo.hotels.map((h) => h.id).sort())
    expect(Object.keys(store.placesById).sort()).toEqual(PLACES.tokyo.attractions.map((x) => x.id).sort())
    expect(store.form.budgetCurrency).toBe('JPY')
    expect(clearedOnCitySwitch(store)).toEqual([])
  })

  it('discards a late answer for the old city (stale response) and logs only metadata', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    let release
    const late = new Promise((r) => { release = r })
    const fetchMock = vi.fn(async (url, init) => {
      if (url.includes('/data/places')) return res(200, PLACES[new URL(`http://x${url}`).searchParams.get('city_id')])
      if (url.includes('/optimise')) { await late; return res(200, { city_id: 'seoul', result: planFor('seoul'), feasibility_report: { overall: 'pass', checks: [], data_quality_warnings: [], summary: 'SECRET-BODY' }, approximate: false, nights_used: 1, nights_source: 'x' }) }
      return res(404, {})
    })
    vi.stubGlobal('fetch', fetchMock)
    await setUpCity('seoul')
    store.chosenHotel = PLACES.seoul.hotels[0].id
    const pending = runOptimise()           // asked while Seoul is selected, answer is still on its way
    await selectCity('tokyo')               // the user switches city
    release()                               // the old answer (a Seoul plan) arrives
    await pending
    expect(store.plan).toBeNull()
    expect(store.planError).toBeNull()
    expect(store.cityId).toBe('tokyo')
    expect(warn).toHaveBeenCalledTimes(1)   // the late Seoul plan was caught by the city check, not silently applied
    expect(JSON.stringify(warn.mock.calls[0])).not.toContain('SECRET-BODY')
    // a response from the old city that was NOT aborted must be caught by the client even when the request itself was not aborted:
    const direct = await import('../../src/api/routes.js')
    const lateFetch = vi.fn(async () => res(200, { city_id: 'seoul', result: {}, secret: 'SECRET-BODY' }))
    vi.stubGlobal('fetch', lateFetch)
    await expect(direct.optimise({ days: 1 }, 'h', { cityId: 'tokyo' })).rejects.toMatchObject({ code: 'aborted' })
    expect(warn).toHaveBeenCalledTimes(2)
    const logged = JSON.stringify(warn.mock.calls[1])
    expect(logged).toContain('seoul')
    expect(logged).not.toContain('SECRET-BODY')
  })

  it('refuses to build a request without a city', async () => {
    const direct = await import('../../src/api/routes.js')
    expect(() => direct.optimise({}, 'h', {})).toThrow('city_id is required')
    expect(() => direct.getPlaces()).toThrow('city_id is required')
  })
})

describe('hotel names', () => {
  it('removes "(fictional)" from every name and sentence and touches nothing else', () => {
    expect(cleanHotelText('Jongno Garden Hotel (fictional)')).toBe('Jongno Garden Hotel')
    expect(cleanHotelText('A (fictional) costs more than B (Fictional).')).toBe('A costs more than B.')
    expect(cleanHotelText('Hotel 한옥 스테이 (fictional)')).toBe('Hotel 한옥 스테이')
    expect(cleanHotelText(undefined)).toBeUndefined()
  })
  it('loadPlaces shows clean names while the fixture data keeps the provenance suffix', async () => {
    vi.stubGlobal('fetch', recordingFetch([]))
    await setUpCity('seoul')
    expect(seoul.hotels.every((h) => h.name.includes('(fictional)'))).toBe(true)
    expect(Object.values(store.hotelsById).every((h) => !h.name.includes('fictional'))).toBe(true)
  })
})
