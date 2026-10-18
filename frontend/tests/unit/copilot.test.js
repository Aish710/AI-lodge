import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import TripCopilot from '../../src/components/TripCopilot.vue'
import { resetAll, setAiOff, store } from '../../src/store.js'
import { res } from './helpers.js'

let wrapper
beforeEach(() => { resetAll(); setAiOff(false); store.cityId = 'tokyo'; store.planPrefs = { days: 1 }; store.plan = { fingerprint: '1234567890abcdef', result: { status: 'feasible' } } })
afterEach(() => { wrapper?.unmount(); setAiOff(false); vi.unstubAllGlobals() })
const answer = { fingerprint: '1234567890abcdef', message: 'Calculated evidence', evidence: [{ kind: 'unknown', reference: 'dataset.mode', label: 'Data', value: 'Fictional hotels' }], executed: false }

it('quick questions use explicit operations even with AI off and never mutate the plan', async () => {
  setAiOff(true)
  const plan = store.plan
  const fetch = vi.fn(async () => res(200, answer)); vi.stubGlobal('fetch', fetch)
  wrapper = mount(TripCopilot)
  expect(wrapper.find('#copilot-question').exists()).toBe(false)
  await wrapper.findAll('button')[0].trigger('click'); await flushPromises()
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toMatchObject({ operation: 'EXPLAIN_PLAN', fingerprint: plan.fingerprint, preferences: store.planPrefs })
  expect(wrapper.text()).toContain('Fictional hotels'); expect(wrapper.text()).toContain('Nothing applied')
  expect(store.plan).toBe(plan)
})

it('free text classifies without confirmation or mutation fields', async () => {
  const fetch = vi.fn(async () => res(200, answer)); vi.stubGlobal('fetch', fetch)
  wrapper = mount(TripCopilot)
  await wrapper.get('input').setValue('Why expensive?'); await wrapper.get('form').trigger('submit'); await flushPromises()
  const body = JSON.parse(fetch.mock.calls[0][1].body)
  expect(body.text).toBe('Why expensive?'); expect(body.operation).toBeNull(); expect(body.confirmed_ids).toBeUndefined()
})

it('discards a delayed reply when the current plan changes', async () => {
  let finish
  vi.stubGlobal('fetch', vi.fn(() => new Promise(resolve => { finish = resolve })))
  wrapper = mount(TripCopilot)
  await wrapper.findAll('button')[0].trigger('click')
  store.plan = { fingerprint: 'ffffffffffffffff', result: { status: 'feasible' } }; await flushPromises()
  finish(res(200, answer)); await flushPromises()
  expect(wrapper.find('[data-testid=copilot-answer]').exists()).toBe(false)
})

it('does not display raw API failures', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => res(422, { error: { code: 'invalid_schedule', message: 'PRIVATE raw error' } })))
  wrapper = mount(TripCopilot)
  await wrapper.findAll('button')[0].trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('Your plan is unchanged'); expect(wrapper.text()).not.toContain('PRIVATE')
})

it('only opens the existing workflow, without sending an apply request', async () => {
  const fetch = vi.fn(async () => res(200, { ...answer, handoff: 'scenario' })); vi.stubGlobal('fetch', fetch)
  const target = document.createElement('section'); target.dataset.testid = 'whatif'; target.tabIndex = -1; target.scrollIntoView = vi.fn(); document.body.append(target)
  wrapper = mount(TripCopilot)
  await wrapper.findAll('button')[0].trigger('click'); await flushPromises()
  await wrapper.findAll('button').find(b => b.text() === 'Open What if?').trigger('click')
  expect(fetch).toHaveBeenCalledTimes(1); expect(target.scrollIntoView).toHaveBeenCalled(); expect(document.activeElement).toBe(target)
  target.remove()
})

it('invalidates evidence after preferences change in place', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => res(200, answer)))
  wrapper = mount(TripCopilot)
  await wrapper.findAll('button')[0].trigger('click'); await flushPromises()
  expect(wrapper.find('[data-testid=copilot-answer]').exists()).toBe(true)
  store.planPrefs.days = 2; await flushPromises()
  expect(wrapper.find('[data-testid=copilot-answer]').exists()).toBe(false)
})

it('renders source scope as escaped text and rejects non-HTTPS source links', async () => {
  const { default: AttractionCard } = await import('../../src/components/AttractionCard.vue')
  wrapper = mount(AttractionCard, { props: { place: { id: 'a', name: 'A', category: 'garden', duration_minutes: 60, verification: { hours: { state: 'source_checked', source_url: 'javascript:alert(1)', note: '<script>attack</script>', checked_on: '2026-10-18', checked_by: 'web-assisted' } } } } })
  expect(wrapper.text()).toContain('<script>attack</script>')
  expect(wrapper.find('script').exists()).toBe(false)
  expect(wrapper.find('a').exists()).toBe(false)
  expect(wrapper.text()).toContain('not live availability')
})
