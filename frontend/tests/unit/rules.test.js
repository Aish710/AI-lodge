import { describe, expect, it } from 'vitest'
import { conflictActions, hotelCallout, hoursWarnings, isInfeasible, notScheduledItems } from '../../src/lib/rules.js'
import differs from '../fixtures/compare-differs-true.json'
import same from '../fixtures/compare-differs-false.json'
import infeasible from '../fixtures/optimise-infeasible.json'
import feasible from '../fixtures/optimise-feasible.json'
import places from '../fixtures/places.json'

const byId = Object.fromEntries(places.attractions.map((p) => [p.id, p]))

describe('hotel callout (decision 2): only when the API flag is true', () => {
  it('shows the "not the best value" callout for a real response where the flag is true', () => {
    expect(differs.rate_winner_differs_from_true_winner).toBe(true)
    expect(hotelCallout(differs)).toEqual({ kind: 'differs', text: 'The cheapest rate is not the best value for this trip.' })
  })
  it('shows the neutral line for a real response where the flag is false', () => {
    expect(same.rate_winner_differs_from_true_winner).toBe(false)
    expect(hotelCallout(same)).toEqual({ kind: 'same', text: 'For this trip the cheapest hotel is also the best overall.' })
  })
  it('shows nothing without a winner, and never treats a truthy non-true value as true', () => {
    expect(hotelCallout(null).kind).toBe('none')
    expect(hotelCallout({ best_by_true_cost: null, rate_winner_differs_from_true_winner: false }).kind).toBe('none')
    expect(hotelCallout({ best_by_true_cost: 'h', rate_winner_differs_from_true_winner: 'true' }).kind).toBe('same')
    expect(hotelCallout({ best_by_true_cost: 'h' }).kind).toBe('same')
  })
})

describe('not-scheduled panel mapping (decision 3)', () => {
  it('maps every missed id to a named item with the plain explanation and the penalty when the API gave one', () => {
    const items = notScheduledItems(['meiji_jingu', 'unknown_id'], byId, 3000)
    expect(items).toHaveLength(2)
    expect(items[0]).toMatchObject({ id: 'meiji_jingu', name: byId.meiji_jingu.name, penaltyJpy: 3000, reason: 'Skipped because including it would cost more than it is worth for this plan.' })
    expect(items[1].name).toBe('unknown_id') // falls back to the id, never invents a name
    expect(notScheduledItems(['x'], byId, null)[0].penaltyJpy).toBeNull()
    expect(notScheduledItems(undefined, byId, 1)).toEqual([])
  })
  it('works on a real response', () => {
    const items = notScheduledItems(feasible.result.missed_preferences, byId, null)
    expect(items.length).toBe(feasible.result.missed_preferences.length)
  })
})

describe('infeasible mapping (decision 4)', () => {
  it('HTTP 200 with status infeasible is a normal result, a feasible one is not', () => {
    expect(isInfeasible(infeasible)).toBe(true)
    expect(isInfeasible(feasible)).toBe(false)
    expect(isInfeasible(null)).toBe(false)
  })
  it('turns computed alternatives into patches that re-run the request, and leaves unmappable ones as text', () => {
    const prefs = { days: 2, must_visit: ['akihabara', 'senso_ji'], strict_budget: false }
    const acts = conflictActions(infeasible.result, prefs, byId)
    const kinds = Object.fromEntries(acts.map((a) => [a.kind, a]))
    expect(kinds.allow_unknown_hours.patch).toEqual({ allow_unknown_hours: true })
    expect(kinds.demote_must_visit.patch).toEqual({ demote_must_visit: 'akihabara' })
    const synthetic = { alternatives: [
      { kind: 'add_day', message: 'Add a day (trip becomes 3 days): a feasible plan exists.' },
      { kind: 'relax_budget', message: 'Treat the budget as a soft target instead of a strict limit: a feasible plan exists.' },
      { kind: 'extend_day', message: 'Extend the day end to 21:00: a feasible plan exists.' },
      { kind: 'extend_day', message: 'no time in here' },
      { kind: 'something_new', message: 'A new kind: ok' }] }
    const out = conflictActions(synthetic, prefs, byId)
    expect(out.map((a) => a.patch)).toEqual([{ days: 3 }, { strict_budget: false }, { day_end: '21:00' }, null, null])
    expect(out[0].label).toBe('Add a day (trip becomes 3 days)')
  })
})

describe('closed-day warnings come from the API hours', () => {
  it('lists closed and unknown days for the chosen trip days', () => {
    const tnm = byId.tokyo_national_museum // closed Monday
    expect(hoursWarnings(tnm, 0, 2)).toEqual([{ day: 1, weekday: 'Monday', kind: 'closed' }])
    expect(hoursWarnings(tnm, 2, 3)).toEqual([])
    expect(hoursWarnings(byId.akihabara, 2, 2).map((w) => w.kind)).toEqual(['unknown', 'unknown'])
  })
})
