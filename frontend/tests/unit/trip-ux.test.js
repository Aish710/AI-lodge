import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../../src/App.vue'
import CreateTrip from '../../src/views/CreateTrip.vue'
import Wishlist from '../../src/views/Wishlist.vue'
import SettingsSummaryStrip from '../../src/components/SettingsSummaryStrip.vue'
import { resetAll, store, chooseHotel } from '../../src/store.js'
import { budgetSanityHint, hasUnsavedWork, tripSummaryText } from '../../src/lib/tripSummary.js'
import places from '../fixtures/places.json'
import feasible from '../fixtures/optimise-feasible.json'
import { res } from './helpers.js'

const RouterLinkTestStub = { props: ['to'], template: '<a><slot /></a>' }

function seedData() {
  store.city = {
    id: 'tokyo',
    display_name: 'Tokyo',
    country: 'Japan',
    currency_code: 'JPY',
    display_currency_code: 'SGD',
    sample_fx_to_display_currency: 1 / 110,
    counts: { attractions: 12, hotels: 3, matrix_nodes: 15 },
  }
  store.cities = [store.city]
  store.fx = { currency_code: 'JPY', display_currency_code: 'SGD', rate: 1 / 110 }
  store.places = places.attractions
  store.placesById = Object.fromEntries(places.attractions.map((p) => [p.id, p]))
  store.hotelsById = Object.fromEntries(places.hotels.map((h) => [h.id, h]))
}

function testRouter() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: CreateTrip },
      { path: '/wishlist', component: Wishlist },
      { path: '/hotels', component: { template: '<SettingsSummaryStrip />', components: { SettingsSummaryStrip } } },
      { path: '/evidence', component: { template: '<div />' } },
    ],
  })
  return router
}

beforeEach(() => {
  resetAll()
  store.server = 'ready'
  seedData()
  vi.unstubAllGlobals()
})

describe('trip settings summary strip', () => {
  it('formats the kept settings compactly with budget conversion and custom nights', () => {
    store.form.budgetAmount = 40000
    store.form.nightsOverride = true
    store.form.nights = 3
    const w = mount(SettingsSummaryStrip, { global: { stubs: { RouterLink: RouterLinkTestStub } } })
    expect(w.get('[data-testid=settings-strip]').text()).toContain('3 days · starts Wed · 09:00-19:00 · budget ¥40,000 (≈ S$363.64 at sample rate) · Balanced · ¥1,000/h · 3 nights (custom)')
    expect(w.get('[data-testid=edit-trip-settings]').text()).toBe('Edit trip settings')
  })

  it('says no budget set when the budget is blank', () => {
    expect(tripSummaryText(store)).toContain('no budget set')
  })
})

describe('in-memory state across navigation', () => {
  it('keeps form values, wishlist and hotel across Next/Back buttons', async () => {
    const router = testRouter()
    router.push('/')
    await router.isReady()
    const w = mount({ template: '<router-view />' }, { global: { plugins: [router] } })
    await w.get('#f-days').setValue('4')
    await w.get('#f-budget').setValue('40000')
    await w.get('form[aria-label="Trip details"]').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/wishlist')
    store.wishlist.senso_ji = 'must'
    chooseHotel('hotel_lantern_asakusa')
    await w.get('button.btn-outline-secondary').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/')
    expect(store.form.days).toBe(4)
    expect(store.form.budgetAmount).toBe(40000)
    expect(store.wishlist.senso_ji).toBe('must')
    expect(store.chosenHotel).toBe('hotel_lantern_asakusa')
  })

  it('keeps state through browser-style back navigation and the edit link', async () => {
    const router = testRouter()
    router.push('/wishlist')
    await router.isReady()
    const w = mount({ template: '<router-view />' }, { global: { plugins: [router] } })
    store.form.days = 5
    store.wishlist.akihabara = 'skip'
    chooseHotel('hotel_harbour_odaiba')
    await router.push('/hotels')
    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/wishlist')
    expect(store.form.days).toBe(5)
    expect(store.wishlist.akihabara).toBe('skip')
    expect(store.chosenHotel).toBe('hotel_harbour_odaiba')
    await router.push('/hotels')
    await w.get('[data-testid=edit-trip-settings]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/')
    expect(store.form.days).toBe(5)
    expect(store.wishlist.akihabara).toBe('skip')
    expect(store.chosenHotel).toBe('hotel_harbour_odaiba')
  })
})

describe('start over, leave guard and budget hint', () => {
  it('clears trip work only after confirmation', async () => {
    vi.stubGlobal('confirm', vi.fn(() => false))
    store.form.days = 6
    store.wishlist.senso_ji = 'must'
    chooseHotel('hotel_lantern_asakusa')
    const router = testRouter()
    router.push('/')
    await router.isReady()
    const w = mount(CreateTrip, { global: { plugins: [router] } })
    await w.get('[data-testid=start-over]').trigger('click')
    expect(store.form.days).toBe(6)
    expect(store.wishlist.senso_ji).toBe('must')
    vi.mocked(window.confirm).mockReturnValue(true)
    await w.get('[data-testid=start-over]').trigger('click')
    expect(store.form.days).toBe(3)
    expect(store.wishlist).toEqual({})
    expect(store.chosenHotel).toBeNull()
  })

  it('guards refresh/close only when unsaved work exists', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url) => {
      if (String(url).endsWith('/health')) return res(200, { status: 'ok', mode: 'sample', llm_configured: false, llm_mode: 'sample', llm_limit_reached: false })
      if (String(url).includes('/data/cities')) return res(200, { cities: [store.city] })
      return res(200, places)
    }))
    const router = testRouter()
    router.push('/')
    await router.isReady()
    const w = mount(App, { global: { plugins: [router], stubs: { HonestyBanner: true, ModeIndicator: true, ServerStatus: true, RateLimitNotice: true } } })
    let e = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(e)
    expect(e.defaultPrevented).toBe(false)
    store.form.days = 4
    expect(hasUnsavedWork(store)).toBe(true)
    e = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(e)
    expect(e.defaultPrevented).toBe(true)
    w.unmount()
  })

  it('shows a non-blocking hint when the budget is far above dataset costs', () => {
    store.form.days = 1
    store.form.pace = 'balanced'
    store.form.budgetAmount = '1000000'
    expect(budgetSanityHint(store)).toContain('much higher')
    const w = mount(CreateTrip, { global: { plugins: [testRouter()] } })
    expect(w.get('[data-testid=budget-sanity-hint]').text()).toContain('Did you mean a smaller number?')
  })

  it('counts a plan as unsaved work', () => {
    expect(hasUnsavedWork(store)).toBe(false)
    store.plan = feasible
    expect(hasUnsavedWork(store)).toBe(true)
  })
})
