import { describe, expect, it } from 'vitest'
import { applyPatch, buildPreferences, budgetInJpy, DEFAULT_FORM, nightsUsed } from '../../src/lib/prefs.js'

describe('buildPreferences', () => {
  it('builds the strict request body the API expects, with no extra fields', () => {
    const { prefs, errors } = buildPreferences({ ...DEFAULT_FORM(), days: 2 }, { senso_ji: 'must', akihabara: 'skip' }, 110)
    expect(errors).toEqual([])
    expect(Object.keys(prefs).sort()).toEqual(['allow_unknown_hours', 'budget', 'day_end', 'day_start', 'days', 'interests', 'locked', 'max_walking_minutes_per_day',
      'must_visit', 'nights', 'pace', 'skip', 'start_weekday', 'strict_budget', 'value_of_time_per_hour'])
    expect(prefs).toMatchObject({ days: 2, must_visit: ['senso_ji'], skip: ['akihabara'], budget: null, strict_budget: false, nights: null, allow_unknown_hours: false })
  })
  it('converts SGD budgets with the labelled sample rate and keeps JPY as is', () => {
    expect(budgetInJpy({ budgetAmount: '200', budgetCurrency: 'SGD' }, 110)).toBe(22000)
    expect(budgetInJpy({ budgetAmount: '15000', budgetCurrency: 'JPY' }, 110)).toBe(15000)
    expect(budgetInJpy({ budgetAmount: '', budgetCurrency: 'JPY' }, 110)).toBeNull()
    expect(budgetInJpy({ budgetAmount: '-5', budgetCurrency: 'JPY' }, 110)).toBeNaN()
  })
  it('reports plain-language errors and never sends a strict budget without an amount', () => {
    expect(buildPreferences({ ...DEFAULT_FORM(), days: 9 }, {}, 110).errors[0]).toMatch(/1 and 7/)
    expect(buildPreferences({ ...DEFAULT_FORM(), dayStart: '12:00', dayEnd: '10:00' }, {}, 110).errors[0]).toMatch(/end after/)
    const strictNoBudget = buildPreferences({ ...DEFAULT_FORM(), strictBudget: true }, {}, 110)
    expect(strictNoBudget.errors[0]).toMatch(/strict budget needs an amount/)
    expect(strictNoBudget.prefs.strict_budget).toBe(false)
    expect(buildPreferences({ ...DEFAULT_FORM(), budgetAmount: '100', budgetCurrency: 'SGD' }, {}, null).errors[0]).toMatch(/rate has not loaded/)
  })
  it('uses days - 1 nights by default and the user override when set, and shows which', () => {
    expect(nightsUsed({ ...DEFAULT_FORM(), days: 4 })).toBe(3)
    expect(nightsUsed({ ...DEFAULT_FORM(), days: 4, nightsOverride: true, nights: 5 })).toBe(5)
    expect(buildPreferences({ ...DEFAULT_FORM(), nightsOverride: true, nights: 5 }, {}, 110).prefs.nights).toBe(5)
  })
})

describe('applyPatch (conflict actions)', () => {
  it('applies a patch to copies and leaves the originals untouched', () => {
    const form = { ...DEFAULT_FORM(), days: 2 }
    const wl = { akihabara: 'must' }
    const a = applyPatch(form, wl, { days: 3 })
    expect(a.form.days).toBe(3); expect(form.days).toBe(2)
    expect(applyPatch(form, wl, { allow_unknown_hours: true }).form.allowUnknownHours).toBe(true)
    expect(applyPatch(form, wl, { strict_budget: false }).form.strictBudget).toBe(false)
    expect(applyPatch(form, wl, { day_end: '21:00' }).form.dayEnd).toBe('21:00')
    const d = applyPatch(form, wl, { demote_must_visit: 'akihabara' })
    expect(d.wishlist.akihabara).toBe('nice'); expect(wl.akihabara).toBe('must')
  })
})
