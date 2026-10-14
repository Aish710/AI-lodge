import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { addOp, buildReplanArgs, describeOp, diffRows, DAY_PARTS, MAX_OPS, mustVisitRemovals, proposalToOps, removeOpAt, trueCostCaveat } from '../../src/lib/replan.js'
import { applyQueue, chooseHotel, queueOp, queueProposal, resetAll, restorePrevious, store, unqueue } from '../../src/store.js'
import { errBody, res } from './helpers.js'
import applied from '../fixtures/replan-applied.json'
import feasible from '../fixtures/optimise-feasible.json'
import places from '../fixtures/places.json'

const snap = (x) => JSON.parse(JSON.stringify(x))
const byId = Object.fromEntries(places.attractions.map((p) => [p.id, p]))
const hotels = Object.fromEntries(places.hotels.map((h) => [h.id, h]))
const prefs = { days: 3, budget: null, strict_budget: false, pace: 'balanced', interests: [], must_visit: ['senso_ji', 'meiji_jingu'], skip: ['akihabara'], day_start: '09:00', day_end: '19:00',
  value_of_time_per_hour: 1000, max_walking_minutes_per_day: 90, start_weekday: 2, allow_unknown_hours: false, nights: null, locked: [] }

describe('pending-changes queue', () => {
  it('queues, removes, and replaces a contradictory older operation with the newer one', () => {
    let q = []
    q = addOp(q, { op: 'lock', attraction_id: 'senso_ji', day: 1, start_time: '10:00' }).queue
    q = addOp(q, { op: 'move', attraction_id: 'senso_ji', day: 2, start_time: '09:30' }).queue
    expect(q).toEqual([{ op: 'move', attraction_id: 'senso_ji', day: 2, start_time: '09:30' }]) // one slot per sight, newest wins
    q = addOp(q, { op: 'remove', attraction_id: 'senso_ji' }).queue
    expect(q.map((o) => o.op)).toEqual(['remove']) // lock/move and remove cannot coexist (the server would reject the pair)
    q = addOp(q, { op: 'remove', attraction_id: 'tokyo_tower' }).queue
    expect(q).toHaveLength(2)
    expect(removeOpAt(q, 0).map((o) => o.attraction_id)).toEqual(['tokyo_tower'])
  })
  it('allows only one budget change and one hotel switch', () => {
    let q = addOp([], { op: 'change_budget', budget: 1000, strict: false }).queue
    q = addOp(q, { op: 'change_budget', budget: 2000, strict: true }).queue
    q = addOp(q, { op: 'switch_hotel', hotel_id: 'a' }).queue
    q = addOp(q, { op: 'switch_hotel', hotel_id: 'b' }).queue
    expect(q).toEqual([{ op: 'change_budget', budget: 2000, strict: true }, { op: 'switch_hotel', hotel_id: 'b' }])
  })
  it('caps the queue at 20 operations and leaves it unchanged with a plain message', () => {
    let q = []
    for (let i = 0; i < MAX_OPS; i++) q = addOp(q, { op: 'remove', attraction_id: `x${i}` }).queue
    expect(q).toHaveLength(20)
    const over = addOp(q, { op: 'remove', attraction_id: 'x20' })
    expect(over.queue).toBe(q)
    expect(over.error).toMatch(/at most 20/)
    expect(addOp(q, { op: 'remove', attraction_id: 'x0' }).queue).toHaveLength(20) // replacing an existing one is still allowed
  })
  it('describes each operation in plain language, with names and a labelled budget', () => {
    expect(describeOp({ op: 'lock', attraction_id: 'senso_ji', day: 1, start_time: '10:00' }, byId, hotels)).toBe('Lock Senso-ji on day 1 at 10:00')
    expect(describeOp({ op: 'move', attraction_id: 'senso_ji', day: 2, start_time: '14:00' }, byId, hotels)).toBe('Move Senso-ji to day 2 at 14:00')
    expect(describeOp({ op: 'remove', attraction_id: 'senso_ji' }, byId, hotels)).toBe('Remove Senso-ji')
    expect(describeOp({ op: 'change_budget', budget: 15000, strict: true }, byId, hotels)).toBe('Set the budget to ¥15,000 (strict limit)')
    expect(describeOp({ op: 'switch_hotel', hotel_id: 'hotel_lantern_asakusa' }, byId, hotels)).toContain(hotels.hotel_lantern_asakusa.name)
  })
  it('uses the same day-part mapping as the API', () => {
    expect(DAY_PARTS).toEqual({ morning: '09:30', midday: '12:00', afternoon: '14:00', evening: '17:30' })
  })
})

describe('must-visit confirmation flag (decision 6), asserted at the request-building layer', () => {
  const rm = [{ op: 'remove', attraction_id: 'senso_ji' }]
  const base = { prefs, currentResult: feasible.result, queue: rm }
  it('defaults to false', () => {
    expect(buildReplanArgs(base).options.confirmRemoveMustVisit).toBe(false)
  })
  it('is true only after explicit confirmation from the UI for a queue that really removes a must-visit', () => {
    expect(buildReplanArgs({ ...base, confirmed: true }).options.confirmRemoveMustVisit).toBe(true)
    expect(buildReplanArgs({ ...base, confirmed: 'true' }).options.confirmRemoveMustVisit).toBe(false)
    expect(buildReplanArgs({ ...base, confirmed: 1 }).options.confirmRemoveMustVisit).toBe(false)
    expect(buildReplanArgs({ ...base, confirmed: true, source: 'nl' }).options.confirmRemoveMustVisit).toBe(false) // never from the natural-language path
    expect(buildReplanArgs({ ...base, queue: [{ op: 'remove', attraction_id: 'tokyo_tower' }], confirmed: true }).options.confirmRemoveMustVisit).toBe(false) // not needed: not a must-visit
  })
  it('finds the must-visits a queue would remove', () => {
    expect(mustVisitRemovals([...rm, { op: 'remove', attraction_id: 'tokyo_tower' }, { op: 'lock', attraction_id: 'meiji_jingu', day: 1, start_time: '10:00' }], prefs)).toEqual(['senso_ji'])
  })
  it('a natural-language proposal carries operations only: it cannot confirm anything', () => {
    const proposal = { status: 'ok', requires_confirmation: true, confirmation_reasons: ['x'], operations: [{ op: 'remove', attraction_id: 'senso_ji' }, { op: 'remove', attraction_id: 'tokyo_tower' }], descriptions: ['a', 'b'] }
    expect(proposalToOps(proposal)).toEqual(proposal.operations)
    expect(proposalToOps(proposal, [1])).toEqual([{ op: 'remove', attraction_id: 'tokyo_tower' }])
    expect(JSON.stringify(proposalToOps(proposal))).not.toMatch(/confirm/)
  })
})

describe('diff view model', () => {
  it('gives direction, glyph and a word for every line (never colour alone)', () => {
    const rows = diffRows(applied.diff)
    expect(rows.map((r) => r.key)).toEqual(['admissions_jpy', 'transport_jpy', 'rooms_jpy', 'time_cost_jpy', 'missed_penalty_jpy', 'true_cost_jpy', 'travel_minutes'])
    const tc = rows.find((r) => r.key === 'true_cost_jpy')
    expect([tc.before, tc.after, tc.delta, tc.direction, tc.glyph, tc.word]).toEqual([40177, 39510, -667, 'down', '▼', 'decrease'])
    expect(rows.find((r) => r.key === 'rooms_jpy')).toMatchObject({ direction: 'same', glyph: '=', word: 'no change' })
  })
  it('attaches the not-like-for-like warning to a saving', () => {
    const c = trueCostCaveat(applied.diff)
    expect(c.show).toBe(true)
    expect(c.isSaving).toBe(true)
    expect(c.warning).toMatch(/^Not like-for-like/)
    expect(trueCostCaveat({ ...applied.diff, warnings: ['Some other warning'] }).show).toBe(false)
  })
})

describe('replan flows through the store', () => {
  let fetchMock
  const stub = (impl) => { fetchMock = vi.fn(impl); vi.stubGlobal('fetch', fetchMock) }
  const bodyOf = (call) => JSON.parse(call[1].body)
  beforeEach(() => {
    resetAll()
    store.plan = structuredClone(feasible)
    store.planPrefs = structuredClone(prefs)
    store.chosenHotel = 'hotel_lantern_asakusa'
    store.hotelIds = ['hotel_lantern_asakusa', 'hotel_kitsune_shinjuku']
    store.places = places.attractions
    store.placesById = byId
  })
  afterEach(() => vi.unstubAllGlobals())

  it('sends the schedule exactly as received, all queued operations in one call, and the flag false by default', async () => {
    const before = snap(store.plan.result)
    stub(async () => res(200, applied))
    queueOp({ op: 'remove', attraction_id: 'teamlab_planets' })
    queueOp({ op: 'lock', attraction_id: 'tokyo_skytree', day: 1, start_time: '10:00' })
    await applyQueue()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const sent = bodyOf(fetchMock.mock.calls[0])
    expect(sent.current_result).toEqual(before)
    expect(sent.operations).toHaveLength(2)
    expect(sent.confirm_remove_must_visit).toBe(false)
    expect(sent.preferences).toEqual(prefs)
    expect(store.queue).toEqual([])
    expect(store.plan.result).toEqual(applied.schedule) // the server's schedule is shown as received
  })

  it('a must-visit removal reaches the server flag-less unless the dialog confirmed; with confirmation it is true', async () => {
    stub(async () => res(200, applied))
    queueOp({ op: 'remove', attraction_id: 'senso_ji' })
    await applyQueue({ confirmed: false })
    expect(bodyOf(fetchMock.mock.calls[0]).confirm_remove_must_visit).toBe(false)
    queueOp({ op: 'remove', attraction_id: 'senso_ji' })
    await applyQueue({ confirmed: true })
    expect(bodyOf(fetchMock.mock.calls[1]).confirm_remove_must_visit).toBe(true)
  })

  it('queueing a natural-language proposal never sets the flag and never calls the server', async () => {
    stub(async () => res(200, {}))
    store.proposal = { status: 'ok', requires_confirmation: true, operations: [{ op: 'remove', attraction_id: 'senso_ji' }], descriptions: ['remove Senso-ji'] }
    queueProposal([0])
    expect(fetchMock).not.toHaveBeenCalled()
    expect(store.queue).toEqual([{ op: 'remove', attraction_id: 'senso_ji' }])
    expect(store.proposal).toBeNull()
    stub(async () => res(200, applied))
    await applyQueue({ confirmed: false })
    expect(bodyOf(fetchMock.mock.calls[0]).confirm_remove_must_visit).toBe(false)
  })

  it('"restore previous plan" is a swap of two server results and mutates neither', async () => {
    const original = snap(store.plan)
    const fixtureCopy = structuredClone(applied)
    stub(async () => res(200, applied))
    queueOp({ op: 'remove', attraction_id: 'teamlab_planets' })
    await applyQueue()
    expect(store.plan.result).toEqual(applied.schedule)
    expect(store.previous).not.toBeNull()
    restorePrevious()
    expect(store.plan).toEqual(original)
    expect(store.previous).toBeNull()
    expect(store.restored).toBe(true)
    expect(applied).toEqual(fixtureCopy)
    expect(fetchMock).toHaveBeenCalledTimes(1) // nothing was sent to restore
  })

  it('an infeasible or rejected replan keeps the original plan, shows the result, and keeps the queue', async () => {
    const original = snap(store.plan)
    stub(async () => res(200, { ...applied, status: 'infeasible', schedule: original.result, schedule_changed: false, diff: null, conflicts: [{ code: 'x', message: 'No schedule fits.', attraction_ids: [] }], summary: 'Replan infeasible.' }))
    queueOp({ op: 'move', attraction_id: 'senso_ji', day: 1, start_time: '09:00' })
    await applyQueue()
    expect(store.plan).toEqual(original)
    expect(store.lastReplan.status).toBe('infeasible')
    expect(store.previous).toBeNull()
    expect(store.queue).toHaveLength(1)
  })

  it('handles a 422 (for example a tampered schedule) generically and leaves the plan alone', async () => {
    const original = snap(store.plan)
    stub(async () => res(422, errBody('invalid_schedule', 'The schedule does not match the dataset.', { findings: ['x'] })))
    queueOp({ op: 'remove', attraction_id: 'teamlab_planets' })
    await applyQueue()
    expect(store.replanError).toMatchObject({ code: 'invalid_schedule', status: 422 })
    expect(store.plan).toEqual(original)
    expect(store.queue).toHaveLength(1)
  })

  it('unqueue removes one queued operation; switching hotel to a new one invalidates a replanned plan', () => {
    queueOp({ op: 'remove', attraction_id: 'a' }); queueOp({ op: 'remove', attraction_id: 'b' })
    unqueue(0)
    expect(store.queue.map((o) => o.attraction_id)).toEqual(['b'])
    store.planFromReplan = true
    chooseHotel('hotel_lantern_asakusa')
    expect(store.planFromReplan).toBe(true)
    chooseHotel('hotel_kitsune_shinjuku')
    expect(store.planFromReplan).toBe(false)
  })
})
