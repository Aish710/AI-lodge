// Stage 1 (AI first): the Describe card, "What the AI understood", markers, the header popover and the replan card. Canned API responses only.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import NlParsePanel from '../../src/components/NlParsePanel.vue'
import ModeIndicator from '../../src/components/ModeIndicator.vue'
import ProposedOperations from '../../src/components/ProposedOperations.vue'
import ExplainBlock from '../../src/components/ExplainBlock.vue'
import AiMark from '../../src/components/AiMark.vue'
import aiExamples from '../../src/lib/aiExamples.json'
import { assumedList, understoodRows } from '../../src/lib/understood.js'
import { DEFAULT_FORM } from '../../src/lib/prefs.js'
import { resetAll, store } from '../../src/store.js'
import places from '../fixtures/places.json'
import feasible from '../fixtures/optimise-feasible.json'

const CITIES = ['tokyo', 'seoul', 'singapore', 'kuala_lumpur']
const prefs = { days: 3, budget: null, strict_budget: false, pace: 'balanced', interests: [], must_visit: ['senso_ji'], skip: [], day_start: '09:00', day_end: '19:00',
  value_of_time_per_hour: 1000, max_walking_minutes_per_day: 90, start_weekday: 2, allow_unknown_hours: false, nights: null, locked: [] }
const ok = { status: 'ok', draft: { ...prefs, days: 4, budget: 20000, must_visit: ['senso_ji'], skip: ['akihabara'], interests: ['food'] }, raw_input_echo: '4 days, 20000 yen, Senso-ji',
  extracted_json: { days: 4, must_visit_names: ['Senso-ji'] }, defaults_applied: ['pace: balanced (not stated)', 'value of time: 1,000 JPY/hour (not stated)'],
  unresolved_names: [{ input: 'Moon Base', message: 'Not a place in this dataset, so it cannot be scheduled.', suggestions: [] }],
  ambiguities: [{ input: 'the museum', candidates: [{ id: 'tokyo_national_museum', name: 'Tokyo National Museum' }, { id: 'ghibli_museum', name: 'Ghibli Museum' }] }],
  clarifications: ['Which museum do you mean?'], unclear: [], assumptions: {}, call_count: 1, mode: 'llm', prompt_version: '2' }

beforeEach(() => { resetAll(); store.cityId = 'tokyo'; store.city = { currency_code: 'JPY', display_currency_code: 'SGD' }; store.places = places.attractions })
afterEach(() => { vi.unstubAllGlobals(); resetAll(); store.health = null; store.parseResult = null })

describe('the Describe card is the first, primary card', () => {
  it('has the AI-first wording, no "(optional)", and the renamed button', () => {
    const w = mount(NlParsePanel)
    expect(w.get('#nl-h').text()).toContain('Ask the AI to set up your trip')
    expect(w.text()).not.toContain('(optional)')
    expect(w.text()).toContain('The AI fills the form below. You check everything before anything is planned.')
    expect(w.get('[data-testid=nl-extract]').text()).toBe('Ask the AI')
    expect(w.text()).not.toContain('Extract')
  })
  it('the example prompts FILL the box and never send; the three exist for every city and match the pinned backend prompts', async () => {
    const f = vi.fn(); vi.stubGlobal('fetch', f)
    const pinned = JSON.parse(readFileSync(resolve(process.cwd(), '../backend/tests/fixtures/live_eval_prompts_by_city.json'), 'utf8'))
    for (const c of CITIES) {
      store.cityId = c
      const w = mount(NlParsePanel)
      for (const [tid, kind, from] of [['ex-typical', 'typical', 'typical'], ['ex-wrong-city', 'wrong_city', 'wrong_city'], ['ex-vague', 'vague_place', 'ambiguous']]) {
        await w.get(`[data-testid=${tid}]`).trigger('click')
        const want = pinned.find((p) => p.city === c && p.kind === from).text
        expect(w.get('textarea').element.value).toBe(want)
        expect(aiExamples[c][kind]).toBe(want)
      }
    }
    expect(f).not.toHaveBeenCalled()
  })
  it('the wrong-city example names a different city than the one selected', () => {
    for (const c of CITIES) {
      const other = { tokyo: /Seoul/, seoul: /Tokyo/, singapore: /Bangkok/, kuala_lumpur: /Singapore/ }[c]
      expect(aiExamples[c].wrong_city).toMatch(other)
    }
  })
})

describe('What the AI understood', () => {
  it('shows the sentence beside one "AI read" row per field, an "I assumed" list with change links, and never blocks Apply', async () => {
    store.parseResult = ok
    store.form = { ...DEFAULT_FORM(), days: 2 }
    const w = mount(NlParsePanel, { attachTo: document.body })
    expect(w.get('#understood-h').text()).toBe('What the AI understood')
    expect(w.get('[data-testid=nl-raw]').text()).toBe('4 days, 20000 yen, Senso-ji')
    const rows = w.get('[data-testid=nl-rows]')
    expect(rows.get('[data-testid=row-days]').text()).toContain('4')
    expect(rows.get('[data-testid=row-budget]').text()).toContain('20,000')
    expect(rows.get('[data-testid=row-must]').text()).toContain('Senso-ji')
    expect(rows.findAll('[data-testid=ai-mark]').length).toBeGreaterThanOrEqual(4)
    expect(rows.text()).toContain('AI read')
    expect(w.get('[data-testid=nl-defaults]').text()).toContain('pace: balanced (not stated)')
    expect(w.findAll('[data-testid=nl-defaults] button').length).toBe(2)
    expect(w.get('[data-testid=unresolved]').text()).toContain("not in this city's data")
    expect(w.findAll('[data-testid=candidate-chip]')).toHaveLength(2)         // the ambiguity is a choose-one, not a gate
    expect(w.get('[data-testid=nl-applied]').text()).toContain('already filled in')
    expect(w.get('[data-testid=nl-applied]').text()).toContain('Nothing is planned until you click "Plan my trip"')
    const apply = w.get('[data-testid=nl-apply]')
    expect(apply.attributes('disabled')).toBeUndefined()
    await apply.trigger('click')
    expect(store.form.days).toBe(4)                                           // "Apply to my trip" fills the editable form...
    expect(w.get('[data-testid=nl-applied]').text()).toContain('Nothing has been planned yet')
    expect(store.plan).toBeNull()                                              // ...and never plans or advances
    w.unmount()
  })
  it('a field filled by a default is listed under "I assumed", not as an AI read', () => {
    const rows = understoodRows(ok, { places: places.attractions, currency: 'JPY' })
    expect(rows.map((r) => r.field)).not.toContain('pace')
    expect(assumedList(ok.defaults_applied).map((a) => a.field)).toEqual(['f-pace', 'f-vot'])
    expect(assumedList(['pace: balanced (not stated)'])[0].field).toBe('f-pace')
    expect(assumedList(['something new'])[0].field).toBeNull()
  })
  it('a wrong-city answer offers "Switch to <city>" and fills nothing', () => {
    store.cities = [{ id: 'tokyo', display_name: 'Tokyo', country: 'Japan' }, { id: 'seoul', display_name: 'Seoul', country: 'South Korea' }]
    store.parseResult = { status: 'needs_clarification', draft: null, raw_input_echo: '3 days in Tokyo', extracted_json: null, defaults_applied: [], unresolved_names: [], ambiguities: [],
      clarifications: ['That sounds like Tokyo. Nothing was planned.'], unclear: [], assumptions: {}, switch_offer: { city_id: 'tokyo', display_name: 'Tokyo', country: 'Japan' } }
    const w = mount(NlParsePanel)
    expect(w.get('[data-testid=switch-offer-button]').text()).toBe('Switch to Tokyo')
    expect(w.find('[data-testid=nl-apply]').exists()).toBe(false)
    expect(w.find('[data-testid=nl-rows]').exists()).toBe(false)
  })
  it('shows a Cancel while the AI is reading, and a calm line (not an alert) when the AI is off', () => {
    store.busy.parse = true
    expect(mount(NlParsePanel).find('[data-testid=nl-cancel]').exists()).toBe(true)
    store.busy.parse = false
    store.health = { mode: 'sample', llm_limit_reached: false }
    const w = mount(NlParsePanel)
    expect(w.get('[data-testid=ai-off-note]').text()).toContain('AI is off in this deployment; the form works the same.')
    expect(w.find('[role=alert]').exists()).toBe(false)
  })
})

describe('markers and the header popover', () => {
  it('markers are text with the exact tooltip, never colour alone', () => {
    const ai = mount(AiMark, { props: { kind: 'ai' } })
    expect(ai.text()).toContain('AI')
    expect(ai.attributes('title')).toBe('Interpreted or written by the AI. Checked by code before it was shown.')
    expect(mount(AiMark, { props: { kind: 'calc' } }).text()).toContain('Calculated')
  })
  it('opens a two-column popover with the model-free facts, the gateway host from /health, and closes on Escape', async () => {
    store.health = { mode: 'llm', llm_limit_reached: false, llm_endpoint: 'api.example-gateway.test', llm_relay: true, llm_model: 'model-x' }
    const w = mount(ModeIndicator, { attachTo: document.body })
    expect(w.get('[data-testid=mode-indicator]').text()).toContain('AI assistant on')
    expect(w.find('[data-testid=ai-popover]').exists()).toBe(false)
    await w.get('[data-testid=ai-popover-button]').trigger('click')
    const pop = w.get('[data-testid=ai-popover]').text()
    for (const t of ['What the AI does here', 'What it never does', 'Reads your words', 'Pick your schedule', 'Invent prices, hours or times', 'Change your plan without your click', 'Every AI answer is checked by code before you see it.', 'api.example-gateway.test', 'model-x']) expect(pop).toContain(t)
    expect(w.get('[data-testid=ai-popover-button]').attributes('aria-expanded')).toBe('true')
    await w.get('[data-testid=ai-popover-button]').trigger('keydown', { key: 'Escape' })
    expect(w.find('[data-testid=ai-popover]').exists()).toBe(false)
    w.unmount()
  })
  it('when the AI is off the popover says the form works the same, and names no gateway', async () => {
    store.health = { mode: 'sample', llm_limit_reached: false }
    const w = mount(ModeIndicator)
    await w.get('[data-testid=ai-popover-button]').trigger('click')
    expect(w.get('[data-testid=ai-popover]').text()).toContain('AI off: the form works the same.')
  })
})

describe('Your trip: ask the AI to change the plan', () => {
  beforeEach(() => { store.plan = feasible; store.planPrefs = { ...prefs, must_visit: [] }; store.placesById = Object.fromEntries(places.attractions.map((p) => [p.id, p])) })
  it('has example chips built from the current plan that fill the box and send nothing', async () => {
    const f = vi.fn(); vi.stubGlobal('fetch', f)
    const w = mount(ProposedOperations)
    expect(w.get('#pr-h').text()).toContain('Ask the AI to change your plan')
    const chips = w.findAll('[data-testid^=replan-chip-]')
    expect(chips.length).toBe(2)
    expect(chips[0].text()).toMatch(/^Move .+ to the morning$/)
    expect(chips[1].text()).toMatch(/^Skip .+/)
    await chips[1].trigger('click')
    expect(w.get('textarea').element.value).toBe(chips[1].text())
    expect(f).not.toHaveBeenCalled()
  })
  it('proposals are a ticked list; "Add to my changes" queues only the ticked ones and says so', async () => {
    store.proposal = { status: 'ok', executed: false, operations: [{ op: 'remove', attraction_id: 'akihabara' }, { op: 'remove', attraction_id: 'senso_ji' }],
      descriptions: ['Remove Akihabara', 'Remove Senso-ji'], requires_confirmation: true, confirmation_reasons: ['Senso-ji is a must-visit'], clarifications: [], unclear: [], unresolved_names: [], ambiguities: [], raw_input_echo: '' }
    const w = mount(ProposedOperations)
    expect(w.get('[data-testid=proposal-needs-confirmation]').text()).toContain('The AI cannot confirm this for you')
    await w.findAll('[data-testid=proposal-ops] input')[1].setValue(false)
    await w.get('[data-testid=proposal-queue]').trigger('click')
    expect(store.queue).toHaveLength(1)
    expect(w.get('[data-testid=proposal-added]').text()).toContain('Added 1 change(s) to your pending changes. Nothing has been applied yet.')
  })
})

describe('Explain this plan', () => {
  it('is a prominent opt-in button; AI text carries the checked badge and the code warnings verbatim', () => {
    const w0 = mount(ExplainBlock, { props: { explanation: null } })
    expect(w0.get('[data-testid=explain-button]').text()).toBe('Explain this plan')
    const w = mount(ExplainBlock, { props: { explanation: { source: 'llm', text: 'ok', warnings: ['Unknown price: X'] } } })
    expect(w.get('[data-testid=explain-badge]').text()).toBe('AI-written, numbers checked')
    expect(w.get('[data-testid=explain-warnings]').text()).toContain('Unknown price: X')
    expect(w.text()).toContain('How was this checked?')
    expect(mount(ExplainBlock, { props: { explanation: { source: 'template', text: 't', warnings: [] } } }).get('[data-testid=explain-badge]').text()).toBe('Code-written summary')
  })
})

describe('the pitch line', () => {
  it('is the exact agreed sentence', async () => {
    const { PITCH } = await import('../../src/brand.js')
    expect(PITCH).toBe('Choose a hotel based on the trip it makes possible, then build a feasible itinerary around it.')
  })
})

describe('"What the AI did" drawer', () => {
  it('shows calls, raw model output beside what code rejected or changed, the code-only parts, and never a prompt or key', async () => {
    store.health = { mode: 'llm', llm_model: 'model-x', llm_endpoint: 'gw.example.test', llm_limit_reached: false }
    store.parseResult = { ...ok, call_count: 2 }
    const w = mount(NlParsePanel, { attachTo: document.body })
    const d = w.get('[data-testid=ai-drawer-parse]')
    expect(d.text()).not.toContain('Moon Base')                        // closed: nothing technical is rendered
    d.element.open = true
    await d.trigger('toggle')
    expect(d.get('[data-testid=drawer-calls]').text()).toBe('2')
    expect(d.get('[data-testid=drawer-raw]').text()).toContain('"must_visit_names"')
    const changes = d.get('[data-testid=drawer-changes]').text()
    expect(changes).toContain('"Moon Base" was dropped')
    expect(changes).toContain('"the museum" was not guessed')
    expect(changes).toContain('Defaults filled in by code')
    expect(d.get('[data-testid=drawer-code]').text()).toContain("Matched every name to this city's places")
    expect(d.text()).toContain('model-x')
    expect(d.text()).not.toMatch(/system prompt:|api[_ -]?key|sk-/i)
    w.unmount()
  })
  it('explain: a rejected sentence is explained, and an AI-off result says no model was called', async () => {
    const { drawerModel } = await import('../../src/lib/aiDrawer.js')
    const m = drawerModel('explain', { source: 'template', text: 't', warnings: ['W'], call_count: 1, reason: 'grounding check failed', grounding: { checked: 3, rejected_tokens: ['9,999'] } })
    expect(m.changes.map((c) => c.what).join(' ')).toContain('9,999')
    expect(m.changes.some((c) => c.what.includes('1 warning'))).toBe(true)
    const off = drawerModel('parse', { ...ok, mode: 'sample', call_count: 0, extracted_json: null }, { health: { llm_model: 'secret-model' } })
    expect(off.calls).toBe(0)
    expect(off.source).toContain('nothing was sent to a model')
    expect(off.model).toBeNull()
  })
  it('a proposal that removes a must-visit says only the user can allow it', async () => {
    const { drawerModel } = await import('../../src/lib/aiDrawer.js')
    expect(drawerModel('proposal', { requires_confirmation: true, call_count: 1, mode: 'llm', unresolved_names: [], ambiguities: [] }).changes[0].why).toContain('the AI cannot set it')
  })
})
