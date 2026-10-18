import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { applyRepair, cancelRepair, repairApplicable, resetAll, runRepair, runStyleText, applyStyleSettings, setAiOff, store, toggleRepairConfirm } from '../../src/store.js'
import { applyAiSettings, effective, emptyProfile } from '../../src/lib/profiles.js'
import { DEFAULT_FORM, formFromPrefs } from '../../src/lib/prefs.js'
import RepairAssistant from '../../src/components/RepairAssistant.vue'
import StyleAssistant from '../../src/components/StyleAssistant.vue'
import { res } from './helpers.js'
import feasible from '../fixtures/optimise-feasible.json'

const base = { days: 2, budget: null, strict_budget: false, pace: 'balanced', interests: [], must_visit: ['a'], skip: [], day_start: '09:00', day_end: '19:00', value_of_time_per_hour: 1000,
  max_walking_minutes_per_day: 90, start_weekday: 2, allow_unknown_hours: false, nights: null, locked: [] }
const act = (over = {}) => ({ id: 'a1', action: 'set_max_activities', target: 'max_activities_per_day', target_label: 'Activities per day', expected_previous: null, proposed: 3, reason: 'fits', hard_constraint: true, requires_confirmation: false, ...over })
const proposal = (over = {}) => ({ status: 'ok', executed: false, actions: [act()], understood: ['At most 3 activities a day'], unchanged: ['Your hotel stays X'], hard_changes: [], refused: [], unsupported: [], clarifications: [],
  verification: { state: 'verified', verified: true, conflicts: [] }, base_fingerprint: 'fp', keep_hotel: false, keep_hotel_inferred: false, ...over })

beforeEach(() => { resetAll(); store.cityId = 'tokyo'; store.chosenHotel = 'h1'; store.hotelsById = { h1: { id: 'h1', name: 'One' } }; store.placesById = { a: { id: 'a', name: 'Alpha' } }; store.planPrefs = { ...base }
  store.plan = { result: { status: 'infeasible', conflicts: [], days: [], alternatives: [] } }; store.wishlist = { a: 'must' } })
afterEach(() => vi.unstubAllGlobals())

describe('AI repair store', () => {
  it('asks with the CURRENT plan preferences, hotel and the person\'s own hotel lock; nothing is applied', async () => {
    const f = vi.fn(async () => res(200, proposal())); vi.stubGlobal('fetch', f)
    store.repair.keepHotel = true
    await runRepair('make it fit')
    const b = JSON.parse(f.mock.calls[0][1].body)
    expect(b).toMatchObject({ text: 'make it fit', hotel_id: 'h1', keep_hotel: true }); expect(b.preferences).toEqual(store.planPrefs)
    expect(store.repair.proposal.executed).toBe(false); expect(store.plan.result.status).toBe('infeasible')
  })
  it('does nothing when the AI is switched off', async () => {
    const f = vi.fn(); vi.stubGlobal('fetch', f); setAiOff(true)
    await runRepair('x'); expect(f).not.toHaveBeenCalled(); setAiOff(false)
  })
  it('can be applied only when verified AND every confirmation-needing action is ticked', () => {
    const p = proposal({ actions: [act(), act({ id: 'a2', action: 'allow_unknown_hours', requires_confirmation: true })] })
    expect(repairApplicable(p, [])).toBe(false); expect(repairApplicable(p, ['a2'])).toBe(true)
    expect(repairApplicable({ ...p, verification: { state: 'infeasible', verified: false } }, ['a2'])).toBe(false)
    expect(repairApplicable({ ...p, verification: { state: 'conditional', verified: false } }, ['a2'])).toBe(true)
    expect(repairApplicable({ ...p, status: 'needs_clarification' }, ['a2'])).toBe(false)
    expect(repairApplicable(proposal({ actions: [] }), [])).toBe(false)
  })
  it('apply sends the proposal exactly, installs the server plan, syncs the form and wishlist, keeps history and clears the proposal', async () => {
    store.repair.proposal = proposal({ actions: [act({ id: 'a1', action: 'demote_must_visit', target: 'a', expected_previous: 'must', proposed: 'optional', requires_confirmation: true })] })
    toggleRepairConfirm('a1', true)
    const f = vi.fn(async () => res(200, { ...feasible, new_preferences: { ...base, must_visit: [], max_activities_per_day: 3, pace: 'relaxed' }, hotel_id: 'h1', keep_hotel: false }))
    vi.stubGlobal('fetch', f)
    await applyRepair()
    const b = JSON.parse(f.mock.calls[0][1].body)
    expect(b.base_fingerprint).toBe('fp'); expect(b.confirmed_ids).toEqual(['a1']); expect(b.actions[0].requires_confirmation).toBe(true)
    expect(store.plan.result.status).toBe('feasible'); expect(store.form.maxActivities).toBe(3); expect(store.form.pace).toBe('relaxed'); expect(store.wishlist.a).toBe('nice')
    expect(store.history.length).toBe(1); expect(store.repair.proposal).toBeNull()
  })
  it('a stale proposal is dropped, the plan is left alone and the person is told', async () => {
    store.repair.proposal = proposal()
    const before = store.plan
    vi.stubGlobal('fetch', vi.fn(async () => res(409, { error: { code: 'stale_proposal', message: 'The plan changed since this proposal was made.', details: [], request_id: 'r' } })))
    await applyRepair()
    expect(store.plan).toBe(before); expect(store.repair.proposal).toBeNull(); expect(store.repair.error.code).toBe('stale_proposal')
  })
  it('Apply never fires without the ticks and Cancel clears the proposal', async () => {
    store.repair.proposal = proposal({ actions: [act({ requires_confirmation: true })] })
    const f = vi.fn(); vi.stubGlobal('fetch', f)
    await applyRepair(); expect(f).not.toHaveBeenCalled()
    cancelRepair(); expect(store.repair.proposal).toBeNull()
  })
})

describe('RepairAssistant', () => {
  it('shows what was understood, what changes, what stays, the solver check, and a disabled Apply until confirmed', async () => {
    store.repair.proposal = proposal({ actions: [act({ requires_confirmation: true, hard_constraint: true })], hard_changes: ['x'] })
    const w = mount(RepairAssistant, { global: { stubs: { AiMark: true } } })
    expect(w.get('[data-testid=repair-understood]').text()).toContain('At most 3 activities a day')
    expect(w.get('[data-testid=repair-unchanged]').text()).toContain('Your hotel stays X')
    expect(w.get('[data-testid=repair-verification]').text()).toContain('Solved and checked by the independent validator')
    expect(w.get('[data-testid=repair-action-set_max_activities]').text()).toContain('Changes a hard rule')
    expect(w.get('[data-testid=repair-apply]').attributes('disabled')).toBeDefined()
    await w.get('[data-testid=repair-confirm-a1]').setValue(true)
    expect(w.get('[data-testid=repair-apply]').attributes('disabled')).toBeUndefined()
    expect(w.find('[data-testid=repair-cancel]').exists() && w.find('[data-testid=repair-retry]').exists()).toBe(true)
  })
  it('labels an unverified proposal as not verified and keeps Apply disabled', () => {
    store.repair.proposal = proposal({ verification: { state: 'infeasible', verified: false, conflicts: ['No schedule'] } })
    const w = mount(RepairAssistant, { global: { stubs: { AiMark: true } } })
    expect(w.get('[data-testid=repair-verification]').text()).toContain('Not verified: no plan was found'); expect(w.get('[data-testid=repair-apply]').attributes('disabled')).toBeDefined()
  })
  it('a provisional proposal says so', () => {
    store.repair.proposal = proposal({ verification: { state: 'conditional', verified: false, conflicts: [] } })
    expect(mount(RepairAssistant, { global: { stubs: { AiMark: true } } }).get('[data-testid=repair-verification]').text()).toContain('provisional')
  })
  it('with the AI off it shows a note and no input, while nothing else is removed', () => {
    setAiOff(true)
    const w = mount(RepairAssistant, { global: { stubs: { AiMark: true } } })
    expect(w.find('[data-testid=repair-ai-off]').exists()).toBe(true); expect(w.find('[data-testid=repair-text]').exists()).toBe(false); setAiOff(false)
  })
  it('refused and unsupported items are shown, a model failure shows the plan is unchanged', () => {
    store.repair.proposal = proposal({ actions: [], understood: [], refused: [{ input: 'switch_hotel', why: 'You asked to keep your hotel' }], unsupported: ['a quieter route'], verification: null })
    const t = mount(RepairAssistant, { global: { stubs: { AiMark: true } } }).text()
    expect(t).toContain('Not allowed: You asked to keep your hotel'); expect(t).toContain('Not something the planner can do: a quieter route')
    store.repair.proposal = proposal({ status: 'llm_unavailable', actions: [], clarifications: ['The language model could not be reached.'] })
    expect(mount(RepairAssistant, { global: { stubs: { AiMark: true } } }).get('[data-testid=repair-unavailable]').text()).toContain('Your plan is unchanged')
  })
})

describe('AI style settings', () => {
  const settings = [{ field: 'pace', label: 'Pace', current: 'balanced', proposed: 'relaxed', source: 'inferred', reason: 'r', kept_yours: false, requires_confirmation: true },
    { field: 'maxActivities', label: 'Activities per day', current: null, proposed: 3, source: 'explicit', reason: 'r', kept_yours: false, requires_confirmation: true },
    { field: 'must_visit', label: 'Must-visit: Alpha', current: null, proposed: true, source: 'explicit', reason: 'r', target: 'a' }]
  it('applies only what was ticked, records explicit vs inferred, and an explicit value becomes the person\'s own', () => {
    const r = applyAiSettings(DEFAULT_FORM(), emptyProfile(), settings, ['pace', 'maxActivities'])
    expect(r.form.pace).toBe('relaxed'); expect(r.form.maxActivities).toBe(3); expect(r.extra.mustVisit).toEqual([])
    expect(r.state.ai).toEqual({ pace: 'inferred', maxActivities: 'explicit' }); expect(r.state.user.maxActivities).toBe(true); expect(r.state.user.pace).toBeUndefined()
    const rows = effective(r.form, r.state, 1000)
    expect(rows.find((x) => x.field === 'pace').source).toBe('ai-inferred'); expect(rows.find((x) => x.field === 'maxActivities').source).toBe('ai-explicit')
  })
  it('nothing ticked changes nothing; must-visits go to the wishlist only when ticked', () => {
    const f = DEFAULT_FORM()
    expect(applyAiSettings(f, emptyProfile(), settings, []).form).toEqual(f)
    expect(applyAiSettings(f, emptyProfile(), settings, ['must_visita']).extra.mustVisit).toEqual(['a'])
  })
  it('asks the server with the form values and the person\'s overrides, never solving, then applies only on click', async () => {
    store.profile = { ...emptyProfile(), user: { pace: true } }
    const f = vi.fn(async () => res(200, { status: 'ok', executed: false, settings, questions: [], unsupported: [], clarifications: [] })); vi.stubGlobal('fetch', f)
    await runStyleText('slow trip')
    const b = JSON.parse(f.mock.calls[0][1].body)
    expect(b.user_overrides).toEqual(['pace']); expect(b.current).toMatchObject({ pace: 'balanced', maxActivities: null })
    expect(store.form.pace).toBe('balanced')                                // preview only
    applyStyleSettings(['pace']); expect(store.form.pace).toBe('relaxed')
  })
  it('the style box shows the preview with source labels and an apply button only for ticked items', async () => {
    store.styleAi.proposal = { status: 'ok', settings: [{ ...settings[0], kept_yours: true }, settings[1]], questions: ['How much is your budget?'], unsupported: ['quiet'], clarifications: [] }
    const w = mount(StyleAssistant, { global: { stubs: { AiMark: true } } })
    expect(w.get('[data-testid=source-pace]').text()).toContain('Suggested by the AI (inferred)'); expect(w.get('[data-testid=source-maxActivities]').text()).toContain('You said this')
    expect(w.text()).toContain('You set this yourself'); expect(w.get('[data-testid=style-questions]').text()).toContain('budget'); expect(w.get('[data-testid=style-unsupported]').text()).toContain('quiet')
  })
})

describe('formFromPrefs', () => {
  it('mirrors what the server really used and never deletes a must-visit the server kept', () => {
    const { form, wishlist } = formFromPrefs(DEFAULT_FORM(), { a: 'must', b: 'nice', c: 'skip' }, { ...base, must_visit: ['b'], skip: ['a'], max_daily_travel_minutes: 120, allow_unknown_hours: true })
    expect(form.maxDailyTravel).toBe(120); expect(form.allowUnknownHours).toBe(true); expect(form.maxActivities).toBe('')
    expect(wishlist).toEqual({ a: 'skip', b: 'must', c: 'nice' })
  })
})

it('keeps the existing plan when apply-time validation rejects a repair', async () => {
  const before = store.plan, prefs = store.planPrefs
  store.repair.proposal = proposal()
  vi.stubGlobal('fetch', vi.fn(async () => res(422, { error: { code: 'repair_not_feasible', message: 'These changes did not produce a validated plan. Your current plan is unchanged.' } })))
  await applyRepair()
  expect(store.plan).toBe(before); expect(store.planPrefs).toBe(prefs)
  expect(store.repair.error.code).toBe('repair_not_feasible')
})
