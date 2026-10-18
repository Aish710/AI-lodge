// Your trip screen's cards, against REAL /optimise responses exported by backend/scripts/export_cost_fixtures.py (one per city).
import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CostPanel from '../../src/components/CostPanel.vue'
import DaySelector from '../../src/components/DaySelector.vue'
import DayTimeline from '../../src/components/DayTimeline.vue'
import GettingAround from '../../src/components/GettingAround.vue'
import { formatLocalMoney, humanMinutes } from '../../src/lib/format.js'
import { dayMix, dayStatus } from '../../src/lib/tripView.js'
import { resetAll, store } from '../../src/store.js'
import tokyoP from '../fixtures/places-tokyo.json'
import singaporeP from '../fixtures/places-singapore.json'
import seoulP from '../fixtures/places-seoul.json'
import klP from '../fixtures/places-kuala_lumpur.json'
import tokyoO from '../fixtures/optimise-cost-tokyo.json'
import singaporeO from '../fixtures/optimise-cost-singapore.json'
import seoulO from '../fixtures/optimise-cost-seoul.json'
import klO from '../fixtures/optimise-cost-kuala_lumpur.json'

const CITIES = { tokyo: [tokyoP, tokyoO], singapore: [singaporeP, singaporeO], seoul: [seoulP, seoulO], kuala_lumpur: [klP, klO] }
function seed(city) {
  const [p, o] = CITIES[city]
  store.server = 'ready'
  store.city = { ...p.city, counts: {} }
  store.cityId = city
  store.fx = { currency_code: p.city.currency_code, display_currency_code: p.city.display_currency_code, rate: p.city.sample_fx_to_display_currency }
  store.places = p.attractions
  store.placesById = Object.fromEntries(p.attractions.map((a) => [a.id, a]))
  store.hotelsById = Object.fromEntries(p.hotels.map((h) => [h.id, h]))
  store.plan = o
  store.planPrefs = o._request.preferences
  store.chosenHotel = o._request.hotel_id
  return o
}
beforeEach(() => { resetAll() })

describe('every city: the server totals add up and the cards show exactly those figures', () => {
  for (const city of Object.keys(CITIES)) {
    it(`${city}: day totals sum to the trip totals and to the validated totals`, () => {
      const o = seed(city)
      const cs = o.cost_summary
      expect(cs.days.reduce((n, d) => n + d.day_total, 0)).toBe(cs.trip.cash_total)
      expect(cs.trip.cash_total).toBe(o.result.totals.total_jpy)
      expect(cs.days.reduce((n, d) => n + d.admissions, 0)).toBe(o.result.totals.admissions_jpy)
      expect(cs.days.reduce((n, d) => n + d.transport, 0)).toBe(o.result.totals.transport_jpy)
      expect(cs.trip.cash_total_with_rooms).toBe(cs.trip.cash_total + cs.trip.rooms)
    })
    it(`${city}: Getting around shows the API totals (nothing recomputed in the browser)`, () => {
      const o = seed(city)
      const w = mount(GettingAround)
      expect(w.get('[data-testid=ga-total]').text()).toBe(humanMinutes(o.result.totals.travel_minutes))
      expect(w.get('[data-testid=ga-average]').text()).toBe(humanMinutes(o.cost_summary.trip.avg_travel_minutes_per_day))
      expect(w.get('[data-testid=ga-transport]').text()).toBe(formatLocalMoney(o.result.totals.transport_jpy, o.cost_summary.currency))
      expect(w.get('[data-testid=ga-area]').text()).toBe(o.cost_summary.trip.hotel_area)
      expect(w.text()).toContain('estimated')
      expect(w.text()).toContain('Time moving between places, not time at sights.')
    })
    it(`${city}: the cost panel has one row per day, a Rooms row, a trip total in cash, in the city currency`, () => {
      const o = seed(city)
      const w = mount(CostPanel)
      const cs = o.cost_summary
      for (const d of cs.days) expect(w.get(`[data-testid=cost-day-${d.day}]`).text()).toContain(formatLocalMoney(d.day_total, cs.currency))
      expect(w.get('[data-testid=cost-rooms]').text()).toContain(formatLocalMoney(cs.trip.rooms, cs.currency))
      expect(w.get('[data-testid=trip-cash-total]').text()).toBe(formatLocalMoney(cs.trip.cash_total_with_rooms, cs.currency))
      expect(w.text()).not.toMatch(/(?<![A-Z])\$\d/)   // S$ is fine; a bare $ is not
    })
  }
})

describe('cost panel: unknown prices, budget meter, cash versus true cost', () => {
  it('lists unknown prices by name and never counts them as zero', () => {
    const o = seed('tokyo')
    const withUnknown = JSON.parse(JSON.stringify(o))
    const day = withUnknown.cost_summary.days[0]
    day.unknown_price_ids = ['teamlab_planets']
    withUnknown.cost_summary.trip.unknown_price_ids = ['teamlab_planets']
    withUnknown.cost_summary.trip.unknown_price_count = 1
    store.plan = withUnknown
    const w = mount(CostPanel)
    expect(w.get('[data-testid=cost-unknown]').text()).toContain('1 price is unknown, not included')
    expect(w.get('[data-testid=cost-unknown]').text()).toContain('teamLab Planets')
    expect(w.get(`[data-testid=cost-day-${day.day}]`).text()).toContain('1 price(s) unknown')
    expect(w.text()).not.toMatch(/¥0 \(/)
  })
  it('a free day with no unknown prices says Free for admissions', () => {
    const o = seed('tokyo')
    const free = JSON.parse(JSON.stringify(o))
    Object.assign(free.cost_summary.days[0], { admissions: 0, unknown_price_ids: [] })
    store.plan = free
    expect(mount(CostPanel).get(`[data-testid=cost-day-${free.cost_summary.days[0].day}]`).text()).toContain('Free')
  })
  it('shows a budget meter with its scope only when a budget is set, and says when it is exceeded', () => {
    const o = seed('seoul')
    store.planPrefs = { ...store.planPrefs, budget: null }
    expect(mount(CostPanel).find('[data-testid=budget-meter]').exists()).toBe(false)
    store.planPrefs = { ...store.planPrefs, budget: o.cost_summary.trip.cash_total + 10000, strict_budget: false }
    let w = mount(CostPanel)
    const meter = w.get('[data-testid=budget-meter] [role=meter]')
    expect(meter.attributes('aria-valuenow')).toBe(String(o.cost_summary.trip.cash_total))
    expect(w.get('[data-testid=budget-meter]').text()).toContain('sights and transport only (not rooms or food)')
    expect(w.get('[data-testid=budget-meter]').text()).toContain('left')
    store.planPrefs = { ...store.planPrefs, budget: o.cost_summary.trip.cash_total - 5000 }
    w = mount(CostPanel)
    expect(w.get('[data-testid=budget-meter]').text()).toContain('Over by')
  })
  it('keeps cash cost and true cost as two figures, and never labels true cost as money', () => {
    const o = seed('seoul')
    store.comparison = { results: [{ hotel_id: o._request.hotel_id, breakdown: { true_cost_jpy: o.cost_summary.trip.cash_total + 123456 } }] }
    const w = mount(CostPanel)
    expect(w.get('[data-testid=figure-cash]').text()).toContain(formatLocalMoney(o.cost_summary.trip.cash_total, 'KRW'))
    expect(w.get('[data-testid=figure-true]').text()).toContain('a comparison figure, not money')
    expect(w.get('[data-testid=figure-true]').text()).toContain(formatLocalMoney(o.cost_summary.trip.cash_total + 123456, 'KRW'))
    expect(w.get('[data-testid=two-figures]').text()).toContain('Cash cost')
    expect(w.get('[data-testid=two-figures]').text()).toContain('True cost')
  })
})

describe('day selector, day cards, event cards, connectors', () => {
  const mountTimeline = (city, extra = {}) => {
    const o = seed(city)
    return { o, w: mount(DayTimeline, { props: { days: o.result.days, placesById: store.placesById, fx: store.fx, hotelName: 'Hotel X', costDays: o.cost_summary.days, ...extra } }) }
  }
  it('All shows every day; a selected day shows only that day', async () => {
    const { o, w } = mountTimeline('kuala_lumpur')
    expect(w.findAll('[data-testid^=day-block], section.day-block')).toHaveLength(o.result.days.length)
    await w.setProps({ selectedDay: 2 })
    expect(w.findAll('section.day-block')).toHaveLength(1)
    expect(w.get('section.day-block').attributes('data-testid')).toBe('day-2')
  })
  it('the selector has a chip per day plus All, selected by text and style, with arrow-key navigation', async () => {
    const o = seed('seoul')
    const w = mount(DaySelector, { props: { days: o.result.days } })
    expect(w.findAll('[role=tab]').map((t) => t.text().replace('✓ ', '').replace(' (selected)', ''))).toEqual([...o.result.days.map((d) => `Day ${d.day}`), 'All days'])
    await w.get('[data-testid=daychip-1]').trigger('click')
    expect(store.selectedDay).toBe(1)
    expect(w.get('[data-testid=daychip-1]').text()).toContain('selected')
    expect(w.get('[data-testid=daychip-1]').attributes('aria-selected')).toBe('true')
    await w.get('[data-testid=daychip-1]').trigger('keydown', { key: 'ArrowRight' })
    expect(store.selectedDay).toBe(2)
    await w.get('[data-testid=daychip-2]').trigger('keydown', { key: 'End' })
    expect(store.selectedDay).toBe('all')
  })
  it('a day card shows weekday, stops, time at sights, travel, cash cost, theme mix and a one-line status', () => {
    const { o, w } = mountTimeline('seoul')
    const d = o.result.days.find((x) => x.stops.length)
    const cd = o.cost_summary.days.find((x) => x.day === d.day)
    const facts = w.get(`[data-testid=day-facts-${d.day}]`).text()
    expect(facts).toContain(`${d.stops.length} stops`)
    expect(facts).toContain('At sights')
    expect(facts).toContain('Travel')
    expect(facts).toContain(formatLocalMoney(cd.day_total, 'KRW'))
    const mix = w.get(`[data-testid=day-mix-${d.day}]`).text()
    expect(mix).toContain(`Day ${d.day}: ${dayMix(d, store.placesById)}`)
    expect(mix).toContain(dayStatus(d))
    expect(w.get(`[data-testid=day-card-${d.day}]`).text()).toMatch(/Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday/)
  })
  it('an event card has time range and duration, name, theme icon and label, tags and a cost line', () => {
    const { o, w } = mountTimeline('tokyo')
    const s = o.result.days.find((x) => x.stops.length).stops[0]
    const card = w.get(`[data-testid=stop-${s.attraction_id}]`)
    expect(card.get(`[data-testid=time-${s.attraction_id}]`).text()).toContain(`${s.start}–${s.end}`)
    expect(card.text()).toContain(store.placesById[s.attraction_id].name)
    expect(card.get('[data-testid=event-theme]').text()).toMatch(/Sightseeing|Shopping|Food & drink/)
    expect(card.get(`[data-testid=cost-${s.attraction_id}]`).text()).toMatch(/Admission: (Free|Price unknown|\S)/)
  })
  it('tags: Must visit vs Include if it fits, Needs booking, Unknown hours, Locked', () => {
    const o = seed('tokyo')
    const stops = [
      { attraction_id: 'senso_ji', start: '09:00', end: '10:30', travel_minutes_from_previous: 20, transport_jpy_from_previous: 220, cost: 0, cost_status: 'known', is_must_visit: true, uncertainty_flags: [] },
      { attraction_id: 'teamlab_planets', start: '11:00', end: '13:00', travel_minutes_from_previous: 30, transport_jpy_from_previous: 300, cost: 0, cost_status: 'unknown', is_must_visit: false, uncertainty_flags: ['price_unknown', 'advance_booking_required', 'opening_hours_unknown'] },
    ]
    const day = { day: 1, weekday: 'wed', hotel_departure: '08:30', hotel_return: '14:00', return_travel_minutes: 25, return_transport_jpy: 250, stops }
    const w = mount(DayTimeline, { props: { days: [day], placesById: store.placesById, fx: store.fx, hotelName: 'Hotel X', lockedIds: ['senso_ji'] } })
    expect(w.get('[data-testid=tags-senso_ji]').text()).toContain('Must visit')
    expect(w.get('[data-testid=tags-senso_ji]').text()).not.toContain('Needs booking')
    expect(w.get('[data-testid=stop-senso_ji] [data-testid=locked-pill]').exists()).toBe(true)
    const t = w.get('[data-testid=tags-teamlab_planets]').text()
    expect(t).toContain('Include if it fits')
    expect(t).toContain('Needs booking')
    expect(t).toContain('Opening hours unverified')
    expect(w.get('[data-testid=cost-teamlab_planets]').text()).toContain('Price unknown')
    expect(w.get('[data-testid=cost-teamlab_planets]').text()).toContain('not in the total')
    expect(o).toBeTruthy()
  })
  it('connectors say travel time, fare and "estimated" in one line; no transport mode is claimed', () => {
    const { o, w } = mountTimeline('kuala_lumpur')
    const first = w.get('[data-testid=connector-1-0]').text()
    expect(first).toMatch(/Travel .*min · .* · estimated/)
    expect(first).toContain('from the hotel')
    expect(w.get('[data-testid=connector-1-back]').text()).toContain('back to the hotel')
    expect(w.text()).not.toMatch(/Train|Bus|Metro|Taxi|Walk/)
    expect(o).toBeTruthy()
  })
  it('hovering or focusing an event card announces its stop for the map link', async () => {
    const { o, w } = mountTimeline('seoul')
    const id = o.result.days.find((x) => x.stops.length).stops[0].attraction_id
    await w.get(`[data-testid=stop-${id}]`).trigger('mouseenter')
    expect(w.emitted('hover-stop').at(-1)).toEqual([id])
    await w.get(`[data-testid=stop-${id}]`).trigger('mouseleave')
    expect(w.emitted('hover-stop').at(-1)).toEqual([null])
    await w.setProps({ activeStop: id })
    expect(w.get(`[data-testid=stop-${id}]`).classes()).toContain('is-active')
  })
})
