// A symbol is printed only if it is unique among the currencies of ALL supported cities; a shared one prints the ISO code.
// A temporary CNY test city (a fixture, not shipped) is registered next to Tokyo, and the registry is restored afterwards.
import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { formatDisplayMoney, formatLocalMoney, setSupportedCurrencies, symbolFor } from '../../src/lib/format.js'
import { money } from '../../src/lib/money.js'
import { describeOp } from '../../src/lib/replan.js'
import { resetAll, store } from '../../src/store.js'
import CityChip from '../../src/components/CityChip.vue'
import DiffView from '../../src/components/DiffView.vue'
import applied from '../fixtures/replan-applied.json'
import cnyCity from '../fixtures/city-cny-test.json'
import tokyo from '../fixtures/places-tokyo.json'
import seoul from '../fixtures/places-seoul.json'
import singapore from '../fixtures/places-singapore.json'
import kl from '../fixtures/places-kuala_lumpur.json'

const SHIPPED = [tokyo.city, seoul.city, singapore.city, kl.city]
let restore = null
const register = (cities) => { restore = setSupportedCurrencies(cities.map((c) => c.currency_code)) }
afterEach(() => { restore?.(); restore = null; resetAll() })

describe('the symbol rule', () => {
  it('shipped cities: every symbol is unique, so symbols are printed', () => {
    register(SHIPPED)
    expect(formatLocalMoney(1500, 'JPY')).toBe('¥1,500')
    expect(formatLocalMoney(135000, 'KRW')).toBe('₩135,000')
    expect(formatLocalMoney(40, 'SGD')).toBe('S$40')
    expect(formatLocalMoney(120, 'MYR')).toBe('RM120')
    expect(symbolFor('JPY')).toBe('¥')
  })

  it('registering a CNY test city next to Tokyo switches Tokyo to "JPY 1,500", and reverting switches it back', () => {
    register(SHIPPED)
    expect(formatLocalMoney(1500, 'JPY')).toBe('¥1,500')
    const undo = setSupportedCurrencies([...SHIPPED, cnyCity].map((c) => c.currency_code))
    expect(formatLocalMoney(1500, 'JPY')).toBe('JPY 1,500')
    expect(formatLocalMoney(1500, 'CNY')).toBe('CNY 1,500')
    expect(formatLocalMoney(1500, 'JPY')).not.toBe(formatLocalMoney(1500, 'CNY'))
    // unaffected currencies keep their unique symbols
    expect(formatLocalMoney(135000, 'KRW')).toBe('₩135,000')
    expect(formatLocalMoney(40, 'SGD')).toBe('S$40')
    undo()
    expect(formatLocalMoney(1500, 'JPY')).toBe('¥1,500')
  })

  it('every screen that prints amounts follows the rule (money helper, diff view, queued budget, display currency)', () => {
    register([...SHIPPED, cnyCity])
    store.city = tokyo.city
    expect(money(3000)).toBe('JPY 3,000')
    expect(describeOp({ op: 'change_budget', budget: 15000, strict: true }, {}, {}, 'JPY')).toBe('Set the budget to JPY 15,000 (strict limit)')
    const diff = mount(DiffView, { props: { result: applied, placesById: {} } }).text()
    expect(diff).toContain('JPY 1,500')
    expect(diff).not.toContain('¥')
    expect(formatDisplayMoney(11000, { sample_fx_to_display_currency: 1 / 110, display_currency_code: 'SGD' })).toBe('S$100.00')
  })

  it('a currency with no known symbol prints "amount CODE"', () => {
    expect(formatLocalMoney(1500, 'XYZ')).toBe('1,500 XYZ')
  })

  it('the city chip shows the currency code, e.g. "Tokyo · JPY"', () => {
    store.city = tokyo.city
    expect(mount(CityChip).get('[data-testid=city-chip]').text().replace(/\s+/g, ' ')).toContain('Tokyo · JPY')
    store.city = seoul.city
    expect(mount(CityChip).get('[data-testid=city-chip]').text().replace(/\s+/g, ' ')).toContain('Seoul · KRW')
  })
})
