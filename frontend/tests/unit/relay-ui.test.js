import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import HowItWorks from '../../src/views/HowItWorks.vue'
import MdBlocks from '../../src/components/MdBlocks.vue'
import { parseBlocks } from '../../src/lib/mdparse.js'
import { resetAll, store } from '../../src/store.js'

const mountHow = () => mount(HowItWorks, { global: { stubs: { 'router-link': true } } })
beforeEach(() => { resetAll(); store.health = null })

describe('How it works states the real connection', () => {
  it('a relay: names the gateway host and says the text passes through it (never "direct")', () => {
    store.health = { status: 'ok', mode: 'llm', llm_configured: true, llm_mode: 'llm', llm_limit_reached: false, llm_endpoint: 'api.apiyi.com', llm_relay: true }
    const w = mountHow()
    const note = w.get('[data-testid=relay-note]').text()
    expect(note).toContain('third-party gateway')
    expect(note).toContain('api.apiyi.com')
    expect(note).toContain('passes through that gateway')
    expect(w.find('[data-testid=direct-note]').exists()).toBe(false)
  })
  it('no relay: says direct; sample mode: says neither', () => {
    store.health = { status: 'ok', mode: 'llm', llm_configured: true, llm_mode: 'llm', llm_limit_reached: false, llm_endpoint: 'api.anthropic.com', llm_relay: false }
    expect(mountHow().get('[data-testid=direct-note]').text()).toContain('directly')
    store.health = { status: 'ok', mode: 'sample', llm_configured: false, llm_mode: 'sample', llm_limit_reached: false }
    const w = mountHow()
    expect(w.find('[data-testid=relay-note]').exists()).toBe(false)
    expect(w.find('[data-testid=direct-note]').exists()).toBe(false)
  })
})

describe('generated live files are shown as plain text with the model and host they name', () => {
  it('renders the header line verbatim and never as HTML', () => {
    const md = '# AI self-check (live)\n\nModel: `claude-haiku-4-5-20251001`. Endpoint host: `api.apiyi.com`. Served via a third-party relay: <b>x</b>.\n\n| City | Passed |\n|---|---|\n| Tokyo | 5/5 |\n'
    const w = mount(MdBlocks, { props: { blocks: parseBlocks(md) } })
    expect(w.text()).toContain('claude-haiku-4-5-20251001')
    expect(w.text()).toContain('api.apiyi.com')
    expect(w.text()).toContain('third-party relay')
    expect(w.find('b').exists()).toBe(false)
    expect(w.text()).toContain('Tokyo')
  })
})
