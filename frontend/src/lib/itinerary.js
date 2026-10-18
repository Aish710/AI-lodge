// Pure helpers for "Compare with my itinerary": editing the user's own days. No optimisation, no timing and no cost arithmetic here;
// the server places, validates and scores everything (/evaluate-itinerary).

export const MAX_PER_DAY = 8

/** Start from the sights the user chose, in the order they listed them, spread evenly over the trip days. */
export function seedDays(ids, days) {
  const n = Math.max(1, days)
  const out = Array.from({ length: n }, () => [])
  const per = Math.ceil(ids.length / n) || 1
  ids.forEach((id, i) => out[Math.min(Math.floor(i / per), n - 1)].push(id))
  return out
}

const clone = (d) => d.map((x) => [...x])

export function moveWithin(days, day, index, delta) {
  const j = index + delta
  if (j < 0 || j >= days[day].length) return days
  const out = clone(days)
  ;[out[day][index], out[day][j]] = [out[day][j], out[day][index]]
  return out
}

export function moveToDay(days, day, index, target) {
  if (target === day || target < 0 || target >= days.length || days[target].length >= MAX_PER_DAY) return days
  const out = clone(days)
  const [id] = out[day].splice(index, 1)
  out[target].push(id)
  return out
}

export function removeStop(days, day, index, mustIds = []) {
  if (mustIds.includes(days[day][index])) return days     // a must-visit is never removed silently
  const out = clone(days)
  out[day].splice(index, 1)
  return out
}

export function addStop(days, day, id) {
  if (!id || days.flat().includes(id) || days[day].length >= MAX_PER_DAY) return days
  const out = clone(days)
  out[day].push(id)
  return out
}

/** Sentences for the form, never a request. */
export function problems(days, mustIds) {
  const all = days.flat()
  const out = []
  if (!all.length) out.push('Add at least one attraction to your itinerary.')
  for (const m of mustIds) if (!all.includes(m)) out.push('Every must-visit needs a place in your itinerary.')
  return [...new Set(out)]
}

/** The arms exactly as the server returned them, labelled for display. Money and the score are kept apart. */
export function armRows(result) {
  return (result?.arms ?? []).map((a) => ({
    key: a.key, label: a.label, feasible: a.feasible, why: a.feasible ? null : (a.conflicts[0] ?? (a.failed_checks.length ? `Fails: ${a.failed_checks.join(', ')}` : 'No feasible plan')),
    sights: a.sights?.length ?? 0, omitted: a.omitted ?? [], minutes: a.travel_minutes ?? null,
    spend: a.breakdown ? a.breakdown.admissions_jpy + a.breakdown.transport_jpy : null, score: a.score_jpy ?? null,
  }))
}

/** Drag-and-drop move: take the stop at `from` and insert it at `to` (indices are into the days AS THEY ARE NOW). Returns the same array when nothing would change. Pure. */
export function moveStop(days, from, to) {
  if (!days[from.day] || days[from.day][from.index] === undefined || !days[to.day]) return days
  if (from.day !== to.day && days[to.day].length >= MAX_PER_DAY) return days
  const out = days.map((d) => [...d])
  const [id] = out[from.day].splice(from.index, 1)
  let at = Math.max(to.index, 0)                                  // a slot in the list AS IT WAS before the item was taken out
  if (from.day === to.day && from.index < at) at -= 1            // taking the item out shifted everything after it up by one
  at = Math.min(at, out[to.day].length)
  if (from.day === to.day && at === from.index) return days
  out[to.day].splice(at, 0, id)
  return out
}

/** Plain sentence announced to screen readers after a move. */
export function moveAnnouncement(name, days, id) {
  for (let d = 0; d < days.length; d++) { const i = days[d].indexOf(id); if (i >= 0) return `${name} is now day ${d + 1}, position ${i + 1} of ${days[d].length}.` }
  return `${name} was removed.`
}
