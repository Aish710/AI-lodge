import { describe, expect, it } from 'vitest'
import { PROFILES, applyProfile, clearOverrides, effective, emptyProfile, profileName, proposed, syncOverrides } from '../../src/lib/profiles.js'
import { DEFAULT_FORM, buildPreferences } from '../../src/lib/prefs.js'

const city = { currency_code: 'JPY', display_currency_code: 'SGD', sample_fx_to_display_currency: 0.0088 }

describe('travel profiles', () => {
  it('every profile proposes only values the planner accepts', () => {
    for (const p of PROFILES) {
      const w = proposed(p, 1000)
      const { errors, prefs } = buildPreferences({ ...DEFAULT_FORM(), pace: w.pace, maxActivities: w.maxActivities, maxDailyTravel: w.maxDailyTravel, valueOfTime: w.valueOfTime }, {}, city)
      expect(errors, p.id).toEqual([])
      expect(prefs.value_of_time_per_hour).toBe(w.valueOfTime)
    }
  })
  it('a profile changes the actual request fields', () => {
    const r = applyProfile(DEFAULT_FORM(), emptyProfile(), 'relaxed', 1000)
    const { prefs } = buildPreferences(r.form, {}, city)
    expect(prefs).toMatchObject({ pace: 'relaxed', max_activities_per_day: 2, max_daily_travel_minutes: 120 })
    const c = buildPreferences(applyProfile(DEFAULT_FORM(), emptyProfile(), 'convenience', 1000).form, {}, city).prefs
    expect(c.value_of_time_per_hour).toBe(4000)
  })
  it('scales the value of time to the city, not to a currency', () => {
    expect(proposed(PROFILES.find((p) => p.id === 'budget'), 18).valueOfTime).toBe(9)
    expect(proposed(PROFILES.find((p) => p.id === 'convenience'), 15000).valueOfTime).toBe(60000)
  })
  it('a value the user typed survives switching profile; the rest follow the new profile', () => {
    let { form, state } = applyProfile(DEFAULT_FORM(), emptyProfile(), 'relaxed', 1000)
    form = { ...form, maxActivities: 5 }
    state = syncOverrides(form, state)
    expect(state.user).toEqual({ maxActivities: true })
    const r = applyProfile(form, state, 'sightseeing', 1000)
    expect(r.form.maxActivities).toBe(5); expect(r.form.pace).toBe('packed')
    expect(profileName(r.state)).toMatch(/custom/)
  })
  it('shows where each value came from, and reset returns to the profile', () => {
    let { form, state } = applyProfile(DEFAULT_FORM(), emptyProfile(), 'relaxed', 1000)
    form = { ...form, maxDailyTravel: 60 }; state = syncOverrides(form, state)
    const rows = effective(form, state, 1000)
    expect(rows.find((r) => r.field === 'maxDailyTravel').source).toBe('you'); expect(rows.find((r) => r.field === 'pace').source).toBe('profile')
    const back = applyProfile(form, clearOverrides(state), 'relaxed', 1000)
    expect(back.form.maxDailyTravel).toBe(120)
  })
  it('never touches must-visits or inputs it does not own, and does not mutate its arguments', () => {
    const f = DEFAULT_FORM(); const snap = JSON.stringify(f)
    const r = applyProfile(f, emptyProfile(), 'budget', 1000)
    expect(JSON.stringify(f)).toBe(snap)
    expect(r.form.days).toBe(f.days); expect(r.form.budgetAmount).toBe(f.budgetAmount); expect(Object.keys(r.form).sort()).toEqual(Object.keys(f).sort())
  })
})
