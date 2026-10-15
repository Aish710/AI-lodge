import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import NlParsePanel from '../../src/components/NlParsePanel.vue'
import { resetAll, store } from '../../src/store.js'

beforeEach(() => { resetAll(); store.health = null })
afterEach(() => vi.unstubAllGlobals())

describe('the AI box says plainly when the AI is off', () => {
  it('sample mode: calm note plus its own mode chip, before any click, and no request is made', () => {
    const f = vi.fn(); vi.stubGlobal('fetch', f)
    store.health = { mode: 'sample', llm_limit_reached: false }
    const w = mount(NlParsePanel, { global: { stubs: { 'router-link': true } } })
    expect(w.get('[data-testid=ai-off-note]').text()).toContain('AI is off in this deployment; the form works the same.')
    expect(w.get('[data-testid=ai-box-mode]').text()).toContain('Sample mode')
    expect(f).not.toHaveBeenCalled()
  })
  it('daily limit reached: says so and still says the form works the same', () => {
    store.health = { mode: 'llm', llm_limit_reached: true }
    const w = mount(NlParsePanel, { global: { stubs: { 'router-link': true } } })
    expect(w.get('[data-testid=ai-off-note]').text()).toContain('daily AI limit has been reached')
    expect(w.get('[data-testid=ai-off-note]').text()).toContain('the form works the same')
  })
  it('AI on, or health not loaded yet: no note (no flash of a wrong claim)', () => {
    store.health = { mode: 'llm', llm_limit_reached: false }
    expect(mount(NlParsePanel, { global: { stubs: { 'router-link': true } } }).find('[data-testid=ai-off-note]').exists()).toBe(false)
    store.health = null
    expect(mount(NlParsePanel, { global: { stubs: { 'router-link': true } } }).find('[data-testid=ai-off-note]').exists()).toBe(false)
  })
})
