// "Rough preview" while choosing sights: computed in the browser from the sample data already loaded. No solver, no AI, no request.
// It is a floor for what the plan will contain, not a plan: the planner decides the real schedule, order and which optional sights fit.
import paceCaps from './pacecaps.json'
import { stateOf } from '../store.js'

/** Sights that are still in the running (everything except "Not interested"). */
export function chosenSights(store) {
  return (store.places ?? []).filter((p) => stateOf(p.id) !== 'skip')
}

export function roughPreview(store) {
  const places = store.places ?? []
  const must = places.filter((p) => stateOf(p.id) === 'must')
  const maybe = places.filter((p) => stateOf(p.id) === 'nice')
  const inRunning = [...must, ...maybe]
  const days = Math.max(1, Number(store.form.days) || 1)
  const capPerDay = paceCaps[store.form.pace] ?? 3
  const sum = (list) => list.reduce((n, p) => n + (Number.isFinite(p.admission_cost) ? p.admission_cost : 0), 0)
  const unknown = (list) => list.filter((p) => p.admission_cost === null || p.admission_cost === undefined).map((p) => p.name)
  const areas = [...new Set([...must, ...maybe].map((p) => p.area).filter(Boolean))]
  return {
    mustCount: must.length, maybeCount: maybe.length, total: inRunning.length,
    maxFit: capPerDay * days,                       // at this pace and number of days (same cap the planner enforces)
    mustAdmissions: sum(must), mustUnknown: unknown(must),
    allAdmissions: sum(inRunning), allUnknown: unknown(inRunning),
    areas, mustOverCap: must.length > capPerDay * days,
  }
}
