// Replan logic, pure and unit-tested. Rules enforced here (the server enforces them again):
//  * edits are sent as /replan operations; the client never edits a schedule or computes a cost
//  * at most 20 operations per request
//  * confirm_remove_must_visit is true ONLY when the user explicitly confirmed in the dialog, and NEVER on the natural-language path
import daypart from './daypart.json'
import limits from './limits.json'
import { formatLocalMoney } from './format.js'

export const MAX_OPS = limits.max_replan_operations
export const DAY_PARTS = Object.fromEntries(Object.entries(daypart).filter(([k]) => k !== 'note'))
export const DAY_PART_LABELS = { morning: 'Morning', midday: 'Midday', afternoon: 'Afternoon', evening: 'Evening' }

const SLOT = new Set(['lock', 'move'])
/** Does queued op `a` make queued op `b` (same attraction) contradictory? Later operations win; the queue never holds a pair the server would reject. */
function clashes(a, b) {
  if (a.attraction_id !== b.attraction_id || !a.attraction_id) return false
  if (SLOT.has(a.op) && SLOT.has(b.op)) return true
  if (a.op === b.op) return true
  const kinds = new Set([a.op, b.op])
  return (kinds.has('remove') && (kinds.has('lock') || kinds.has('move') || kinds.has('unlock'))) || (kinds.has('unlock') && (kinds.has('lock') || kinds.has('move')))
}

/** Add an operation. Returns {queue, error}. A newer operation replaces any contradictory older one; one budget and one hotel switch only. */
export function addOp(queue, op) {
  const kept = queue.filter((q) => !(clashes(q, op) || (['change_budget', 'switch_hotel'].includes(op.op) && q.op === op.op)))
  if (kept.length >= MAX_OPS) return { queue, error: `You can queue at most ${MAX_OPS} changes at once. Apply or remove some first.` }
  return { queue: [...kept, { ...op }], error: null }
}
export function removeOpAt(queue, index) {
  return queue.filter((_, i) => i !== index)
}

export function describeOp(op, placesById, hotelsById, currency = 'JPY') {
  const name = (id) => placesById[id]?.name ?? id
  switch (op.op) {
    case 'lock': return `Lock ${name(op.attraction_id)} on day ${op.day} at ${op.start_time}`
    case 'move': return `Move ${name(op.attraction_id)} to day ${op.day} at ${op.start_time}`
    case 'unlock': return `Unlock ${name(op.attraction_id)}`
    case 'remove': return `Remove ${name(op.attraction_id)}`
    case 'change_budget': return op.budget === null || op.budget === undefined ? 'Remove the budget' : `Set the budget to ${formatLocalMoney(op.budget, currency)} (${op.strict ? 'strict limit' : 'soft target'})`
    case 'switch_hotel': return `Switch hotel to ${hotelsById[op.hotel_id]?.name ?? op.hotel_id}`
    default: return String(op.op)
  }
}

/** Ids of must-visits that the queue would remove. Non-empty => the confirmation dialog is required before anything is sent. */
export function mustVisitRemovals(queue, prefs) {
  const must = new Set(prefs?.must_visit ?? [])
  return queue.filter((o) => o.op === 'remove' && must.has(o.attraction_id)).map((o) => o.attraction_id)
}

/**
 * The ONLY place a /replan request body is shaped. `confirmed` must be the literal boolean true from the dialog's confirm button, and the
 * source must be the UI. Natural-language proposals carry operations only (see proposalToOps), so the flag cannot come from them.
 */
export function buildReplanArgs({ prefs, currentResult, queue, confirmed = false, source = 'ui' }) {
  return {
    prefs, currentResult, operations: queue.map((o) => ({ ...o })),
    options: { confirmRemoveMustVisit: source === 'ui' && confirmed === true && mustVisitRemovals(queue, prefs).length > 0 },
  }
}

/** A /parse-replan proposal -> operations to queue. Deliberately drops requires_confirmation and everything else: consent is the user's. */
export function proposalToOps(proposal, includeIdx = null) {
  const ops = proposal?.operations ?? []
  return ops.filter((_, i) => includeIdx === null || includeIdx.includes(i)).map((o) => ({ ...o }))
}

// ---- diff view model ----
const LINES = [['admissions_jpy', 'Admissions', 'jpy'], ['transport_jpy', 'Transport (estimated)', 'jpy'], ['rooms_jpy', 'Rooms', 'jpy'],
  ['time_cost_jpy', 'Travel time × value of time', 'jpy'], ['missed_penalty_jpy', 'Missed preferences', 'jpy'], ['true_cost_jpy', 'True cost', 'jpy'], ['travel_minutes', 'Travel time (h:mm)', 'min']]

export const isNotLikeForLike = (w) => /^Not like-for-like/i.test(w)

export function diffRows(diff) {
  return LINES.map(([key, label, unit]) => {
    const d = diff[key]
    const direction = d.delta > 0 ? 'up' : d.delta < 0 ? 'down' : 'same'
    return { key, label, unit, before: d.before, after: d.after, delta: d.delta, direction, glyph: { up: '▲', down: '▼', same: '=' }[direction],
      word: { up: 'increase', down: 'decrease', same: 'no change' }[direction], strong: key === 'true_cost_jpy' }
  })
}

/** A saving next to a "Not like-for-like" warning must carry that warning beside the number (never a bare saving). */
export function trueCostCaveat(diff) {
  const warning = (diff.warnings ?? []).find(isNotLikeForLike)
  const row = diffRows(diff).find((r) => r.key === 'true_cost_jpy')
  return warning ? { show: true, isSaving: row.delta < 0, warning } : { show: false, isSaving: row.delta < 0, warning: null }
}

export function outcomeKind(result) {
  if (!result) return 'none'
  return result.status === 'applied' ? 'applied' : 'unchanged'
}
