import { afterEach, describe, expect, it, vi } from 'vitest'
import { resetAll, selectCity, store } from '../../src/store.js'
import places from '../fixtures/places.json'
import { res } from './helpers.js'

const sgPlaces = {
  ...places,
  city: { id: 'singapore', display_name: 'Singapore', currency_code: 'SGD', display_currency_code: 'USD' },
  hotels: [{ id: 'hotel_bay_lantern', name: 'Bay Lantern Stay (fictional)', area: 'Marina Bay', lat: 1.28, lon: 103.85, nightly_rate: 200, source: { record: 'sample' } }],
}

afterEach(() => { vi.unstubAllGlobals(); resetAll() })

describe('switching city', () => {
  it('drops the old city\'s hotels and selections and asks the API for the new city only', async () => {
    store.cities = [{ id: 'tokyo', currency_code: 'JPY' }, { id: 'singapore', currency_code: 'SGD' }]
    store.hotelIds = ['hotel_kitsune_shinjuku', 'hotel_lantern_asakusa']
    store.chosenHotel = 'hotel_kitsune_shinjuku'
    store.hotelsById = Object.fromEntries(places.hotels.map((h) => [h.id, h]))
    const fetchMock = vi.fn(async () => res(200, sgPlaces))
    vi.stubGlobal('fetch', fetchMock)

    await selectCity('singapore')

    expect(fetchMock.mock.calls[0][0]).toContain('city_id=singapore')
    expect(store.hotelIds).toEqual([])
    expect(store.chosenHotel).toBeNull()
    expect(Object.keys(store.hotelsById)).toEqual(['hotel_bay_lantern'])
  })
})
