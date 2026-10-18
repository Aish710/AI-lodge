import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { categoryOf, describeConflicts, headline, repairViews, resultState } from '../../src/lib/conflicts.js'
import { planStatus } from '../../src/lib/band.js'
import ConflictPanel from '../../src/components/ConflictPanel.vue'
import FeasibilityReport from '../../src/components/FeasibilityReport.vue'

const byId = { national_mosque_malaysia: { id: 'national_mosque_malaysia', name: 'National Mosque of Malaysia' } }
const conflict = { code: 'unknown_hours_not_allowed', message: 'Must-visit National Mosque of Malaysia has unknown opening hours, and unknown hours are not allowed (it is never assumed open).', attraction_ids: ['national_mosque_malaysia'], category: 'missing_information' }
const alt = (kind, changes, over = {}) => ({ kind, message: `${kind}: a feasible plan exists.`, details: { attractions_scheduled: 6, total_jpy: 177, travel_minutes: 120, changes, verified_by_validator: true, rank: 1, ...over } })
const result = (alternatives = [alt('allow_unknown_hours', [{ field: 'allow_unknown_hours', from: false, to: true }]), alt('demote_must_visit', [{ field: 'must_visit', removed: 'national_mosque_malaysia' }], { rank: 2 })]) =>
  ({ status: 'infeasible', conflicts: [conflict], alternatives, days: [] })
const mountIt = (r = result()) => mount(ConflictPanel, { props: { result: r, prefs: { days: 2, must_visit: ['national_mosque_malaysia'] }, placesById: byId } })

describe('classifying a result', () => {
  it('missing information is not the same as an infeasible plan', () => {
    expect(resultState({ result: result() })).toBe('blocked_missing_info')
    expect(resultState({ result: { status: 'infeasible', conflicts: [{ code: 'closed_all_days', message: 'x' }] } })).toBe('infeasible')
    expect(resultState({ result: { status: 'infeasible', conflicts: [conflict, { code: 'pace_cap', message: 'x' }] } })).toBe('infeasible')   // mixed: a known constraint is also involved
    expect(resultState({ result: { status: 'feasible' }, feasibility_report: { verification: 'conditional' } })).toBe('conditional')
    expect(resultState({ result: { status: 'feasible' }, feasibility_report: { verification: 'verified' } })).toBe('feasible')
  })
  it('older responses without a category are classified by their code', () => {
    expect(categoryOf({ code: 'unknown_hours_not_allowed' })).toBe('missing_information')
    expect(categoryOf({ code: 'pace_cap' })).toBe('known_constraints')
  })
  it('the chip says which of the three it is', () => {
    expect(planStatus({ result: result() }).label).toBe('Blocked by missing information')
    expect(planStatus({ result: { status: 'feasible' }, feasibility_report: { overall: 'pass_with_warnings', verification: 'conditional' } }).label).toBe('Feasible if opening hours are confirmed')
    expect(planStatus({ result: { status: 'infeasible', conflicts: [{ code: 'pace_cap', message: 'x' }] } }).label).toBe('Not possible')
  })
  it('never claims real-world impossibility for missing data', () => {
    const t = JSON.stringify([headline('blocked_missing_info'), describeConflicts([conflict], byId)])
    expect(t).toMatch(/missing information/); expect(t).toMatch(/not a finding that the visit is impossible/); expect(t).not.toMatch(/cannot be visited|is closed|impossible to visit/i)
  })
})

describe('the conflict panel', () => {
  it('shows a friendly title and explanation; the raw code and technical sentence are only in the technical details', () => {
    const w = mountIt()
    const main = w.get('[data-testid=conflict-friendly]').text() + w.get('[data-testid=conflict-title]').text()
    expect(main).toContain("We don't know when National Mosque of Malaysia is open")
    expect(main).not.toContain('unknown_hours_not_allowed')
    expect(w.get('[data-testid=technical-details]').text()).toContain('unknown_hours_not_allowed')
    expect(w.text()).toContain('not a fault')
  })
  it('every repair has a title, the exact change, why it may help, the verified label and its effect, and an Apply button', () => {
    const w = mountIt()
    const cards = w.findAll('[data-testid=alternatives] > li')
    expect(cards.length).toBe(2)
    for (const c of cards) {
      expect(c.get('[data-testid=repair-title]').text().length).toBeGreaterThan(5)
      expect(c.get('[data-testid=repair-why]').text()).toContain('Why it may help')
      expect(c.get('[data-testid=repair-effect]').text()).toContain('sight(s)')
      expect(c.get('[data-testid=repair-verified]').text()).toContain('checked by the validator')
      expect(c.find('button').text()).toBe('Apply this change')
    }
    expect(cards[0].get('[data-testid=repair-title]').text()).toContain('Opening hours unverified')
  })
  it('giving up a must-visit is flagged as such and is never the default or automatic', async () => {
    const w = mountIt()
    const card = w.get('[data-testid=repair-demote_must_visit]')
    expect(card.get('[data-testid=repair-warning]').text()).toContain('gives up something you required')
    expect(w.emitted('apply')).toBeUndefined()                      // nothing is applied without a click
    await card.get('button').trigger('click')
    expect(w.emitted('apply')[0]).toEqual([{ demote_must_visit: 'national_mosque_malaysia' }])
  })
  it('a repair the server did not verify is labelled "Not verified", not verified', () => {
    const w = mountIt(result([alt('add_day', [{ field: 'days', from: 2, to: 3 }], { verified_by_validator: false })]))
    expect(w.get('[data-testid=repair-unverified]').text()).toBe('Not verified'); expect(w.find('[data-testid=repair-verified]').exists()).toBe(false)
  })
  it('an empty or malformed repair list shows a clear empty state and never a blank item', () => {
    for (const alts of [[], [{ kind: 'x', message: '', details: {} }], [{ kind: 'y' }]]) {
      const w = mountIt(result(alts))
      expect(w.find('[data-testid=no-repair]').exists()).toBe(true)
      expect(w.findAll('[data-testid=alternatives] > li').length).toBe(0)
    }
  })
  it('repair views are never blank', () => {
    const v = repairViews(result([alt('allow_unknown_hours', []), { kind: 'q', message: '' }]), byId, String, String)
    expect(v.every((x) => x.title.trim().length > 0)).toBe(true)
  })
})

describe('the feasibility report', () => {
  const noPlan = { overall: 'fail', verification: 'none', blocked_by: 'missing_information', data_quality_warnings: [], summary: 'FAIL: blocked by missing information: the data does not say whether a required sight is open, so the planner cannot confirm a plan.',
    checks: [{ id: 'plan_exists', name: 'A valid plan exists', status: 'fail', message: 'Blocked by missing information: the data does not say whether a required sight is open, so the planner cannot confirm a plan.', stop_ids: [] }] }
  it('says the failure once and keeps the single check under technical details', () => {
    const w = mount(FeasibilityReport, { props: { report: noPlan } })
    expect(w.find('[data-testid=failed-checks]').exists()).toBe(false)
    const visible = w.get('[data-testid=report-summary]').text()
    expect(visible).toContain('missing information')
    expect(w.text().split('missing information').length - 1).toBeLessThanOrEqual(3)      // summary + the folded technical check, not four copies
    expect(w.get('details summary').text()).toBe('Technical details')
  })
  it('marks a conditional plan as not fully verified', () => {
    const w = mount(FeasibilityReport, { props: { report: { overall: 'pass_with_warnings', verification: 'conditional', conditional_stop_ids: ['x'], data_quality_warnings: [], summary: 'S', checks: [{ id: 'unknown_hours_used', name: 'Unknown opening hours', status: 'warning', message: 'm', stop_ids: ['x'] }] } } })
    expect(w.get('[data-testid=report-conditional]').text()).toContain('Check before you travel')
  })
})
