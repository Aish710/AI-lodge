import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { buildScenario, diffPlans, draftFrom } from '../../src/lib/whatif.js'
import { applyWhatIf, discardWhatIf, openWhatIf, resetAll, restoreState, runWhatIf, saveWhatIf, store } from '../../src/store.js'
import { res } from './helpers.js'
import feasibleOld from '../fixtures/optimise-feasible.json'
// the stored fixture predates the validator's verified/provisional label; a current server always returns it
const feasible = { ...feasibleOld, feasibility_report: { ...feasibleOld.feasibility_report, verification: 'verified' } }

const base = { days: 3, budget: null, strict_budget: false, pace: 'balanced', interests: [], must_visit: ['a', 'b'], skip: ['z'], day_start: '09:00', day_end: '19:00', value_of_time_per_hour: 1000,
  max_walking_minutes_per_day: 90, start_weekday: 2, allow_unknown_hours: false, nights: null, locked: [{ attraction_id: 'a', day: 1, start_time: '10:00' }] }

describe('what-if scenario building', () => {
  it('an untouched draft changes nothing', () => {
    const s = buildScenario(base, 'h1', draftFrom(base, 'h1'))
    expect(s.changes).toEqual([]); expect(s.prefs).toEqual(base); expect(s.errors).toEqual([])
  })
  it('names exactly what differs and never touches the original', () => {
    const before = JSON.stringify(base)
    const d = { ...draftFrom(base, 'h1'), days: 2, dayEnd: '17:00', maxActivities: '2', maxDailyTravel: '120', budget: 5000, strict: true }
    const s = buildScenario(base, 'h1', d)
    expect(s.prefs).toMatchObject({ days: 2, day_end: '17:00', max_activities_per_day: 2, max_daily_travel_minutes: 120, budget: 5000, strict_budget: true })
    expect(s.changes.length).toBe(5); expect(JSON.stringify(base)).toBe(before)
  })
  it('leaving a sight out also drops its lock and must-visit flag, adding a must-visit un-skips it, and a hotel change is a change', () => {
    const d = { ...draftFrom(base, 'h1'), exclude: ['a'], addMust: ['z'], hotel: 'h2' }
    const s = buildScenario(base, 'h1', d)
    expect(s.prefs.must_visit).toEqual(['b', 'z']); expect(s.prefs.locked).toEqual([]); expect(s.prefs.skip).toContain('a'); expect(s.prefs.skip).not.toContain('z'); expect(s.hotel).toBe('h2')
  })
  it('rejects values the planner cannot enforce, with sentences', () => {
    for (const bad of [{ days: 9 }, { dayEnd: '08:00' }, { maxActivities: '12' }, { maxDailyTravel: '5' }, { budget: -3 }, { vot: -1 }]) expect(buildScenario(base, 'h1', { ...draftFrom(base, 'h1'), ...bad }).errors.length).toBe(1)
  })
  it('the difference is plain subtraction of server numbers and says when sights differ', () => {
    const mk = (stops, cash, trav) => ({ result: { days: [{ day: 1, stops: stops.map((id) => ({ attraction_id: id, start: '10:00' })) }] }, cost_summary: { trip: { cash_total_with_rooms: cash, travel_minutes: trav } } })
    const same = diffPlans(mk(['a', 'b'], 1000, 100), mk(['b', 'a'], 900, 80))
    expect(same).toMatchObject({ money: -100, minutes: -20, sameSights: true, note: null })
    const diff = diffPlans(mk(['a', 'b'], 1000, 100), mk(['a'], 600, 40))
    expect(diff).toMatchObject({ removed: ['b'], added: [], sameSights: false, sights: -1 }); expect(diff.note).toMatch(/not a like-for-like saving/)
  })
})

describe('what-if store behaviour', () => {
  beforeEach(() => { resetAll(); store.cityId = 'tokyo'; store.chosenHotel = 'h1'; store.hotelsById = { h1: { id: 'h1', name: 'One' }, h2: { id: 'h2', name: 'Two' } }
    store.plan = feasible; store.planPrefs = { ...base, locked: [] } })
  afterEach(() => vi.unstubAllGlobals())
  it('a preview never changes the current plan; discard keeps it', async () => {
    const f = vi.fn(async () => res(200, { ...feasible, marker: 'preview' })); vi.stubGlobal('fetch', f)
    openWhatIf(); store.whatif.draft.days = 2
    const planBefore = store.plan, prefsBefore = JSON.stringify(store.planPrefs)
    await runWhatIf()
    expect(store.whatif.result.marker).toBe('preview'); expect(store.plan).toBe(planBefore); expect(JSON.stringify(store.planPrefs)).toBe(prefsBefore)
    discardWhatIf()
    expect(store.plan).toBe(planBefore); expect(store.whatif.result).toBeNull()
  })
  it('apply commits it, keeps the old plan in history and restoring it works', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, { ...feasible, marker: 'applied' })))
    const old = store.plan
    openWhatIf(); store.whatif.draft.maxActivities = '2'
    await runWhatIf(); applyWhatIf()
    expect(store.plan.marker).toBe('applied'); expect(store.planPrefs.max_activities_per_day).toBe(2); expect(store.whatif.draft).toBeNull()
    store.history = [{ id: 99, label: 'Planned', hotel: 'h1', plan: old, prefs: { ...base, locked: [] }, fromReplan: false }, ...store.history]
    expect(restoreState(99)).toBe(true); expect(store.plan).toBe(old)
  })
  it('save keeps a labelled alternative without changing the current plan', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, { ...feasible, marker: 'saved' })))
    const cur = store.plan
    openWhatIf(); store.whatif.draft.pace = 'relaxed'
    await runWhatIf(); saveWhatIf()
    expect(store.plan).toBe(cur); expect(store.history[0]).toMatchObject({ label: 'Saved what-if', kind: 'saved' })
  })
  it('an infeasible scenario cannot be applied and leaves the plan alone', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, { result: { status: 'infeasible', conflicts: [{ code: 'x', message: 'no' }], days: [] } })))
    const cur = store.plan
    openWhatIf(); store.whatif.draft.days = 1
    await runWhatIf(); applyWhatIf()
    expect(store.plan).toBe(cur)
  })
  it('a stale answer is dropped when the panel was closed or a newer preview was started', async () => {
    let release
    vi.stubGlobal('fetch', vi.fn(() => new Promise((r) => { release = () => r(res(200, { ...feasible, marker: 'late' })) })))
    openWhatIf(); store.whatif.draft.days = 2
    const p = runWhatIf()
    discardWhatIf(); release(); await p
    expect(store.whatif.result).toBeNull()
  })
  it('an unchanged draft or an invalid one never reaches the network', async () => {
    const f = vi.fn(); vi.stubGlobal('fetch', f)
    openWhatIf(); await runWhatIf(); expect(f).not.toHaveBeenCalled(); expect(store.whatif.error.message).toMatch(/at least one/)
    store.whatif.draft.days = 99; await runWhatIf(); expect(f).not.toHaveBeenCalled()
  })
})


describe('what-if validation is never assumed', () => {
  it('a result without the validator\'s verdict or label is "not checked", cannot be applied, and says why', async () => {
    const { validationOf } = await import('../../src/lib/whatif.js')
    const missing = { result: { status: 'feasible' }, feasibility_report: undefined }
    const noLabel = { result: { status: 'feasible' }, feasibility_report: { overall: 'pass' } }
    for (const r of [missing, noLabel]) { const v = validationOf(r); expect(v.applicable).toBe(false); expect(v.kind).toBe('unknown'); expect(v.text).toMatch(/Not checked/) }
    expect(validationOf({ result: { status: 'feasible' }, feasibility_report: { overall: 'pass', verification: 'verified' } })).toMatchObject({ kind: 'good', applicable: true })
    expect(validationOf({ result: { status: 'feasible' }, feasibility_report: { overall: 'pass_with_warnings', verification: 'conditional' } })).toMatchObject({ kind: 'warn', applicable: true })
    expect(validationOf({ result: { status: 'feasible' }, feasibility_report: { overall: 'fail', verification: 'none' } }).applicable).toBe(false)
    expect(validationOf({ result: { status: 'infeasible' } }).applicable).toBe(false)
  })
  it('applyWhatIf refuses an unchecked preview and leaves the plan alone', async () => {
    resetAll(); store.cityId = 'tokyo'; store.chosenHotel = 'h1'; store.hotelsById = { h1: { id: 'h1', name: 'One' } }; store.plan = feasible; store.planPrefs = { ...base, locked: [] }
    vi.stubGlobal('fetch', vi.fn(async () => res(200, { ...feasibleOld, marker: 'unchecked' })))
    openWhatIf(); store.whatif.draft.days = 2
    await runWhatIf(); const cur = store.plan; applyWhatIf()
    expect(store.plan).toBe(cur); vi.unstubAllGlobals()
  })
  it('different coverage is not comparable and lower spending from fewer sights is called that', async () => {
    const { diffPlans } = await import('../../src/lib/whatif.js')
    const mk = (stops, cash) => ({ result: { days: [{ day: 1, stops: stops.map((id) => ({ attraction_id: id, start: '10:00' })) }] }, cost_summary: { trip: { cash_total_with_rooms: cash, travel_minutes: 60 } } })
    const less = diffPlans(mk(['a', 'b'], 1000), mk(['a'], 600))
    expect(less.comparable).toBe(false); expect(less.lowerBecauseLess).toBe(true)
    const same = diffPlans(mk(['a', 'b'], 1000), mk(['b', 'a'], 900))
    expect(same.comparable).toBe(true); expect(same.lowerBecauseLess).toBe(false)
    expect(diffPlans(mk(['a'], 1), mk([], 0)).empty).toBe(true)
  })
})
