import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { addStop, armRows, moveToDay, moveWithin, problems, removeStop, seedDays } from '../../src/lib/itinerary.js'
import { adoptItineraryArm, resetAll, runItineraryCompare, startItinerary, store } from '../../src/store.js'
import { res } from './helpers.js'
import feasible from '../fixtures/optimise-feasible.json'

describe('itinerary editing helpers', () => {
  it('seeds every sight exactly once over the trip days, in the order given', () => {
    const d = seedDays(['a', 'b', 'c', 'd', 'e'], 2)
    expect(d.flat()).toEqual(['a', 'b', 'c', 'd', 'e']); expect(d.length).toBe(2)
  })
  it('moves within a day, between days, and never past the ends', () => {
    const d = [['a', 'b'], ['c']]
    expect(moveWithin(d, 0, 0, 1)[0]).toEqual(['b', 'a'])
    expect(moveWithin(d, 0, 0, -1)).toBe(d)
    expect(moveToDay(d, 0, 0, 1)).toEqual([['b'], ['c', 'a']])
    expect(d).toEqual([['a', 'b'], ['c']])                          // inputs are never mutated
  })
  it('never removes a must-visit and never adds a duplicate', () => {
    const d = [['a', 'b']]
    expect(removeStop(d, 0, 0, ['a'])).toBe(d)
    expect(removeStop(d, 0, 1, ['a'])).toEqual([['a']])
    expect(addStop(d, 0, 'a')).toBe(d)
    expect(addStop(d, 0, 'z')).toEqual([['a', 'b', 'z']])
  })
  it('explains in a sentence what is missing instead of sending a bad request', () => {
    expect(problems([[]], [])).toEqual(['Add at least one attraction to your itinerary.'])
    expect(problems([['a']], ['b']).length).toBe(1)
    expect(problems([['a']], ['a'])).toEqual([])
  })
  it('shows the arms as returned, keeping spending and score apart', () => {
    const r = armRows({ arms: [{ key: 'yours', label: 'Your itinerary', feasible: true, conflicts: [], failed_checks: [], sights: ['a', 'b'], omitted: [], travel_minutes: 90, breakdown: { admissions_jpy: 500, transport_jpy: 300 }, score_jpy: 9999 },
      { key: 'x', label: 'X', feasible: false, conflicts: ['Closed on day 1.'], failed_checks: [] }] })
    expect(r[0]).toMatchObject({ spend: 800, score: 9999, minutes: 90, sights: 2 })
    expect(r[1].why).toBe('Closed on day 1.'); expect(r[1].spend).toBeNull()
  })
})

describe('itinerary store actions', () => {
  beforeEach(() => { resetAll(); store.cityId = 'tokyo'; store.chosenHotel = 'h1'; store.plan = feasible; store.planPrefs = { days: 2, must_visit: ['a'], skip: [], locked: [], value_of_time_per_hour: 1000 }
    store.placesById = { a: { id: 'a' }, b: { id: 'b' }, c: { id: 'c' } }; store.wishlist = { a: 'must', b: 'nice' } })
  afterEach(() => vi.unstubAllGlobals())
  it('starts from the chosen sights, skips none of them, and sends the user days to the server', async () => {
    startItinerary()
    expect(store.itin.days.flat().sort()).toEqual(['a', 'b'])
    const f = vi.fn(async () => res(200, { arms: [], verdict: { kind: 'tie', text: 't' }, target_sights: ['a', 'b'] })); vi.stubGlobal('fetch', f)
    await runItineraryCompare()
    const body = JSON.parse(f.mock.calls[0][1].body)
    expect(body.days.flat().sort()).toEqual(['a', 'b']); expect(body.hotel_id).toBe('h1'); expect(body.preferences).toEqual(store.planPrefs)
    expect(store.itin.result.verdict.kind).toBe('tie')
  })
  it('adopting the same-sights plan requires exactly those sights and keeps the previous plan in history', async () => {
    store.itin.result = { target_sights: ['a', 'b'] }
    const f = vi.fn(async () => res(200, feasible)); vi.stubGlobal('fetch', f)
    await adoptItineraryArm('same')
    const body = JSON.parse(f.mock.calls[0][1].body)
    expect(body.preferences.must_visit).toEqual(['a', 'b']); expect(body.preferences.skip).toEqual(['c'])
    expect(store.history.length).toBe(1)
  })
  it('adopting the full plan keeps the user must-visit flags only', async () => {
    store.itin.result = { target_sights: ['a', 'b'] }
    const f = vi.fn(async () => res(200, feasible)); vi.stubGlobal('fetch', f)
    await adoptItineraryArm('full')
    expect(JSON.parse(f.mock.calls[0][1].body).preferences.must_visit).toEqual(['a'])
  })
})

import { moveAnnouncement, moveStop } from '../../src/lib/itinerary.js'
describe('drag-and-drop moves', () => {
  const d = [['a', 'b', 'c'], ['x'], []]
  it('moves within a day with the insertion slot semantics and never mutates', () => {
    expect(moveStop(d, { day: 0, index: 0 }, { day: 0, index: 3 })[0]).toEqual(['b', 'c', 'a'])
    expect(moveStop(d, { day: 0, index: 2 }, { day: 0, index: 0 })[0]).toEqual(['c', 'a', 'b'])
    expect(moveStop(d, { day: 0, index: 1 }, { day: 0, index: 1 })).toBe(d)            // dropped where it already is
    expect(moveStop(d, { day: 0, index: 1 }, { day: 0, index: 2 })).toBe(d)            // the slot right after itself is the same place
    expect(d).toEqual([['a', 'b', 'c'], ['x'], []])
  })
  it('moves across days, onto an empty day, and refuses a full day', () => {
    expect(moveStop(d, { day: 0, index: 1 }, { day: 2, index: 0 })).toEqual([['a', 'c'], ['x'], ['b']])
    expect(moveStop(d, { day: 1, index: 0 }, { day: 0, index: 1 })).toEqual([['a', 'x', 'b', 'c'], [], []])
    const full = [['a'], Array.from({ length: 8 }, (_, i) => 's' + i)]
    expect(moveStop(full, { day: 0, index: 0 }, { day: 1, index: 0 })).toBe(full)
  })
  it('ignores impossible requests and announces the result in words', () => {
    expect(moveStop(d, { day: 5, index: 0 }, { day: 0, index: 0 })).toBe(d)
    expect(moveStop(d, { day: 0, index: 9 }, { day: 0, index: 0 })).toBe(d)
    expect(moveAnnouncement('Alpha', [['x'], ['b', 'a']], 'a')).toBe('Alpha is now day 2, position 2 of 2.')
  })
})
