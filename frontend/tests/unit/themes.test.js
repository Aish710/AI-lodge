import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import Plan from '../../src/views/Plan.vue'
import AttractionCard from '../../src/components/AttractionCard.vue'
import { THEMES, countByTheme, interestsToThemes, isLimited, mixText, themeOf } from '../../src/lib/themes.js'
import { formatPrice } from '../../src/lib/format.js'
import { resetAll, setWish, store, toggleInterestTheme } from '../../src/store.js'
import tokyo from '../fixtures/places-tokyo.json'
import singapore from '../fixtures/places-singapore.json'
import seoul from '../fixtures/places-seoul.json'
import kl from '../fixtures/places-kuala_lumpur.json'

// jsdom has no ResizeObserver; the map components need one when a stub is not applied to an earlier-mounted wrapper
globalThis.ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} }
const PLACES = { tokyo, singapore, seoul, kuala_lumpur: kl }
// the documented inventory (docs/design/themes-inventory.md; backend/tests/test_themes.py pins the same numbers)
const EXPECTED = { tokyo: { sightseeing: 10, shopping: 1, food: 1 }, singapore: { sightseeing: 8, shopping: 1, food: 1 },
  seoul: { sightseeing: 7, shopping: 2, food: 1 }, kuala_lumpur: { sightseeing: 8, shopping: 1, food: 1 } }

function seed(city) {
  const d = PLACES[city]
  store.server = 'ready'
  store.city = { ...d.city, counts: {} }
  store.cityId = city
  store.cities = [store.city]
  store.fx = { currency_code: d.city.currency_code, display_currency_code: d.city.display_currency_code, rate: d.city.sample_fx_to_display_currency }
  store.places = d.attractions
  store.placesById = Object.fromEntries(d.attractions.map((p) => [p.id, p]))
  store.hotelsById = Object.fromEntries(d.hotels.map((h) => [h.id, h]))
}
const mountPlan = () => mount(Plan, { global: { stubs: { SightsMap: true, 'router-link': true } } })
beforeEach(() => { resetAll() })

describe('theme mapping', () => {
  for (const city of Object.keys(PLACES)) {
    it(`${city}: every attraction maps to exactly one known theme and the counts match the inventory`, () => {
      const ids = THEMES.map((t) => t.id)
      for (const p of PLACES[city].attractions) expect(ids).toContain(themeOf(p))
      expect(countByTheme(PLACES[city].attractions)).toEqual(EXPECTED[city])
    })
  }
  it('an unmapped category is an error, not a silent default', () => {
    expect(() => themeOf({ id: 'x', category: 'spaceport' })).toThrow(/No theme/)
  })
  it('limited means fewer than two', () => { expect(isLimited(1)).toBe(true); expect(isLimited(2)).toBe(false) })
  it('mixText counts by theme, leaves zeros out and can lower-case for sentences', () => {
    const a = PLACES.seoul.attractions
    expect(mixText(a.filter((p) => ['gyeongbokgung', 'myeongdong', 'insadong'].includes(p.id)))).toBe('1 Sightseeing, 2 Shopping')
    expect(mixText(a.filter((p) => p.id === 'gwangjang_market'), { lower: true })).toBe('1 food & drink')
  })
})

describe('theme tabs on the Plan screen', () => {
  it('shows All plus every theme with an icon, a text label and a count', () => {
    seed('seoul')
    const w = mountPlan()
    const tabs = w.findAll('[role=tab]')
    expect(tabs.map((t) => t.attributes('data-testid'))).toEqual(['tab-all', 'tab-sightseeing', 'tab-shopping', 'tab-food'])
    expect(w.get('[data-testid=tab-all]').text()).toContain('10')
    expect(w.get('[data-testid=tab-sightseeing]').text()).toContain('Sightseeing')
    expect(w.get('[data-testid=tab-sightseeing]').text()).toContain('7')
    expect(w.get('[data-testid=tab-shopping]').text()).toContain('2')
    expect(w.get('[data-testid=tab-food]').text()).toContain('1')
    expect(w.get('[data-testid=tab-food]').find('svg[aria-hidden=true]').exists()).toBe(true)     // an icon, never colour alone
  })
  it('filters the grid by theme and keeps the chosen tab in memory', async () => {
    seed('seoul')
    const w = mountPlan()
    await w.get('[data-testid=tab-shopping]').trigger('click')
    expect(store.theme).toBe('shopping')
    expect(w.findAll('article[data-testid^=card-]').map((a) => a.attributes('data-testid'))).toEqual(['card-insadong', 'card-myeongdong'].sort((x, y) => (seoul.attractions.findIndex((p) => `card-${p.id}` === x) - seoul.attractions.findIndex((p) => `card-${p.id}` === y))))
    expect(w.get('[data-testid=tab-shopping]').attributes('aria-selected')).toBe('true')
    await w.get('[data-testid=tab-all]').trigger('click')
    expect(w.findAll('article[data-testid^=card-]')).toHaveLength(10)
    expect(mountPlan().get('[data-testid=tab-all]').attributes('aria-selected')).toBe('true')
  })
  it('a theme with fewer than two sights still shows, marked "Limited in the sample data" (Kuala Lumpur food and shopping)', async () => {
    seed('kuala_lumpur')
    const w = mountPlan()
    for (const t of ['food', 'shopping']) {
      expect(w.get(`[data-testid=tab-${t}]`).text()).toContain('Limited in the sample data')
      await w.get(`[data-testid=tab-${t}]`).trigger('click')
      expect(w.findAll('article[data-testid^=card-]')).toHaveLength(1)                       // shown, not hidden, not padded
    }
    expect(w.get('[data-testid=tab-sightseeing]').text()).not.toContain('Limited')
    seed('seoul')
    expect(mountPlan().get('[data-testid=tab-shopping]').text()).not.toContain('Limited')      // two sights: not limited
  })
  it('arrow keys move between tabs (a keyboard-operable tablist)', async () => {
    seed('tokyo')
    const w = mountPlan()
    await w.get('[data-testid=tab-all]').trigger('keydown', { key: 'ArrowRight' })
    expect(store.theme).toBe('sightseeing')
    await w.get('[data-testid=tab-sightseeing]').trigger('keydown', { key: 'End' })
    expect(store.theme).toBe('food')
    expect(w.get('[data-testid=tab-food]').attributes('tabindex')).toBe('0')
    expect(w.get('[data-testid=tab-all]').attributes('tabindex')).toBe('-1')
  })
  it('shows the per-theme count of your must-visits', async () => {
    seed('seoul')
    setWish('gyeongbokgung', 'must'); setWish('myeongdong', 'must'); setWish('insadong', 'must')
    const w = mountPlan()
    expect(w.get('[data-testid=theme-selected]').text()).toContain('1 Sightseeing, 2 Shopping')
  })
})

describe('interests only highlight', () => {
  it('maps free-text interests to themes in code', () => {
    expect([...interestsToThemes(['street food', 'temples'])].sort()).toEqual(['food', 'sightseeing'])
    expect([...interestsToThemes(['Shopping'])]).toEqual(['shopping'])
    expect([...interestsToThemes(['quantum physics'])]).toEqual([])
  })
  it('tags matching sights and sorts them first within the tab, and says it does not change the plan', async () => {
    seed('seoul')
    toggleInterestTheme('shopping')
    const w = mountPlan()
    const cards = w.findAll('article[data-testid^=card-]')
    expect(cards.slice(0, 2).every((c) => c.find('[data-testid=interest-tag]').exists())).toBe(true)
    expect(cards.slice(0, 2).map((c) => c.attributes('data-testid')).sort()).toEqual(['card-insadong', 'card-myeongdong'])
    expect(cards.slice(2).some((c) => c.find('[data-testid=interest-tag]').exists())).toBe(false)
    expect(w.get('[data-testid=interest-hint]').text()).toBe('This only highlights. The planner uses your Must / Include / Skip choices.')
  })
  it('interests read by the AI highlight too, and the planner request does not change (preferences carry no interests)', async () => {
    seed('tokyo')
    store.parsedInterests = ['street food']
    const w = mountPlan()
    expect(w.get('[data-testid=card-tsukiji_outer_market]').find('[data-testid=interest-tag]').exists()).toBe(true)
    const { buildPreferences } = await import('../../src/lib/prefs.js')
    expect(buildPreferences(store.form, store.wishlist, store.city).prefs.interests).toEqual([])
  })
})

describe('prices: Free, Price unknown, and never "RM0 (~$0.00)"', () => {
  it('formatPrice', () => {
    const fx = { currency_code: 'MYR', display_currency_code: 'SGD', rate: 0.3 }
    expect(formatPrice(0, fx)).toBe('Free')
    expect(formatPrice(null, fx)).toBe('Price unknown')
    expect(formatPrice(undefined, fx)).toBe('Price unknown')
    expect(formatPrice(20, fx)).toContain('RM20')
    expect(formatPrice(20, fx)).toContain('S$')
    expect(formatPrice(0, fx)).not.toMatch(/RM0|0\.00/)
  })
  it('a free sight and an unknown-price sight on the cards', () => {
    seed('seoul')
    const free = seoul.attractions.find((p) => p.admission_cost === 0)
    const w = mount(AttractionCard, { props: { place: free, state: 'nice', startWeekday: 2, days: 1, fx: store.fx } })
    expect(w.text()).toContain('Free')
    expect(w.text()).not.toMatch(/₩0|0\.00/)
    const unk = mount(AttractionCard, { props: { place: { ...free, admission_cost: null }, state: 'nice', startWeekday: 2, days: 1, fx: store.fx } })
    expect(unk.text()).toContain('Price unknown')
  })
})

describe('the rough preview shows the theme mix', () => {
  it('lists what is in the running by theme', () => {
    seed('seoul')
    setWish('myeongdong', 'skip')
    const w = mountPlan()
    expect(w.get('[data-testid=preview-mix]').text()).toContain('7 Sightseeing, 1 Shopping, 1 Food & drink')
  })
})
