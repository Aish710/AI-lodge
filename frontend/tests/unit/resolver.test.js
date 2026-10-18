import { describe, expect, it } from 'vitest'
import { conflictActions, patchFromChanges } from '../../src/lib/rules.js'
import { applyPatch, DEFAULT_FORM } from '../../src/lib/prefs.js'

describe('verified repairs become patches only through structured changes', () => {
  it('maps every lever the server can verify', () => {
    expect(patchFromChanges([{ field: 'max_activities_per_day', from: 2, to: 3 }])).toEqual({ max_activities_per_day: 3 })
    expect(patchFromChanges([{ field: 'days', from: 1, to: 2 }, { field: 'max_daily_travel_minutes', from: 20, to: null }])).toEqual({ days: 2, max_daily_travel_minutes: null })
    expect(patchFromChanges([{ field: 'hotel', from: 'a', to: 'b' }])).toEqual({ hotel: 'b' })
    expect(patchFromChanges([{ field: 'must_visit', removed: 'x' }])).toEqual({ demote_must_visit: 'x' })
  })
  it('refuses to guess an unknown change instead of applying part of it', () => {
    expect(patchFromChanges([{ field: 'days', to: 2 }, { field: 'teleport', to: 1 }])).toBeNull()
    expect(patchFromChanges([])).toBeNull()
  })
  it('keeps the rank, combination and validator flags the server gave', () => {
    const [a] = conflictActions({ alternatives: [{ kind: 'add_day+relax_budget', message: 'Add a day, and treat the budget as soft: a feasible plan exists.', details: { changes: [{ field: 'days', to: 2 }, { field: 'strict_budget', to: false }], rank: 3, combination: true, verified_by_validator: true } }] }, { days: 1, must_visit: [] }, {})
    expect(a).toMatchObject({ rank: 3, combination: true, verified: true, patch: { days: 2, strict_budget: false } })
  })
  it('applying a patch changes only what it names and never touches must-visits unless asked', () => {
    const f = DEFAULT_FORM()
    const r = applyPatch({ ...f, maxActivities: '2', maxDailyTravel: '60' }, { a: 'must' }, { max_activities_per_day: 3, max_daily_travel_minutes: null })
    expect(r.form.maxActivities).toBe('3'); expect(r.form.maxDailyTravel).toBe(''); expect(r.wishlist).toEqual({ a: 'must' })
  })
})
