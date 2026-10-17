// The user's own AI on/off switch: the same trip is planned from the form only, an "AI off" chip shows, a note says what the AI would have added, and nothing fires.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ModeIndicator from '../../src/components/ModeIndicator.vue'
import NlParsePanel from '../../src/components/NlParsePanel.vue'
import ProposedOperations from '../../src/components/ProposedOperations.vue'
import ExplainBlock from '../../src/components/ExplainBlock.vue'
import { AI_OFF_LINE, WOULD_ADD } from '../../src/lib/aiOff.js'
import { explain, resetAll, runParse, runProposal, setAiOff, store } from '../../src/store.js'
import feasible from '../fixtures/optimise-feasible.json'

beforeEach(() => { resetAll(); store.aiOff = false; store.health = { mode: 'llm', llm_limit_reached: false, llm_endpoint: 'gw.example.test', llm_model: 'm' }; store.cityId = 'tokyo' })
afterEach(() => { vi.unstubAllGlobals(); store.aiOff = false; store.health = null })

describe('the chip and its popover', () => {
  it('"AI assistant on" offers to switch the AI off; switching shows an "AI off" chip and offers to turn it back on', async () => {
    const w = mount(ModeIndicator)
    expect(w.get('[data-testid=mode-indicator]').text()).toContain('AI assistant on')
    await w.get('[data-testid=ai-popover-button]').trigger('click')
    await w.get('[data-testid=ai-switch-off]').trigger('click')
    expect(store.aiOff).toBe(true)
    expect(w.get('[data-testid=mode-indicator]').text()).toContain('AI off (you switched it off)')
    await w.get('[data-testid=ai-popover-button]').trigger('click')
    expect(w.get('[data-testid=ai-popover]').text()).toContain('AI off: the form works the same.')
    await w.get('[data-testid=ai-switch-on]').trigger('click')
    expect(store.aiOff).toBe(false)
    expect(w.get('[data-testid=mode-indicator]').text()).toContain('AI assistant on')
  })
  it('when the server itself has the AI off there is no switch (nothing to turn off) and the old wording stays', async () => {
    store.health = { mode: 'sample', llm_limit_reached: false }
    const w = mount(ModeIndicator)
    expect(w.get('[data-testid=mode-indicator]').text()).toContain('Sample mode (AI unavailable)')
    await w.get('[data-testid=ai-popover-button]').trigger('click')
    expect(w.find('[data-testid=ai-switch-off]').exists()).toBe(false)
    expect(w.find('[data-testid=ai-switch-on]').exists()).toBe(false)
  })
})

describe('with the AI off nothing fires, whatever is clicked', () => {
  it('runParse, runProposal and explain return without a request and change nothing', async () => {
    const f = vi.fn(); vi.stubGlobal('fetch', f)
    setAiOff(true)
    store.plan = feasible; store.planPrefs = { days: 2 }
    await runParse('3 days in Tokyo'); await runProposal('drop the market'); await explain('optimise')
    expect(f).not.toHaveBeenCalled()
    expect(store.parseResult).toBeNull(); expect(store.proposal).toBeNull(); expect(store.explanations.optimise).toBeNull(); expect(store.busy.parse).toBe(false)
  })
  it('with the AI on, the same calls go out as before (the switch is not a global block)', async () => {
    const f = vi.fn(async () => ({ ok: true, status: 200, headers: { get: () => null }, text: async () => JSON.stringify({ status: 'llm_unavailable', draft: null, raw_input_echo: 'x', clarifications: [] }) })); vi.stubGlobal('fetch', f)
    await runParse('3 days in Tokyo')
    expect(f).toHaveBeenCalled()
  })
})

describe('the three AI cards when the AI is off', () => {
  it('Plan: a calm line, the list of what the AI would have added, a disabled "Ask the AI"; the example chips still only fill the box', async () => {
    setAiOff(true)
    const w = mount(NlParsePanel)
    expect(w.get('[data-testid=ai-off-note]').text()).toContain('switched off for this session; the form works the same. Nothing is sent to a model.')
    expect(w.get('[data-testid=ai-would-add]').text()).toBe(WOULD_ADD.parse)
    await w.get('textarea').setValue('3 days in Tokyo')
    expect(w.get('[data-testid=nl-extract]').attributes('disabled')).toBeDefined()
    await w.get('[data-testid=ex-typical]').trigger('click')
    expect(w.get('textarea').element.value).toContain('Tokyo')
    expect(w.find('[role=alert]').exists()).toBe(false)
  })
  it('Your trip: the change box says the buttons on each stop still work and what the AI would have added; Explain shows a note instead of a button', () => {
    setAiOff(true)
    store.plan = feasible; store.planPrefs = { must_visit: [] }
    const p = mount(ProposedOperations)
    expect(p.get('[data-testid=proposal-ai-off]').text()).toContain(WOULD_ADD.proposal)
    expect(p.get('[data-testid=proposal-button]').attributes('disabled')).toBeDefined()
    const e = mount(ExplainBlock, { props: { explanation: null } })
    expect(e.get('[data-testid=explain-ai-off]').text()).toContain(WOULD_ADD.explain)
    expect(e.find('[data-testid=explain-button]').exists()).toBe(false)
  })
  it('with the AI on, nothing of this shows and the Explain button is there', () => {
    const e = mount(ExplainBlock, { props: { explanation: null } })
    expect(e.find('[data-testid=explain-ai-off]').exists()).toBe(false)
    expect(e.find('[data-testid=explain-button]').exists()).toBe(true)
    expect(mount(NlParsePanel).find('[data-testid=ai-would-add]').exists()).toBe(false)
  })
  it('an existing result stays visible when the AI is switched off afterwards (only new AI calls stop)', () => {
    setAiOff(true)
    const e = mount(ExplainBlock, { props: { explanation: { source: 'template', text: 'Already written', warnings: [] } } })
    expect(e.get('[data-testid=explain-text]').text()).toBe('Already written')
    expect(AI_OFF_LINE).toContain('Nothing is sent to a model')
  })
})
