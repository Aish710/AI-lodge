import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mount } from '@vue/test-utils'
import benefits from '../../src/lib/benefits.json'
import BenefitStrip from '../../src/components/BenefitStrip.vue'
import { store } from '../../src/store.js'

const study = JSON.parse(readFileSync(resolve(process.cwd(), '..', 'docs', 'itinerary-study.json'), 'utf8'))

describe('benefit strip', () => {
  it('every number equals the generated itinerary study', () => {
    for (const [c, v] of Object.entries(study.cities)) {
      const m = v.summary.matched.input_order, b = benefits.cities[c]
      expect(b).toMatchObject({ trips: v.n_trips, input_order_feasible: v.summary.arms.input_order.feasible, optimiser_feasible: v.summary.arms.optimiser.feasible,
        matched_solved: m.matched_solved, minutes_better: m.minutes_saved.better, minutes_equal: m.minutes_saved.equal, minutes_worse: m.minutes_saved.worse })
    }
  })
  it('states ties and the sample-data caveat, and nothing about a specific traveller', () => {
    store.cityId = 'tokyo'; store.city = { display_name: 'Tokyo' }
    const w = mount(BenefitStrip, { global: { stubs: { 'router-link': { template: '<a><slot/></a>' } } } })
    const t = w.text()
    expect(t).toContain('the same in'); expect(t).toContain('not a prediction for your trip')
    expect(t).not.toMatch(/\bsave[sd]? you\b/i)
  })
})
