import { describe, expect, it } from 'vitest'
import { checksTally, hotelVerdict, planStatus, sightsCovered, topWarnings, warningRank } from '../../src/lib/band.js'
import differsTrue from '../fixtures/compare-differs-true.json'
import differsFalse from '../fixtures/compare-differs-false.json'
import feasible from '../fixtures/optimise-feasible.json'
import infeasible from '../fixtures/optimise-infeasible.json'

const fmt = (n) => `¥${n.toLocaleString('en-US')}`

describe('hotel verdict', () => {
  it('names the best hotel and how much cheaper it is when the lowest rate is not the best value', () => {
    const v = hotelVerdict(differsTrue, fmt)
    const gap = differsTrue.ranking.find((r) => r.hotel_id === differsTrue.cheapest_by_rate).gap_to_winner_jpy
    expect(v.kind).toBe('good')
    expect(v.headline).toMatch(/^Best value: /)
    expect(v.headline).toContain(`${fmt(gap)} cheaper overall`)
    expect(v.headline).not.toContain('fictional')
  })
  it('says the cheapest hotel is also the best when they are the same', () => {
    expect(hotelVerdict(differsFalse, fmt).headline).toBe('The cheapest hotel is also the best for this trip')
  })
  it('says so plainly when no hotel can host the trip, and returns nothing before a comparison exists', () => {
    expect(hotelVerdict({ ...differsTrue, best_by_true_cost: null }, fmt)).toMatchObject({ kind: 'bad', headline: 'No hotel can host this trip' })
    expect(hotelVerdict(null, fmt)).toBeNull()
  })
})

describe('plan band', () => {
  it('status chip: Feasible, Feasible with warnings, Not possible (icon + word)', () => {
    expect(planStatus({ result: { status: 'feasible' }, feasibility_report: { overall: 'pass' } })).toMatchObject({ kind: 'good', label: 'Feasible', icon: '✓' })
    expect(planStatus({ result: { status: 'feasible' }, feasibility_report: { overall: 'pass_with_warnings' } })).toMatchObject({ kind: 'warn', label: 'Feasible with warnings' })
    expect(planStatus(infeasible)).toMatchObject({ kind: 'warn', label: 'Blocked by missing information', icon: '!' })   // the fixture's only conflict is unknown opening hours
    expect(planStatus({ result: { status: 'infeasible', conflicts: [{ code: 'closed_all_days', message: 'x', attraction_ids: [] }] }, feasibility_report: { overall: 'fail' } })).toMatchObject({ kind: 'bad', label: 'Not possible', icon: '✕' })
    expect(planStatus({ result: { status: 'feasible' }, feasibility_report: { overall: 'fail' } }).label).toBe('Not possible')
  })
  it('checks passed is n of n from the validator report', () => {
    const t = checksTally(feasible.feasibility_report)
    expect(t.total).toBe(feasible.feasibility_report.checks.length)
    expect(t.passed).toBe(feasible.feasibility_report.checks.filter((c) => c.status === 'pass').length)
    expect(checksTally(null)).toEqual({ passed: 0, total: 0 })
  })
  it('sights covered counts sights the user did not rule out', () => {
    const places = [{ id: 'a' }, { id: 'b' }, { id: 'c' }]
    expect(sightsCovered(2, places, { c: 'skip' })).toEqual({ scheduled: 2, wanted: 2 })
    expect(sightsCovered(3, places, {})).toEqual({ scheduled: 3, wanted: 3 })
  })
})

describe('warnings: top 3, nothing dropped', () => {
  const list = ['Estimates are not live.', 'Price unknown for X; excluded.', 'Budget exceeded by 10.', 'Must-visit Y is not scheduled.', 'Another note.']
  it('ranks must-visit, then budget, then unknown data, and keeps every warning', () => {
    const { shown, more } = topWarnings(list)
    expect(shown).toEqual(['Must-visit Y is not scheduled.', 'Budget exceeded by 10.', 'Price unknown for X; excluded.'])
    expect([...shown, ...more].sort()).toEqual([...list].sort())
    expect(more).toHaveLength(2)
    expect(warningRank('Must-visit x')).toBeLessThan(warningRank('Budget y'))
  })
  it('short lists have nothing hidden', () => {
    expect(topWarnings(['a', 'b']).more).toEqual([])
    expect(topWarnings(undefined)).toEqual({ shown: [], more: [] })
  })
})
