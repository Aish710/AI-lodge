// Small, pure decision rules (unit-tested). The UI shows what these return; it never decides these things inline.
import { formatLocalMoney, WEEKDAYS, WEEKDAY_NAMES } from './format.js'

/**
 * Hotel callout (decision 2). The "cheapest rate is not the best value" message appears ONLY when the API says the rate winner
 * differs from the true-cost winner. Otherwise a neutral line. Nothing about any hotel is hard-coded.
 */
export function hotelCallout(comparison) {
  if (!comparison || comparison.best_by_true_cost == null) return { kind: 'none', text: '' }
  if (comparison.rate_winner_differs_from_true_winner === true) {
    return { kind: 'differs', text: 'Among these demo hotels, the cheapest rate is not the best overall for this trip.' }
  }
  return { kind: 'same', text: 'Among these demo hotels, the cheapest is also the best overall for this trip.' }
}

/** Not-scheduled panel (decision 3): every visitable optional sight that was skipped, as a visible decision. */
export function notScheduledItems(missedIds, placesById, penaltyJpy) {
  return (missedIds ?? []).map((id) => ({
    id,
    name: placesById[id]?.name ?? id,
    reason: 'Skipped because including it would cost more than it is worth for this plan.',
    penaltyJpy: penaltyJpy ?? null,
  }))
}

/** Which trip days is an attraction closed / of unknown hours, straight from the API's opening_hours. */
export function hoursWarnings(place, startWeekday, days) {
  const out = []
  for (let d = 1; d <= days; d++) {
    const wd = WEEKDAYS[(startWeekday + d - 1) % 7]
    const h = place.opening_hours?.[wd]
    if (h === null) out.push({ day: d, weekday: WEEKDAY_NAMES[wd], kind: 'closed' })
    else if (h === 'unknown') out.push({ day: d, weekday: WEEKDAY_NAMES[wd], kind: 'unknown' })
  }
  return out
}

/** Classify an /optimise (or replan schedule) response: HTTP 200 + status "infeasible" is a normal result, not an error. */
export function isInfeasible(resp) {
  return resp?.result?.status === 'infeasible'
}

/**
 * Turn the server's computed alternatives into actions: each is a patch to the preferences/wishlist that re-runs the request.
 * Alternatives we cannot map safely are returned with `patch: null` and shown as plain text (never as a button).
 */
/** Structured changes from a verified repair -> one patch (applied only when the user presses Apply). */
export function patchFromChanges(changes) {
  const patch = {}
  for (const c of changes ?? []) {
    if (c.field === 'days') patch.days = c.to
    else if (c.field === 'strict_budget') patch.strict_budget = c.to
    else if (c.field === 'allow_unknown_hours') patch.allow_unknown_hours = c.to
    else if (c.field === 'day_end') patch.day_end = c.to
    else if (c.field === 'max_activities_per_day') patch.max_activities_per_day = c.to
    else if (c.field === 'max_daily_travel_minutes') patch.max_daily_travel_minutes = c.to
    else if (c.field === 'pace') patch.pace = c.to
    else if (c.field === 'hotel') patch.hotel = c.to
    else if (c.field === 'must_visit' && c.removed) patch.demote_must_visit = c.removed
    else return null                         // a change we do not know how to apply is shown as text, never guessed
  }
  return Object.keys(patch).length ? patch : null
}

export function conflictActions(result, prefs, placesById) {
  return (result?.alternatives ?? []).map((a) => {
    const msg = typeof a.message === 'string' ? a.message : ''
    const base = { kind: a.kind, message: msg, patch: null, label: msg.replace(/: a feasible plan exists\.?$/, ''),
      rank: a.details?.rank ?? null, combination: a.details?.combination === true, verified: a.details?.verified_by_validator === true }
    if (a.details?.changes?.length) { const patch = patchFromChanges(a.details.changes); if (patch) return { ...base, patch } }
    if (a.kind === 'add_day') return { ...base, patch: { days: prefs.days + 1 } }
    if (a.kind === 'relax_budget') return { ...base, patch: { strict_budget: false } }
    if (a.kind === 'allow_unknown_hours') return { ...base, patch: { allow_unknown_hours: true } }
    if (a.kind === 'extend_day') {
      const m = /(\d{2}:\d{2})/.exec(msg)
      return m ? { ...base, patch: { day_end: m[1] } } : base
    }
    if (a.kind === 'demote_must_visit') {
      const hit = Object.values(placesById).find((p) => prefs.must_visit.includes(p.id) && msg.includes(`Treat ${p.name} as`))
      return hit ? { ...base, patch: { demote_must_visit: hit.id } } : base
    }
    return base
  })
}

export function checkIcon(status) {
  return { pass: '✓', warning: '!', fail: '✕' }[status] ?? '?'
}
export function checkLabel(status) {
  return { pass: 'Pass', warning: 'Warning', fail: 'Fail' }[status] ?? 'Unknown'
}
export function overallLabel(overall) {
  return { pass: 'Pass', pass_with_warnings: 'Pass with warnings', fail: 'Fail' }[overall] ?? 'Unknown'
}

const FLAG_TEXT = {
  opening_hours_unknown: 'Opening hours unknown',
  price_unknown: 'Price unknown (not in the total)',
  advance_booking_required: 'Advance booking required',
}
export const flagText = (f) => FLAG_TEXT[f] ?? f.replace(/_/g, ' ')

/** Explanation badge rule: AI text only when the API says source === "llm" (it passed the grounding check); everything else is a template. */
export function explanationBadge(explanation) {
  if (explanation?.source === 'llm' && explanation.cited) return { kind: 'llm', label: 'AI-written, every claim cited and checked' }
  return explanation?.source === 'llm'
    ? { kind: 'llm', label: 'AI-written, numbers checked' }
    : { kind: 'template', label: 'Code-written summary' }
}

/**
 * What the natural-language box should show for a /parse or /parse-replan response. `limitReached` comes from GET /health (the daily
 * AI limit), so it can be shown distinctly from an ordinary outage. llm_unavailable is calm and never an error.
 */
export function parseState(result, limitReached = false) {
  if (!result) return { kind: 'idle' }
  if (result.status === 'llm_unavailable') {
    return limitReached
      ? { kind: 'limit', message: 'The daily limit for the AI assistant has been reached, so it is switched off until it resets. Use the form below, everything else works.' }
      : { kind: 'unavailable', message: 'The AI assistant is unavailable right now. Use the form below, everything else works.' }
  }
  if (result.status === 'needs_clarification') return { kind: 'clarify' }
  return { kind: 'ok' }
}

/** Which list (must / skip) a name the user typed came from, read from what the model extracted. Used to place a chosen suggestion. */
export function originOf(input, extracted) {
  if (extracted?.skip_names?.includes(input)) return 'skip'
  return 'must'
}

/** Label for "Load example trip": it must disclose the high value of time the example uses (derived from the example data itself). */
export function exampleLabel(example, currency = 'JPY') {
  const vot = formatLocalMoney(Number(example.form.valueOfTime), currency)
  return { vot, text: `Load a ${example.city_name} example (high value of time, ${vot}/h)`,
    title: `This example uses a high value of time (${vot} an hour) to illustrate the hotel trade-off. It is not a typical trip.` }
}
