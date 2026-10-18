import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DiffView from '../../src/components/DiffView.vue'
import PendingChanges from '../../src/components/PendingChanges.vue'
import ProposedOperations from '../../src/components/ProposedOperations.vue'
import NlParsePanel from '../../src/components/NlParsePanel.vue'
import ExplainBlock from '../../src/components/ExplainBlock.vue'
import ConfirmDialog from '../../src/components/ConfirmDialog.vue'
import StopActions from '../../src/components/StopActions.vue'
import { explanationBadge, exampleLabel, originOf, parseState } from '../../src/lib/rules.js'
import { formFromDraft, DEFAULT_FORM } from '../../src/lib/prefs.js'
import { chooseName, explain, maxInputChars, resetAll, runParse, runProposal, store } from '../../src/store.js'
import examples from '../../src/lib/examples.json'
import { res } from './helpers.js'
import applied from '../fixtures/replan-applied.json'
import feasible from '../fixtures/optimise-feasible.json'
import places from '../fixtures/places.json'

const byId = Object.fromEntries(places.attractions.map((p) => [p.id, p]))
const hotels = Object.fromEntries(places.hotels.map((h) => [h.id, h]))
const prefs = { days: 3, budget: null, strict_budget: false, pace: 'balanced', interests: [], must_visit: ['senso_ji'], skip: [], day_start: '09:00', day_end: '19:00',
  value_of_time_per_hour: 1000, max_walking_minutes_per_day: 90, start_weekday: 2, allow_unknown_hours: false, nights: null, locked: [] }
const parseOk = { status: 'ok', draft: { ...prefs, days: 3, budget: 20000, must_visit: ['senso_ji'], skip: ['akihabara'], value_of_time_per_hour: 1100 }, raw_input_echo: '3 days, 20000 yen, Senso-ji',
  extracted_json: { days: 3, must_visit_names: ['Sensoji', 'Secret Shrine'], skip_names: ['Akiba'] }, resolved_names: [], defaults_applied: ['pace: balanced (not stated)'],
  unresolved_names: [{ input: 'Secret Shrine', message: 'Not a place in this dataset, so it cannot be scheduled.', suggestions: [{ id: 'meiji_jingu', name: 'Meiji Jingu', reason: 'similar' }] }],
  ambiguities: [{ input: 'the museum', candidates: [{ id: 'tokyo_national_museum', name: 'Tokyo National Museum' }, { id: 'ghibli_museum', name: 'Ghibli Museum' }] }],
  clarifications: ['Some places are not in this dataset and cannot be scheduled: \'Secret Shrine\'.'], unclear: [],
  assumptions: { fx: 'SAMPLE FX rate (approximate, not live): 1 SGD = 110 JPY', fx_jpy_per_sgd: 110, budget_scope: 'Budget covers attraction admissions + estimated transport fares only (not hotel rooms, food or shopping).', budget_interpreted: '20000 JPY = 20,000 JPY (soft target)' },
  call_count: 1, mode: 'llm', prompt_version: 'v1' }

beforeEach(() => resetAll())
afterEach(() => vi.unstubAllGlobals())

describe('parse-result states (decision 8)', () => {
  it('maps ok / needs_clarification / llm_unavailable / limit reached', () => {
    expect(parseState(null).kind).toBe('idle')
    expect(parseState({ status: 'ok' }).kind).toBe('ok')
    expect(parseState({ status: 'needs_clarification' }).kind).toBe('clarify')
    const down = parseState({ status: 'llm_unavailable' }, false)
    expect(down.kind).toBe('unavailable')
    expect(down.message).toBe('The AI assistant is unavailable right now. Use the form below, everything else works.')
    const limit = parseState({ status: 'llm_unavailable' }, true)
    expect(limit.kind).toBe('limit')
    expect(limit.message).not.toBe(down.message)
    expect(limit.message).toMatch(/daily limit/)
  })

  it('sample mode shows a calm message (not an alert) and the form flow is untouched', async () => {
    store.parseResult = { status: 'llm_unavailable', draft: null, raw_input_echo: 'x', clarifications: ['The language model is not available (sample mode). Please fill in the trip form instead.'], mode: 'sample' }
    const w = mount(NlParsePanel)
    const note = w.get('[data-testid=nl-unavailable]')
    expect(note.text()).toContain('The AI assistant is unavailable right now. Use the form below, everything else works.')
    expect(w.find('[role=alert]').exists()).toBe(false)
    expect(w.find('[data-testid=error-panel]').exists()).toBe(false)
    expect(store.form).toEqual(DEFAULT_FORM())
  })

  it('shows the daily-limit message distinctly when /health says the limit was reached', () => {
    store.health = { mode: 'sample', llm_limit_reached: true }
    store.parseResult = { status: 'llm_unavailable', draft: null, raw_input_echo: 'x', clarifications: [] }
    const w = mount(NlParsePanel)
    expect(w.find('[data-testid=nl-limit]').exists()).toBe(true)
    expect(w.get('[data-testid=nl-limit]').text()).toMatch(/daily limit/)
    store.health = null
  })

  it('over-length text is refused client-side with a counter, and nothing is sent', async () => {
    const f = vi.fn(); vi.stubGlobal('fetch', f)
    const long = 'x'.repeat(maxInputChars + 1)
    await runParse(long)
    expect(f).not.toHaveBeenCalled()
    expect(store.parseError.code).toBe('input_too_long')
    const w = mount(NlParsePanel)
    await w.get('textarea').setValue(long)
    expect(w.get('[data-testid=nl-count]').text()).toContain(`${maxInputChars + 1} / ${maxInputChars}`)
    expect(w.get('[data-testid=nl-extract]').attributes('disabled')).toBeDefined()
    store.proposal = null
    store.plan = feasible; store.planPrefs = prefs
    await runProposal(long)
    expect(f).not.toHaveBeenCalled()
    expect(store.proposalError.code).toBe('input_too_long')
  })

  it('shows raw input next to the extracted JSON, defaults, assumptions in plain words, and fills the EDITABLE form', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, parseOk)))
    await runParse('3 days, 20000 yen, Senso-ji')
    expect(store.form.days).toBe(3)
    expect(store.form.budgetAmount).toBe('20000')
    expect(store.form.valueOfTime).toBe(1100)
    expect(store.wishlist).toEqual({ senso_ji: 'must', akihabara: 'skip' })
    const w = mount(NlParsePanel)
    expect(w.get('[data-testid=nl-raw]').text()).toBe('3 days, 20000 yen, Senso-ji')
    expect(w.get('[data-testid=nl-json]').text()).toContain('"must_visit_names"')
    expect(w.get('[data-testid=nl-defaults]').text()).toContain('pace: balanced (not stated)')
    expect(w.get('[data-testid=nl-assumptions]').text()).toContain('Exchange rate: SAMPLE FX rate')
    expect(w.get('[data-testid=nl-assumptions]').text()).toContain('What the budget covers: Budget covers attraction admissions')
    expect(w.get('[data-testid=nl-assumptions]').text()).not.toContain('fx_jpy_per_sgd')
  })

  it('suggestion chips and candidate pickers never auto-apply: the wishlist changes only on a click, placed per the list the name came from', async () => {
    store.parseResult = parseOk
    const w = mount(NlParsePanel)
    expect(w.findAll('[data-testid=suggestion-chip]')).toHaveLength(1)
    expect(w.findAll('[data-testid=candidate-chip]')).toHaveLength(2)
    expect(store.wishlist.meiji_jingu).toBeUndefined()
    expect(store.wishlist.ghibli_museum).toBeUndefined()
    await w.get('[data-testid=suggestion-chip]').trigger('click')
    expect(store.wishlist.meiji_jingu).toBe('must')   // "Secret Shrine" came from must_visit_names
    expect(w.text()).toContain('Meiji Jingu was added to your sights as "Must visit"')
    expect(originOf('Akiba', parseOk.extracted_json)).toBe('skip')
    chooseName('x', 'skip'); expect(store.wishlist.x).toBe('skip')
  })

  it('formFromDraft maps a draft to the form without submitting anything', () => {
    const { form, wishlist } = formFromDraft({ ...prefs, nights: 5, budget: null }, DEFAULT_FORM())
    expect(form.nightsOverride).toBe(true); expect(form.nights).toBe(5); expect(form.budgetAmount).toBe('')
    expect(wishlist).toEqual({ senso_ji: 'must' })
  })
})

describe('proposed operations card (decision 7)', () => {
  const proposal = (over = {}) => ({ status: 'ok', executed: false, operations: [{ op: 'remove', attraction_id: 'senso_ji' }, { op: 'lock', attraction_id: 'tokyo_skytree', day: 1, start_time: '14:00' }],
    descriptions: ['remove Senso-ji', 'lock Tokyo Skytree to day 1 14:00'], requires_confirmation: true, confirmation_reasons: ['Senso-ji is a must-visit'], clarifications: [], unclear: [], unresolved_names: [], ambiguities: [], ...over })

  it('shows plain-language operations, flags the confirmation, and runs nothing', () => {
    store.proposal = proposal()
    const w = mount(ProposedOperations)
    expect(w.get('[data-testid=proposal-card]').text()).toContain('Proposal only. Nothing has been applied.')
    expect(w.get('[data-testid=proposal-needs-confirmation]').text()).toContain('The AI cannot confirm this for you')
    expect(w.findAll('[data-testid=proposal-ops] li')).toHaveLength(2)
    expect(store.queue).toEqual([])
  })
  it('queues only the ticked operations, drops the proposal, and sets no confirmation', async () => {
    store.proposal = proposal()
    const w = mount(ProposedOperations)
    await w.findAll('[data-testid=proposal-ops] input')[0].setValue(false)
    await w.get('[data-testid=proposal-queue]').trigger('click')
    expect(store.queue).toEqual([{ op: 'lock', attraction_id: 'tokyo_skytree', day: 1, start_time: '14:00' }])
    expect(store.proposal).toBeNull()
  })
  it('a proposal that needs clarification cannot be queued, and "discard" clears it', async () => {
    store.proposal = proposal({ status: 'needs_clarification', clarifications: ['Which museum?'] })
    const w = mount(ProposedOperations)
    expect(w.get('[data-testid=proposal-queue]').attributes('disabled')).toBeDefined()
    expect(w.get('[data-testid=proposal-clarifications]').text()).toContain('Which museum?')
    await w.get('[data-testid=proposal-discard]').trigger('click')
    expect(store.proposal).toBeNull()
  })
  it('sample mode is a calm notice, not an error', () => {
    store.proposal = { status: 'llm_unavailable', operations: [], descriptions: [], clarifications: ['x'], unclear: [], unresolved_names: [], ambiguities: [] }
    const w = mount(ProposedOperations)
    expect(w.get('[data-testid=proposal-unavailable]').text()).toContain('The AI assistant is unavailable right now. Use the form below, everything else works.')
    expect(w.find('[role=alert]').exists()).toBe(false)
  })
})

describe('explanations (decision 4 and C)', () => {
  it('badge rule: only source "llm" is called AI-written; everything else is a template', () => {
    expect(explanationBadge({ source: 'llm' })).toEqual({ kind: 'llm', label: 'AI-written, numbers checked' })
    expect(explanationBadge({ source: 'template' })).toEqual({ kind: 'template', label: 'Code-written summary' })
    expect(explanationBadge(null).kind).toBe('template')
  })
  it('always renders the API warnings verbatim, whatever the source, and calls the text supporting', () => {
    for (const source of ['llm', 'template']) {
      const w = mount(ExplainBlock, { props: { explanation: { text: 'Plan summary.', source, warnings: ['Unknown prices: teamLab Planets is excluded.', 'Not like-for-like: x'] } } })
      expect(w.get('[data-testid=explain-badge]').text()).toBe(source === 'llm' ? 'AI-written, numbers checked' : 'Code-written summary')
      const warn = w.get('[data-testid=explain-warnings]').text()
      expect(warn).toContain('Unknown prices: teamLab Planets is excluded.')
      expect(warn).toContain('Not like-for-like: x')
      expect(w.text()).toContain('source of truth')
      expect(w.text()).toContain('How was this checked?')
    }
  })
  it('is opt-in: a button until clicked, disabled while busy; a grounding rejection shows the template quietly (no scary message)', async () => {
    const w = mount(ExplainBlock, { props: { explanation: null, busy: false } })
    await w.get('[data-testid=explain-button]').trigger('click')
    expect(w.emitted('explain')).toHaveLength(1)
    expect(mount(ExplainBlock, { props: { explanation: null, busy: true } }).get('[data-testid=explain-button]').attributes('disabled')).toBeDefined()
    const rejected = mount(ExplainBlock, { props: { explanation: { text: 'Template text', source: 'template', warnings: [], reason: 'grounding check failed; template used', grounding: { rejected_tokens: ['9,999'] } } } })
    expect(rejected.text()).not.toMatch(/grounding|rejected|9,999|fail/i)
  })
  it('the store asks for explain=true only on an explicit call and keeps the result out of the plan', async () => {
    store.plan = JSON.parse(JSON.stringify(feasible)); store.planPrefs = prefs; store.chosenHotel = 'hotel_lantern_asakusa'
    const f = vi.fn(async () => res(200, { ...feasible, explanation: { text: 'T', source: 'template', warnings: ['w'] } }))
    vi.stubGlobal('fetch', f)
    expect(f).not.toHaveBeenCalled()
    await explain('optimise')
    expect(JSON.parse(f.mock.calls[0][1].body).explain).toBe(true)
    expect(store.explanations.optimise).toEqual({ text: 'T', source: 'template', warnings: ['w'] })
    expect(store.plan.explanation).toBeUndefined()
  })
})

describe('diff, tray, dialog and stop actions render the safety cues', () => {
  it('the diff view shows every line with text cues, all warnings verbatim, and not-like-for-like beside the saving', () => {
    const w = mount(DiffView, { props: { result: applied, placesById: byId } })
    const row = w.get('[data-testid=diff-true_cost_jpy]')
    expect(row.text()).toContain('▼')
    expect(row.text()).toContain('decrease')
    expect(row.get('[data-testid=not-like-for-like]').text()).toContain('Not like-for-like')
    for (const wtext of applied.diff.warnings) expect(w.get('[data-testid=diff-warnings]').text()).toContain(wtext)
    expect(w.get('[data-testid=diff-summary]').text()).toBe(applied.summary)
    expect(w.get('[data-testid=diff-kept]').text()).toContain('Tokyo Skytree')
    expect(w.get('[data-testid=diff-removed]').text()).toContain('teamLab Planets')
    expect(w.get('[data-testid=diff-removed]').text()).toContain('removed by you')
    expect(w.get('[data-testid=diff-disruption]').text()).toContain('¥1,500 per move')
    expect(w.get('[data-testid=feasibility-report]').exists()).toBe(true)
    for (const key of ['admissions_jpy', 'transport_jpy', 'rooms_jpy', 'time_cost_jpy', 'missed_penalty_jpy', 'true_cost_jpy', 'travel_minutes']) expect(w.find(`[data-testid=diff-${key}]`).exists()).toBe(true)
  })
  it('a diff without a not-like-for-like warning shows no such caveat', () => {
    const clean = { ...applied, diff: { ...applied.diff, warnings: [] } }
    expect(mount(DiffView, { props: { result: clean, placesById: byId } }).find('[data-testid=not-like-for-like]').exists()).toBe(false)
  })
  it('the tray lists exactly what will be sent, lets the user remove one, and disables Apply when empty or busy', async () => {
    const queue = [{ op: 'remove', attraction_id: 'teamlab_planets' }, { op: 'lock', attraction_id: 'senso_ji', day: 1, start_time: '10:00' }]
    const w = mount(PendingChanges, { props: { queue, placesById: byId, hotelsById: hotels, hotelChoices: Object.keys(hotels), currentHotel: 'hotel_lantern_asakusa' } })
    expect(w.get('[data-testid=pending-count]').text()).toBe('2 of 20')
    expect(w.get('[data-testid=pending-list]').text()).toContain('Remove teamLab Planets')
    await w.get('[data-testid=unqueue]').trigger('click')
    expect(w.emitted('remove')[0]).toEqual([0])
    await w.get('[data-testid=apply-changes]').trigger('click')
    expect(w.emitted('apply')).toHaveLength(1)
    expect(mount(PendingChanges, { props: { queue: [], placesById: byId, hotelsById: hotels } }).get('[data-testid=apply-changes]').attributes('disabled')).toBeDefined()
    expect(mount(PendingChanges, { props: { queue, placesById: byId, hotelsById: hotels, busy: true } }).get('[data-testid=apply-changes]').attributes('disabled')).toBeDefined()
  })
  it('the dialog emits confirm only from its confirm button and cancel from the other (default-focus) button', async () => {
    const w = mount(ConfirmDialog, { props: { open: false, title: 'Remove a must-visit?', confirmLabel: 'Yes, remove it', cancelLabel: 'Keep it' } })
    expect(w.get('[data-testid=dialog-cancel]').attributes('autofocus')).toBeDefined()
    await w.get('[data-testid=dialog-cancel]').trigger('click')
    expect(w.emitted('confirm')).toBeUndefined()
    expect(w.emitted('cancel')).toHaveLength(1)
    await w.get('[data-testid=dialog-confirm]').trigger('click')
    expect(w.emitted('confirm')).toHaveLength(1)
  })
  it('stop actions only emit queue operations (lock, unlock, remove, move with day-part shortcuts)', async () => {
    const stop = { attraction_id: 'senso_ji', start: '10:00', end: '11:30' }
    const w = mount(StopActions, { props: { stop, day: 2, totalDays: 3, name: 'Senso-ji', locked: false } })
    await w.get('[data-testid=act-lock]').trigger('click')
    await w.get('[data-testid=act-remove]').trigger('click')
    expect(w.emitted('op')).toEqual([[{ op: 'lock', attraction_id: 'senso_ji', day: 2, start_time: '10:00' }], [{ op: 'remove', attraction_id: 'senso_ji' }]])
    await w.get('[data-testid=act-move]').trigger('click')
    await w.findAll('button').find((b) => b.text().startsWith('Afternoon')).trigger('click')
    await w.get('form').trigger('submit')
    expect(w.emitted('op')[2]).toEqual([{ op: 'move', attraction_id: 'senso_ji', day: 2, start_time: '14:00' }])
    const locked = mount(StopActions, { props: { stop, day: 2, totalDays: 3, name: 'Senso-ji', locked: true } })
    await locked.get('[data-testid=act-unlock]').trigger('click')
    expect(locked.emitted('op')[0]).toEqual([{ op: 'unlock', attraction_id: 'senso_ji' }])
  })
})

describe('example trip honesty (decision 1)', () => {
  it('the label and tooltip disclose the high value of time, derived from the example data', () => {
    const l = exampleLabel(examples.tokyo.valid)
    expect(examples.tokyo.valid.form.valueOfTime).toBe(3000)
    expect(l.text).toContain('high value of time')
    expect(l.text).toContain('¥3,000')
    expect(l.title).toContain('not a typical trip')
    expect(exampleLabel({ form: { valueOfTime: 1500 } }).text).toContain('¥1,500')
  })
  it('each city example names its city and uses that city currency', () => {
    expect(exampleLabel(examples.seoul.valid, 'KRW').text).toContain('Seoul')
    expect(exampleLabel(examples.seoul.valid, 'KRW').text).toContain('45,000')
  })
})
