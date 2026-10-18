// Plain-language views of what the planner returned when it could not plan. Pure functions over server data; nothing here decides feasibility.
// Raw reason codes and the server's technical sentences are kept for an expandable "Technical details" section and never shown as the headline.

export const MISSING_INFO_CODES = ['unknown_hours_not_allowed']

/** missing_information | known_constraints. The server sets `category`; the code is the fallback for older responses. */
export const categoryOf = (c) => c?.category ?? (MISSING_INFO_CODES.includes(c?.code) ? 'missing_information' : 'known_constraints')

/** feasible | conditional | blocked_missing_info | infeasible */
export function resultState(resp) {
  const r = resp?.result
  if (!r) return null
  if (r.status === 'feasible') return resp.feasibility_report?.verification === 'conditional' ? 'conditional' : 'feasible'
  const cs = r.conflicts ?? []
  return cs.length && cs.every((c) => categoryOf(c) === 'missing_information') ? 'blocked_missing_info' : 'infeasible'
}

const names = (c, byId) => (c.attraction_ids ?? []).map((id) => byId[id]?.name ?? id)
const list = (xs) => (xs.length <= 1 ? (xs[0] ?? '') : `${xs.slice(0, -1).join(', ')} and ${xs.at(-1)}`)

const TITLES = {
  unknown_hours_not_allowed: (n) => ({ title: `We don't know when ${list(n) || 'a must-visit sight'} is open`, body: 'The sample data has no opening hours for it. In strict mode the planner never assumes a place is open, so it cannot confirm a plan. This is missing information, not a finding that the visit is impossible.' }),
  closed_all_days: (n) => ({ title: `${list(n)} is closed on every day of your trip`, body: 'According to the sample data it is closed on all of the days you picked.' }),
  no_open_slot: (n) => ({ title: `No time slot fits ${list(n)}`, body: 'Given its opening hours and your day window there is no usable time on any trip day.' }),
  does_not_fit_day: (n) => ({ title: `${list(n)} does not fit in one day`, body: 'The visit plus the trip from and back to the hotel is longer than your day window.' }),
  daily_travel_limit: (n) => ({ title: `${list(n)} needs more estimated travel than your daily limit`, body: 'The estimated round trip from the hotel is above the daily travel limit you set.' }),
  pace_cap: () => ({ title: 'More must-visits than your activity limit allows', body: 'The activities per day you allow, times the number of days, is fewer than the sights you require.' }),
  not_enough_time: () => ({ title: 'Your must-visits need more time than the trip has', body: 'Even without waiting, the visits and travel are longer than the days available.' }),
  budget_too_low: () => ({ title: 'Your strict budget is below the known cost of your must-visits', body: 'Admissions plus the cheapest estimated transport already exceed it.' }),
  no_feasible_schedule: () => ({ title: 'Each request works alone, but not all together', body: 'No schedule satisfies opening hours, travel time, your limits, the budget and any locks at the same time.' }),
  solver_timeout: () => ({ title: 'The planner ran out of time', body: 'This is not a proof that no plan exists. Try again or relax something.' }),
  locked_not_possible: (n) => ({ title: `${list(n)} cannot happen at the time you locked`, body: 'The locked time conflicts with its opening hours or your day window.' }),
  locked_overlap: () => ({ title: 'Two locked stops cannot both happen', body: 'The travel between them does not fit between the locked times.' }),
}

/** One friendly entry per conflict: {title, body, category, code (technical), technical (the server's sentence)}. */
export function describeConflicts(conflicts, byId = {}) {
  return (conflicts ?? []).map((c) => {
    const f = TITLES[c.code]
    const n = names(c, byId)
    const t = f ? f(n) : { title: 'A requirement cannot be met', body: 'The planner could not satisfy all of your requirements together.' }
    return { ...t, category: categoryOf(c), code: c.code, technical: c.message }
  })
}

/** The one-line heading and the lead sentence for the whole result. */
export function headline(state) {
  if (state === 'blocked_missing_info') return { title: "We can't confirm a plan yet: some information is missing", lead: 'This is a result, not a fault. The sample data does not say when a required sight is open, so the planner will not assume it. Choose one of the next steps below.' }
  if (state === 'infeasible') return { title: 'No plan satisfies every requirement', lead: 'This is a result, not a fault: the planner checked and these requests cannot all be met together. Nothing was faked or dropped silently.' }
  return null
}

/** Effect text from numbers the server solved for this repair; empty fields are simply left out. */
function effect(d, money, mins) {
  const bits = []
  if (Number.isFinite(d?.attractions_scheduled)) bits.push(`${d.attractions_scheduled} sight(s) in the plan`)
  if (Number.isFinite(d?.travel_minutes)) bits.push(`${mins(d.travel_minutes)} estimated travel`)
  if (Number.isFinite(d?.total_jpy)) bits.push(`${money(d.total_jpy)} admissions and transport (est.)`)
  return bits.join(' · ')
}

const FIELD_TEXT = {
  allow_unknown_hours: (c) => (c.to ? 'Allow sights with unknown opening hours (each is labelled "Opening hours unverified")' : 'Do not allow unknown hours'),
  days: (c) => `Trip length: ${c.from} → ${c.to} days`,
  strict_budget: (c) => (c.to ? 'Treat the budget as strict' : 'Treat the budget as a soft target'),
  day_end: (c) => `Day ends at ${c.to} instead of ${c.from}`,
  max_activities_per_day: (c) => `Activities per day: ${c.from} → ${c.to}`,
  max_daily_travel_minutes: (c) => (c.to === null ? 'Remove the daily estimated-travel limit' : `Estimated travel per day: ${c.from} → ${c.to} min`),
  pace: (c) => `Pace: ${c.from} → ${c.to}`,
  hotel: (c) => 'Use a different hotel',
  must_visit: (c, byId) => `Stop treating ${byId[c.removed]?.name ?? 'a sight'} as a must-visit`,
}
const WHY = {
  allow_unknown_hours: 'The planner can then include sights whose opening hours the data does not give. The result is provisional: it holds only if they are open.',
  days: 'More days give the same sights more room.', day_end: 'A later finish gives more time in the day.', strict_budget: 'A soft budget lets the plan go over it.',
  max_activities_per_day: 'A higher limit lets more sights fit each day.', max_daily_travel_minutes: 'A looser travel limit allows longer days.', pace: 'A faster pace allows more activities a day.',
  hotel: 'Another hotel can change travel times.', must_visit: 'Giving up this requirement is the only change here that drops something you asked for.',
}

/** Cards for the repairs the server solved. Never blank: an option without a usable title or change is dropped. */
export function repairViews(result, byId, money, mins) {
  return (result?.alternatives ?? []).map((a, i) => {
    const changes = a.details?.changes ?? []
    const lines = changes.map((c) => (FIELD_TEXT[c.field] ? FIELD_TEXT[c.field](c, byId) : null)).filter(Boolean)
    const title = (lines.length ? lines.join(' and ') : (a.message ?? '').replace(/: a feasible plan exists\.?$/, '')).trim()
    const why = [...new Set(changes.map((c) => WHY[c.field]).filter(Boolean))].join(' ')
    return { key: `${a.kind}-${i}`, kind: a.kind, title, change: lines, why, verified: a.details?.verified_by_validator === true, combination: a.details?.combination === true,
      effect: effect(a.details, money, mins), rank: a.details?.rank ?? null, removesMust: changes.some((c) => c.field === 'must_visit') }
  }).filter((v) => v.title)
}
