// The natural-language box and the destination check: results are real ParseResults produced by the backend extraction code with a MOCK model
// (backend/scripts/show_parse_examples.py). Offers never switch anything by themselves.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import NlParsePanel from '../../src/components/NlParsePanel.vue'
import { requestCitySwitch, resetAll, store } from '../../src/store.js'
import { res } from './helpers.js'
import examples from '../fixtures/parse-examples.json'
import seoul from '../fixtures/places-seoul.json'
import tokyo from '../fixtures/places-tokyo.json'

const show = (name) => { store.parseResult = examples[name].result; return mount(NlParsePanel) }
afterEach(() => { vi.unstubAllGlobals(); resetAll(); store.parseResult = null; store.pendingCity = null })

describe('a request for another city', () => {
  it('shows the explanation and a switch BUTTON, but plans nothing and switches nothing', async () => {
    store.cities = [seoul.city, tokyo.city]
    store.cityId = 'seoul'
    store.city = seoul.city
    store.wishlist = { gyeongbokgung: 'must' }          // there is work that a switch would clear
    const w = show('wrong_city_destination')
    expect(w.get('[data-testid=nl-clarifications]').text()).toContain('Nothing was planned')
    expect(w.text()).toContain('Nothing was filled in.')
    const btn = w.get('[data-testid=switch-offer-button]')
    expect(btn.text()).toBe('Switch to Tokyo')
    await btn.trigger('click')
    expect(store.cityId).toBe('seoul')                    // never auto-switched
    expect(store.pendingCity).toBe('tokyo')               // the confirmation (listing what is cleared) is what opens
    expect(store.wishlist).toEqual({ gyeongbokgung: 'must' })
  })

  it('with nothing to lose the switch still needs the user to press the button', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, tokyo)))
    store.cities = [seoul.city, tokyo.city]
    store.cityId = 'seoul'
    store.city = seoul.city
    const w = show('wrong_city_destination')
    expect(store.cityId).toBe('seoul')                    // showing the offer changes nothing
    await w.get('[data-testid=switch-offer-button]').trigger('click')
    await vi.waitFor(() => expect(store.cityId).toBe('tokyo'))
    expect(store.pendingCity).toBeNull()
  })

  it('requestCitySwitch to the current city does nothing', async () => {
    store.cityId = 'seoul'
    await requestCitySwitch('seoul')
    expect(store.pendingCity).toBeNull()
  })
})

describe('other states of the destination and currency checks', () => {
  it('an unsupported city says "not available yet", lists the cities and offers no switch', () => {
    const w = show('unsupported_city')
    expect(w.get('[data-testid=nl-clarifications]').text()).toContain('not available yet')
    for (const c of ['Kuala Lumpur', 'Seoul', 'Singapore', 'Tokyo']) expect(w.get('[data-testid=nl-clarifications]').text()).toContain(c)
    expect(w.find('[data-testid=switch-offer]').exists()).toBe(false)
  })

  it('an ambiguous yen/yuan sign is shown as a currency confirmation, never applied', () => {
    const w = show('currency_confirmation')
    const box = w.get('[data-testid=currency-confirm]')
    expect(box.text()).toContain('Please confirm the currency')
    expect(box.text()).toContain('JPY or CNY')
    expect(box.text()).toContain('KRW')
    expect(examples.currency_confirmation.result.draft.budget).toBeNull()
  })

  it('a generic name that exists in several other cities asks which city and offers no switch; a name ambiguous in the selected city lists only its own places', () => {
    const w1 = show('ambiguous_cross_city_name')
    expect(w1.text()).toContain('several other cities')
    expect(w1.find('[data-testid=switch-offer]').exists()).toBe(false)
    const w2 = show('ambiguous_in_selected_city')
    expect(w2.text()).toContain('Tokyo National Museum')
    expect(w2.text()).toContain('Ghibli Museum')
    expect(w2.find('[data-testid=switch-offer]').exists()).toBe(false)
  })
})
