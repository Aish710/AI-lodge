import { beforeEach, describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import Plan from '../../src/views/Plan.vue'
import Trip from '../../src/views/Trip.vue'
import { costTerms } from '../../src/lib/costTerms.js'
import { resetAll, store } from '../../src/store.js'
import places from '../fixtures/places.json'
import feasible from '../fixtures/optimise-feasible.json'

const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: Plan }, { path: '/trip', component: Trip }] })
const stubs = Object.fromEntries(['SightsMap', 'TripMap', 'ItineraryCompare', 'TripCopilot', 'TradeoffExplorer', 'WhatIfPanel', 'SensitivityPanel', 'ExplainBlock', 'RepairAssistant', 'ProposedOperations', 'BenefitStrip'].map(k => [k, true]))
function view(component) { return mount(component, { global: { plugins: [router], stubs } }) }
beforeEach(() => {
  resetAll()
  store.city = { id: 'tokyo', display_name: 'Tokyo', currency_code: 'JPY' }
  store.cities = [store.city]
  store.places = places.attractions
  store.placesById = Object.fromEntries(places.attractions.map(p => [p.id, p]))
  store.hotelsById = Object.fromEntries(places.hotels.map(p => [p.id, p]))
  store.chosenHotel = places.hotels[0].id
})

describe('consumer setup', () => {
  it('starts with essentials and discloses attraction selection separately', async () => {
    const w = view(Plan)
    expect(w.get('#f-days').isVisible()).toBe(true)
    expect(w.get('[data-testid=sights-section]').isVisible()).toBe(false)
    expect(w.get('[data-testid=setup-ai]').attributes('open')).toBeDefined()
    await w.get('[data-testid=choose-sights]').trigger('click')
    expect(w.get('[data-testid=sights-section]').attributes('style') ?? '').not.toContain('display: none')
    expect(w.get('form[aria-label="Trip essentials"]').attributes('style')).toContain('display: none')
    w.unmount()
  })
  it('searches names and areas without changing any attraction choices', async () => {
    const w = view(Plan)
    const before = { ...store.wishlist }
    await w.get('[data-testid=setup-sights]').trigger('click')
    await w.get('#sight-search').setValue('Senso')
    expect(w.findAll('[data-testid^="card-"]')).toHaveLength(1)
    expect(store.wishlist).toEqual(before)
    await w.get('#sight-search').setValue('not a real attraction')
    expect(w.text()).toContain('No matching attractions')
    w.unmount()
  })
})
describe('trip sections and money contract', () => {
  function seed(cash) {
    store.plan = structuredClone(feasible)
    store.plan.cost_summary = cash ? { currency: 'JPY', days: [], trip: { cash_total_with_rooms: 12345, cash_total: 345, rooms: 12000, nights: 2, nightly_rate: 6000, admissions: 100, transport: 245, unknown_price_count: 1, unknown_price_ids: ['teamlab_planets'] } } : undefined
    store.planPrefs = { days: 3, must_visit: [], locked: [] }
  }
  it('shows server room-inclusive cash and unknown costs across sections', async () => {
    seed(true)
    const w = view(Trip)
    expect(w.get('[data-testid=kpi-total]').text()).toBe('¥12,345')
    expect(w.get('[data-testid=overview-unknown]').text()).toContain('unknown and excluded')
    await w.get('[data-testid=trip-tab-costs]').trigger('click')
    expect(w.get('#trip-panel-costs').isVisible()).toBe(true)
    expect(w.get('#trip-panel-itinerary').isVisible()).toBe(false)
    expect(w.get('[data-testid=kpi-total]').isVisible()).toBe(true)
    expect(w.get('[data-testid=overview-unknown]').isVisible()).toBe(true)
    w.unmount()
  })
  it('does not label an old API subtotal as cash including rooms', () => {
    seed(false)
    const w = view(Trip)
    expect(w.get('[data-testid=kpi-total]').text()).toBe('Unavailable')
    expect(w.get('[data-testid=kpi-total-parts]').text()).toContain('Room-inclusive summary unavailable')
    w.unmount()
  })
  it('keeps section roles and selection coherent for keyboard navigation', async () => {
    seed(false)
    const w = view(Trip)
    const first = w.get('[data-testid=trip-tab-itinerary]')
    expect(first.attributes('aria-selected')).toBe('true')
    expect(w.get('[data-testid=daychip-1]').attributes('aria-selected')).toBe('true')
    await first.trigger('keydown', { key: 'End' })
    await flushPromises()
    expect(w.get('[data-testid=trip-tab-details]').attributes('tabindex')).toBe('0')
    expect(w.get('#trip-panel-details').isVisible()).toBe(true)
    w.unmount()
  })
})

it('normalises only legacy cost terminology, preserving figures and units', () => {
  expect(costTerms('True cost 40,177 -> 39,510 JPY; true-cost comparison.')).toBe('Generalised cost 40,177 -> 39,510 JPY; generalised cost comparison.')
  expect(costTerms(null)).toBeNull()
})
