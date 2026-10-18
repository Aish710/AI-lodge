import { resultState } from './conflicts.js'
// Verdict-first helpers. Pure functions: the screens show what these return, and nothing is decided inline in a template.
import { cleanHotelText } from './names.js'

/** Status chip for a plan: icon + word + colour class (never colour alone). */
export function planStatus(resp) {
  const status = resp?.result?.status
  const overall = resp?.feasibility_report?.overall
  const st = resultState(resp)
  // Three different things: a plan that holds only if unverified hours are open, a plan blocked by information the data lacks, and a plan the known constraints rule out.
  if (st === 'blocked_missing_info') return { kind: 'warn', icon: '!', label: 'Blocked by missing information' }
  if (st === 'conditional') return { kind: 'warn', icon: '!', label: 'Feasible if opening hours are confirmed' }
  if (status === 'infeasible' || overall === 'fail') return { kind: 'bad', icon: '✕', label: 'Not possible' }
  if (overall === 'pass_with_warnings') return { kind: 'warn', icon: '!', label: 'Feasible with warnings' }
  return { kind: 'good', icon: '✓', label: 'Feasible' }
}

/** "n of n": how many of the validator's checks passed. */
export function checksTally(report) {
  const checks = report?.checks ?? []
  return { passed: checks.filter((c) => c.status === 'pass').length, total: checks.length }
}

/** "x of y": sights in the plan out of the sights the user did not rule out (not marked "not interested"). */
export function sightsCovered(scheduled, places, wishlist) {
  const wanted = (places ?? []).filter((p) => wishlist?.[p.id] !== 'skip').length
  return { scheduled, wanted }
}

/** The one headline for the hotel comparison. `fmt` formats an amount in the city's currency. */
export function hotelVerdict(comp, fmt) {
  if (!comp) return null
  if (!comp.best_by_true_cost) return { kind: 'bad', icon: '✕', headline: 'No hotel can host this trip', detail: 'See each hotel below for the conflict.' }
  const name = (id) => cleanHotelText(comp.results.find((r) => r.hotel_id === id)?.hotel_name ?? id)
  if (comp.cheapest_by_rate === comp.best_by_true_cost || !comp.cheapest_by_rate) {
    return { kind: 'good', icon: '✓', headline: 'The cheapest hotel is also the best for this trip', detail: `${name(comp.best_by_true_cost)} has the lowest nightly rate and the lowest true cost.` }
  }
  const gap = comp.ranking?.find((r) => r.hotel_id === comp.cheapest_by_rate)?.gap_to_winner_jpy
  const cheaper = Number.isFinite(gap) && gap > 0 ? `, ${fmt(gap)} cheaper overall` : ''
  return { kind: 'good', icon: '✓', headline: `Best value: ${name(comp.best_by_true_cost)}${cheaper}`, detail: `Compared with ${name(comp.cheapest_by_rate)}, which has the lowest nightly rate.` }
}

// Which warnings matter most: must-visit problems, then budget, then unknown data, then everything else.
export function warningRank(w) {
  const t = String(w).toLowerCase()
  if (/must[- ]?visit|required/.test(t)) return 0
  if (/budget|exceed/.test(t)) return 1
  if (/unknown|not known|placeholder|assum/.test(t)) return 2
  return 3
}

/** Split warnings into the 3 most important and the rest ("Show N more"). Nothing is dropped. Failures are never passed through here. */
export function topWarnings(list, limit = 3) {
  const ranked = [...(list ?? [])].map((w, i) => ({ w, i, r: warningRank(w) })).sort((a, b) => a.r - b.r || a.i - b.i).map((x) => x.w)
  return { shown: ranked.slice(0, limit), more: ranked.slice(limit) }
}
