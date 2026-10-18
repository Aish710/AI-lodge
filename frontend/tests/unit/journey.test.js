// Journey components: empty-day help (evidence only, three honest options), undo bar, and copilot proposal handling (whitelisted keys, preview only).
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyDayHelp from '../../src/components/EmptyDayHelp.vue'
import UndoBar from '../../src/components/UndoBar.vue'
import { previewProposal, resetAll, store } from '../../src/store.js'
import feasible from '../fixtures/optimise-feasible.json'

const stop = (id) => ({ attraction_id: id, start: '09:00', end: '10:00', travel_minutes_from_previous: 5, transport_jpy_from_previous: 0, cost: 0, cost_status: 'known', is_must_visit: false, uncertainty_flags: [] })
function withPlan(stopsPerDay) {
  const plan = JSON.parse(JSON.stringify(feasible))
  plan.result.days = stopsPerDay.map((ids, i) => ({ day: i + 1, weekday: 'Mon', stops: ids.map(stop) }))
  store.plan = plan
  store.planPrefs = { ...plan.result, days: stopsPerDay.length, must_visit: [], skip: [], day_start: '09:00', day_end: '18:00', pace: 'normal', value_of_time_per_hour: 1000, budget: null, strict_budget: false, locked: [] }
  store.chosenHotel = 'h'
  store.placesById = { a: { id: 'a', name: 'Alpha' }, b: { id: 'b', name: 'Beta' }, c: { id: 'c', name: 'Gamma' } }
  store.wishlist = { a: 'must', b: 'nice', c: 'skip' }
}
beforeEach(() => { resetAll() })

describe('EmptyDayHelp', () => {
  it('is absent when every day has a sight', () => {
    withPlan([['a'], ['b']])
    expect(mount(EmptyDayHelp).find('[data-testid=empty-days]').exists()).toBe(false)
  })
  it('names the empty days, states what is known and does not promise feasibility; skipped sights are never offered', () => {
    withPlan([['a'], [], []])
    const w = mount(EmptyDayHelp)
    const t = w.get('[data-testid=empty-days]').text()
    expect(t).toContain('Day 2, Day 3')
    expect(t).toContain('uses 1 of 3 days')
    expect(t).toContain('not proof of one cause')
    expect(t).toContain('may find that nothing fits')
    expect(w.find('[data-testid=ed-add-b]').exists()).toBe(true)
    expect(w.find('[data-testid=ed-add-c]').exists()).toBe(false)     // marked not interested
    expect(w.find('[data-testid=ed-add-a]').exists()).toBe(false)     // already scheduled
  })
  it('Keep the free days dismisses the panel without any request', async () => {
    withPlan([['a'], []])
    const fetchSpy = vi.fn(); vi.stubGlobal('fetch', fetchSpy)
    const w = mount(EmptyDayHelp)
    await w.get('[data-testid=ed-keep]').trigger('click')
    expect(w.find('[data-testid=empty-days]').exists()).toBe(false)
    expect(fetchSpy).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})

describe('UndoBar', () => {
  it('offers undo only when an earlier accepted plan exists, and restoring swaps the plans back', async () => {
    withPlan([['a']])
    const first = store.plan
    store.history = [{ id: 2, label: 'Move applied', kind: 'accepted', plan: { ...first, marker: 2 }, prefs: store.planPrefs, hotel: 'h' }, { id: 1, label: 'First plan', kind: 'accepted', plan: first, prefs: store.planPrefs, hotel: 'h' }]
    store.plan = store.history[0].plan
    const w = mount(UndoBar)
    expect(w.get('[data-testid=undo-last]').text()).toContain('First plan')
    await w.get('[data-testid=undo-last]').trigger('click')
    expect(store.plan).toBe(first)
  })
  it('is hidden for a single remembered plan', () => {
    withPlan([['a']])
    store.history = [{ id: 1, label: 'First plan', kind: 'accepted', plan: store.plan, prefs: store.planPrefs, hotel: 'h' }]
    expect(mount(UndoBar).find('[data-testid=undo-bar]').exists()).toBe(false)
  })
})

describe('previewProposal', () => {
  it('queues a move without sending anything, and ignores unknown proposal kinds', async () => {
    withPlan([['a'], []])
    const fetchSpy = vi.fn(); vi.stubGlobal('fetch', fetchSpy)
    expect(await previewProposal({ kind: 'move', op: { op: 'move', attraction_id: 'a', day: 2, start_time: '09:00' } })).toBe('pending')
    expect(store.queue.length).toBe(1)
    expect(await previewProposal({ kind: 'apply', patch: { days: 1 } })).toBeNull()
    expect(fetchSpy).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
  it('ignores a remove op smuggled in as a move', async () => {
    withPlan([['a'], []])
    expect(await previewProposal({ kind: 'move', op: { op: 'remove', attraction_id: 'a' } })).toBeNull()
    expect(store.queue.length).toBe(0)
  })
})
