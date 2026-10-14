// Amounts are printed in the SELECTED city's own currency. A Seoul screen must never show a yen sign (and ¥ is never used for yuan).
import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { formatLocalMoney } from '../../src/lib/format.js'
import { describeOp } from '../../src/lib/replan.js'
import { formFromDraft } from '../../src/lib/prefs.js'
import { resetAll, store } from '../../src/store.js'
import DayTimeline from '../../src/components/DayTimeline.vue'
import DiffView from '../../src/components/DiffView.vue'
import NotScheduledPanel from '../../src/components/NotScheduledPanel.vue'
import feasible from '../fixtures/optimise-feasible.json'
import applied from '../fixtures/replan-applied.json'
import tokyo from '../fixtures/places-tokyo.json'
import seoul from '../fixtures/places-seoul.json'
import singapore from '../fixtures/places-singapore.json'
import kl from '../fixtures/places-kuala_lumpur.json'

const FIXTURES = { tokyo, seoul, singapore, kuala_lumpur: kl }
const SYMBOL = { JPY: '¥', KRW: '₩', SGD: 'S$', MYR: 'RM' }
afterEach(() => resetAll())

describe('formatLocalMoney', () => {
  it('prints each currency unambiguously, and CNY and JPY side by side can never be confused', () => {
    expect(formatLocalMoney(1500, 'JPY')).toBe('¥1,500')
    expect(formatLocalMoney(1500, 'CNY')).toBe('CNY 1,500')
    expect(formatLocalMoney(135000, 'KRW')).toBe('₩135,000')
    expect(formatLocalMoney(120, 'MYR')).toBe('RM120')
    expect(formatLocalMoney(40, 'SGD')).toBe('S$40')
    expect(formatLocalMoney(1500, 'JPY')).not.toBe(formatLocalMoney(1500, 'CNY'))
    expect(formatLocalMoney(1500, 'CNY')).not.toContain('¥')
    expect(formatLocalMoney(1500, 'XYZ')).toBe('1,500 XYZ')
    expect(formatLocalMoney(null, 'KRW')).toBe('unknown')
  })
})

describe('components follow the selected city', () => {
  for (const city of Object.keys(FIXTURES)) {
    it(`${city}: timeline fares, diff lines and the penalty note use ${FIXTURES[city].city.currency_code} only`, () => {
      store.city = FIXTURES[city].city
      const sym = SYMBOL[store.city.currency_code]
      const f = FIXTURES[city]
      const fx = { ...f.fx, ...f.display_fx, currency_code: f.city.currency_code, display_currency_code: f.display_fx.currency_code }  // as the store builds it
      const day = feasible.result.days[0]
      const tl = mount(DayTimeline, { props: { days: [day], placesById: {}, fx, hotelName: 'Hotel X' } }).text()
      const diff = mount(DiffView, { props: { result: applied, placesById: {} } }).text()
      const note = mount(NotScheduledPanel, { props: { missedIds: ['x'], placesById: { x: { name: 'X' } }, penaltyJpy: 3000 } }).text()
      for (const text of [tl, diff, note]) {
        expect(text).toContain(sym)
        if (sym !== '¥') expect(text).not.toContain('¥')
        if (sym !== '₩') expect(text).not.toContain('₩')
      }
    })
  }
  it('a queued budget change is described in the city currency', () => {
    expect(describeOp({ op: 'change_budget', budget: 150000, strict: false }, {}, {}, 'KRW')).toBe('Set the budget to ₩150,000 (soft target)')
    expect(describeOp({ op: 'change_budget', budget: 15000, strict: true }, {}, {})).toBe('Set the budget to ¥15,000 (strict limit)')
  })
  it('a parsed budget draft is kept in the CITY\'s currency, not silently yen', () => {
    const draft = { days: 2, budget: 200000, strict_budget: false, pace: 'balanced', start_weekday: 1, day_start: '09:00', day_end: '19:00', value_of_time_per_hour: 15000, must_visit: [], skip: [], nights: null }
    expect(formFromDraft(draft, undefined, 'KRW').form.budgetCurrency).toBe('KRW')
    expect(formFromDraft(draft).form.budgetCurrency).toBe('JPY')
  })
})
