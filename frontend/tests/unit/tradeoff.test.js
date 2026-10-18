import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { entryRows, pushState, votOptions, whyHotel } from '../../src/lib/tradeoff.js'
import { adoptAlternative, adoptExplorerPlan, explorerPrefs, resetAll, restoreState, runAlternatives, runExplorer, runOptimise, store } from '../../src/store.js'
import { res } from './helpers.js'
import feasible from '../fixtures/optimise-feasible.json'

const E = (key, hotel, over = {}) => ({ key, label: key, rule: '', hotel_id: hotel, hotel_name: hotel, area: 'a', feasible: true, status: 'OPTIMAL', accommodation_jpy: 100, admissions_jpy: 10,
  transport_jpy: 5, known_spend_jpy: 115, travel_minutes: 60, travel_time_value_jpy: 20, omitted_optional: [], omitted_charge_jpy: 0, unknown_price_items: [], objective_estimate_for_unknown_jpy: 0,
  score_jpy: 135, same_hotel_as: [], ...over })
const money = (v) => String(Math.round(v)), mins = (m) => `${m} min`

describe('explorer helpers', () => {
  it('value-of-time options are multiples of the city default, including an extreme and a small one', () => {
    expect(votOptions(18).map((o) => o.value)).toEqual([9, 18, 36, 72])
    expect(votOptions(undefined)[1].value).toBe(1000)
  })
  it('says plainly when all three rules agree', () => {
    const b = { entries: [E('cheapest_rate', 'h1'), E('convenience_first', 'h1'), E('joint', 'h1')] }
    const w = whyHotel(b, money, mins)
    expect(w.change).toBe(false)
    expect(w.lines[0]).toMatch(/no trade-off/)
  })
  it('explains a joint choice that differs from both baselines, without inventing numbers', () => {
    const b = { entries: [E('cheapest_rate', 'h1'), E('convenience_first', 'h2'), E('joint', 'h3', { score_jpy: 120 })] }
    const w = whyHotel(b, money, mins)
    expect(w.change).toBe(true)
    expect(w.lines[0]).toMatch(/neither the cheapest nor the most convenient/)
  })
  it('rows keep money components separate from the score', () => {
    const [r] = entryRows({ entries: [E('joint', 'h1')] })
    expect(r.spend).toBe(r.rooms + r.admissions + r.transport)
    expect(r.score).toBe(r.spend + r.timeValue + r.charge)
  })
  it('history keeps the newest states and never duplicates an id', () => {
    let l = []
    for (let i = 1; i <= 10; i++) l = pushState(l, { id: i }, 8)
    expect(l.length).toBe(8)
    expect(l[0].id).toBe(10)
    expect(pushState(l, { id: 10 }).filter((s) => s.id === 10).length).toBe(1)
  })
})

describe('explorer store actions', () => {
  beforeEach(() => { resetAll(); store.cityId = 'tokyo'; store.hotelsById = { h1: { id: 'h1', name: 'One' }, h2: { id: 'h2', name: 'Two' } }; store.hotelIds = ['h1', 'h2'] })
  afterEach(() => vi.unstubAllGlobals())
  const comp = (best) => ({ best_by_true_cost: best, results: [{ hotel_id: 'h1', feasible: true }, { hotel_id: 'h2', feasible: true }],
    baselines: { entries: [E('cheapest_rate', 'h1'), E('convenience_first', 'h2'), E('joint', best)] } })

  it('reruns the real compare with locks and explicit preferences kept, changing only the value of time', async () => {
    store.planPrefs = { days: 2, pace: 'relaxed', must_visit: ['x'], locked: [{ attraction_id: 'x', day: 1, start_time: '10:00' }], max_activities_per_day: 2, value_of_time_per_hour: 1000 }
    const f = vi.fn(async () => res(200, comp('h2')))
    vi.stubGlobal('fetch', f)
    await runExplorer(4000)
    const body = JSON.parse(f.mock.calls[0][1].body)
    expect(body.preferences).toEqual({ ...store.planPrefs, value_of_time_per_hour: 4000 })
    expect(body.hotel_ids).toEqual(['h1', 'h2'])
    expect(store.explorer.runs[0].best).toBe('h2')
    expect(explorerPrefs(5).locked.length).toBe(1)
  })
  it('records each valid plan and restores any earlier one without a request', async () => {
    store.hotelsById = { h1: { id: 'h1', name: 'One' } }
    store.form.days = 2
    vi.stubGlobal('fetch', vi.fn(async () => res(200, feasible)))
    await runOptimise('h1')
    store.form.valueOfTime = 2000
    await runOptimise('h1')
    expect(store.history.length).toBe(2)
    const older = store.history[1]
    const f = vi.fn(); vi.stubGlobal('fetch', f)
    expect(restoreState(older.id)).toBe(true)
    expect(store.planPrefs.value_of_time_per_hour).toBe(older.vot)
    expect(f).not.toHaveBeenCalled()
  })
  it('adopting with "keep my hotel" optimises the chosen hotel, not the winner, and keeps the locks', async () => {
    store.chosenHotel = 'h1'
    store.planPrefs = { days: 2, locked: [{ attraction_id: 'x', day: 1, start_time: '10:00' }], value_of_time_per_hour: 1000 }
    store.plan = feasible
    store.explorer.vot = 3000; store.explorer.keepHotel = true; store.explorer.last = comp('h2')
    const f = vi.fn(async () => res(200, feasible)); vi.stubGlobal('fetch', f)
    await adoptExplorerPlan('h2')
    const body = JSON.parse(f.mock.calls[0][1].body)
    expect(body.hotel_id).toBe('h1')
    expect(body.preferences.locked.length).toBe(1)
    expect(body.preferences.value_of_time_per_hour).toBe(3000)
    expect(store.planFromReplan).toBe(true)
    expect(store.form.valueOfTime).toBe(3000)
  })
})

describe('alternatives', () => {
  beforeEach(() => { resetAll(); store.cityId = 'tokyo'; store.chosenHotel = 'h1'; store.hotelsById = { h1: { id: 'h1', name: 'One' }, h2: { id: 'h2', name: 'Two' } }
    store.planPrefs = { days: 2, must_visit: [], skip: [], locked: [], value_of_time_per_hour: 1000 } })
  afterEach(() => vi.unstubAllGlobals())
  it('asks the server with the current plan preferences and stores exactly what comes back', async () => {
    const body = { alternatives: [{ key: 'lowest_money', roles: ['Lowest spending'], hotel_id: 'h2', generated_at_value_of_time: 8000, factor: 8, money: 1, minutes: 2, coverage: 0, score_at_your_value_of_time: 3, fingerprint: 'f' }], method: 'm' }
    const f = vi.fn(async () => res(200, body)); vi.stubGlobal('fetch', f)
    await runAlternatives()
    expect(JSON.parse(f.mock.calls[0][1].body).preferences).toEqual(store.planPrefs)
    expect(store.explorer.alts.alternatives[0].key).toBe('lowest_money')
  })
  it('using one runs the real optimiser at the value of time that generated it, leaves the form setting alone and keeps history', async () => {
    store.plan = feasible; store.form.valueOfTime = 1000
    const f = vi.fn(async () => res(200, feasible)); vi.stubGlobal('fetch', f)
    await adoptAlternative({ hotel_id: 'h2', generated_at_value_of_time: 8000, roles: ['Lowest spending'] })
    const b = JSON.parse(f.mock.calls[0][1].body)
    expect(b.hotel_id).toBe('h2'); expect(b.preferences.value_of_time_per_hour).toBe(8000)
    expect(store.form.valueOfTime).toBe(1000); expect(store.history.length).toBe(1); expect(store.chosenHotel).toBe('h2')
  })
})
