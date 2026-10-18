import { describe, it, expect } from 'vitest'
import { DEFAULT_FORM, buildPreferences } from '../../src/lib/prefs.js'

const city = { currency_code: 'JPY', display_currency_code: 'SGD', sample_fx_to_display_currency: 0.0088 }

describe('optional daily limits', () => {
  it('adds no new keys when unset', () => {
    const { prefs } = buildPreferences(DEFAULT_FORM(), {}, city)
    expect('max_activities_per_day' in prefs).toBe(false)
    expect('max_daily_travel_minutes' in prefs).toBe(false)
  })
  it('sends the limits when set', () => {
    const f = { ...DEFAULT_FORM(), maxActivities: '3', maxDailyTravel: '90' }
    const { prefs, errors } = buildPreferences(f, {}, city)
    expect(errors).toEqual([])
    expect(prefs.max_activities_per_day).toBe(3)
    expect(prefs.max_daily_travel_minutes).toBe(90)
  })
  it('rejects out-of-range values with a sentence', () => {
    expect(buildPreferences({ ...DEFAULT_FORM(), maxActivities: '9' }, {}, city).errors.length).toBe(1)
    expect(buildPreferences({ ...DEFAULT_FORM(), maxDailyTravel: '5' }, {}, city).errors.length).toBe(1)
    expect(buildPreferences({ ...DEFAULT_FORM(), maxActivities: '2.5' }, {}, city).errors.length).toBe(1)
  })
})

describe('minimum active days', () => {
  it('is sent only when set and must be between 1 and the number of days', () => {
    expect('min_active_days' in buildPreferences(DEFAULT_FORM(), {}, city).prefs).toBe(false)
    expect(buildPreferences({ ...DEFAULT_FORM(), days: 4, minActiveDays: '3' }, {}, city).prefs.min_active_days).toBe(3)
    for (const bad of ['0', '5', '2.5', 'x']) expect(buildPreferences({ ...DEFAULT_FORM(), days: 4, minActiveDays: bad }, {}, city).errors.length).toBe(1)
  })
})
