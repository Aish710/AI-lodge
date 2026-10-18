// Cited explanations in the interface: chips per fact id, the source number outlined on hover or focus (a shape, keyboard accessible), and the honest badge.
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ExplainBlock from '../../src/components/ExplainBlock.vue'
import { citedNumbers, clearHighlights, highlightFact, HL } from '../../src/lib/citations.js'
import { explanationBadge } from '../../src/lib/rules.js'
import { store } from '../../src/store.js'

const cited = {
  source: 'llm', cited: true, text: 'x', warnings: [], call_count: 1, dropped: 1, grounding: { checked: 4, rejected_tokens: ['S3: uncited'] },
  sentences: [{ text: 'The true cost went from 31,090 JPY to 28,677 JPY.', fact_ids: ['F5'] }, { text: 'Shinjuku Gyoen was removed.', fact_ids: ['F12', 'F13'] }],
  facts: [{ id: 'F5', text: 'True cost: 31,090 JPY before, 28,677 JPY after' }, { id: 'F12', text: 'Removed: Shinjuku Gyoen (removed by user)' }, { id: 'F13', text: 'Added: Tokyo National Museum on day 2 at 13:21' }],
}

beforeEach(() => {
  store.aiOff = false
  document.body.innerHTML = '<main><table><tbody><tr><td id="cost-after">¥28,677</td><td id="other">¥1,200</td></tr></tbody></table><div class="tile-value" id="tile">¥31,090</div></main>'
})
afterEach(() => { clearHighlights(); document.body.innerHTML = '' })

describe('the badge says exactly what was verified', () => {
  it('cited -> every claim cited and checked; plain AI text -> numbers checked; template -> template summary', () => {
    expect(explanationBadge(cited).label).toBe('AI-written, every claim cited and checked')
    expect(explanationBadge({ source: 'llm' }).label).toBe('AI-written, numbers checked')
    expect(explanationBadge({ source: 'template' }).label).toBe('Code-written summary')
  })
})

describe('citation chips', () => {
  it('each sentence is followed by one chip per fact id, with an accessible name that holds the fact', () => {
    const w = mount(ExplainBlock, { props: { explanation: cited }, attachTo: document.body })
    expect(w.get('[data-testid=explain-badge]').text()).toBe('AI-written, every claim cited and checked')
    const chips = w.findAll('.cite-chip')
    expect(chips.map((c) => c.text())).toEqual(['F5', 'F12', 'F13'])
    expect(chips[0].attributes('aria-label')).toBe('Source F5: True cost: 31,090 JPY before, 28,677 JPY after')
    expect(chips[0].element.tagName).toBe('BUTTON')                       // focusable, so the keyboard reaches it
    expect(w.get('[data-testid=explain-text]').text()).toContain('The true cost went from 31,090 JPY to 28,677 JPY.')
    expect(w.get('[data-testid=cite-facts]').text()).toContain('F13: Added: Tokyo National Museum')
    expect(w.get('[data-testid=cite-dropped]').text()).toContain('1 sentence(s) written by the AI were left out')
    w.unmount()
  })
  it('hover or focus outlines the table cells that hold the cited numbers and shows the fact; blur, leave and Escape clear it', async () => {
    const w = mount(ExplainBlock, { props: { explanation: cited }, attachTo: document.body })
    const chip = w.get('[data-testid=cite-F5]')
    await chip.trigger('focus')
    expect(document.getElementById('cost-after').classList.contains(HL)).toBe(true)
    expect(document.getElementById('tile').classList.contains(HL)).toBe(true)
    expect(document.getElementById('other').classList.contains(HL)).toBe(false)
    expect(w.get('[data-testid=cite-source]').text()).toContain('F5: True cost: 31,090 JPY before')
    expect(chip.attributes('aria-describedby')).toBe('cite-source')
    await chip.trigger('blur')
    expect(document.querySelector(`.${HL}`)).toBeNull()
    await chip.trigger('mouseenter')
    expect(document.getElementById('tile').classList.contains(HL)).toBe(true)
    await chip.trigger('mouseleave')
    expect(document.querySelector(`.${HL}`)).toBeNull()
    await chip.trigger('focus'); await chip.trigger('keydown', { key: 'Escape' })
    expect(document.querySelector(`.${HL}`)).toBeNull()
    w.unmount()
  })
  it('a fact with no number in the tables simply highlights nothing, and says what it is', async () => {
    const w = mount(ExplainBlock, { props: { explanation: cited }, attachTo: document.body })
    await w.get('[data-testid=cite-F12]').trigger('focus')
    expect(document.querySelector(`.${HL}`)).toBeNull()
    expect(w.get('[data-testid=cite-source]').text()).toContain('F12: Removed: Shinjuku Gyoen')
    w.unmount()
  })
  it('the explanation block itself is never highlighted, and leaving the page clears the outline', () => {
    document.body.innerHTML += '<main><div data-testid="explain-block"><td id="inside">31,090</td></div></main>'
    expect(highlightFact('True cost: 31,090 JPY')).not.toContain(document.getElementById('inside'))
    clearHighlights()
    const w = mount(ExplainBlock, { props: { explanation: cited }, attachTo: document.body })
    w.get('[data-testid=cite-F5]').trigger('focus')
    w.unmount()
    expect(document.querySelector(`.${HL}`)).toBeNull()
  })
  it('numbers of fewer than three digits are not used to match cells (they would match everything)', () => {
    expect(citedNumbers('Day 2 at 13:21, 225 min, 1,500 JPY, 3 kept')).toEqual(['225', '1500'])
  })
})

describe('plain (not cited) explanations are unchanged', () => {
  it('no chips, the old text and badge', () => {
    const w = mount(ExplainBlock, { props: { explanation: { source: 'llm', text: 'Plain AI text', warnings: [] } } })
    expect(w.findAll('.cite-chip')).toHaveLength(0)
    expect(w.get('[data-testid=explain-text]').text()).toBe('Plain AI text')
    expect(w.get('[data-testid=explain-badge]').text()).toBe('AI-written, numbers checked')
  })
})
