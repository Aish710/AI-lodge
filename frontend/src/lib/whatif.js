// What-if scenarios: pure helpers. A scenario is a COPY of the current plan's preferences with a few named changes; the server optimises and validates it.
// Nothing here computes a plan, a cost or a travel time. `diffPlans` only subtracts numbers the server already returned and lines up stops by attraction id.

export const WHATIF_PACES = ['relaxed', 'balanced', 'packed']

export function draftFrom(prefs, hotel) {
  return { budget: prefs.budget ?? '', strict: Boolean(prefs.strict_budget), days: prefs.days, dayEnd: prefs.day_end, pace: prefs.pace,
    maxActivities: prefs.max_activities_per_day ?? '', maxDailyTravel: prefs.max_daily_travel_minutes ?? '', vot: prefs.value_of_time_per_hour,
    exclude: [], addMust: [], hotel }
}

const blank = (v) => v === '' || v === null || v === undefined

/** Returns {prefs, hotel, errors, changes}. `changes` lists, in words, only what differs from the current plan. */
export function buildScenario(base, baseHotel, d) {
  const errors = [], changes = []
  const prefs = { ...base }
  if (!Number.isInteger(Number(d.days)) || d.days < 1 || d.days > 7) errors.push('Days must be between 1 and 7.')
  else if (Number(d.days) !== base.days) { prefs.days = Number(d.days); changes.push(`${base.days} → ${d.days} days`) }
  if (d.dayEnd <= base.day_start) errors.push('The day must end after it starts.')
  else if (d.dayEnd !== base.day_end) { prefs.day_end = d.dayEnd; changes.push(`day ends at ${d.dayEnd}`) }
  if (d.pace !== base.pace) { prefs.pace = d.pace; changes.push(`${d.pace} pace`) }
  if (blank(d.budget)) { if (base.budget !== null) { prefs.budget = null; prefs.strict_budget = false; changes.push('no budget') } }
  else if (!(Number(d.budget) >= 0)) errors.push('Budget must be a number of zero or more.')
  else if (Number(d.budget) !== base.budget || Boolean(d.strict) !== Boolean(base.strict_budget)) { prefs.budget = Math.round(Number(d.budget)); prefs.strict_budget = Boolean(d.strict); changes.push(`budget ${prefs.budget}${d.strict ? ' (strict)' : ''}`) }
  const act = blank(d.maxActivities) ? null : Number(d.maxActivities)
  if (act !== null && !(Number.isInteger(act) && act >= 1 && act <= 8)) errors.push('Activities per day must be 1 to 8.')
  else if (act !== (base.max_activities_per_day ?? null)) { if (act === null) delete prefs.max_activities_per_day; else prefs.max_activities_per_day = act; changes.push(act === null ? 'pace sets the activity limit' : `at most ${act} activities a day`) }
  const trv = blank(d.maxDailyTravel) ? null : Number(d.maxDailyTravel)
  if (trv !== null && !(Number.isInteger(trv) && trv >= 20 && trv <= 720)) errors.push('Estimated travel per day must be 20 to 720 minutes.')
  else if (trv !== (base.max_daily_travel_minutes ?? null)) { if (trv === null) delete prefs.max_daily_travel_minutes; else prefs.max_daily_travel_minutes = trv; changes.push(trv === null ? 'no daily travel limit' : `at most ${trv} min estimated travel a day`) }
  if (!(Number(d.vot) >= 0)) errors.push('Value of time must be zero or more.')
  else if (Number(d.vot) !== base.value_of_time_per_hour) { prefs.value_of_time_per_hour = Number(d.vot); changes.push('different value of an hour') }
  if (d.exclude.length) {
    prefs.skip = [...new Set([...(base.skip ?? []), ...d.exclude])]
    prefs.must_visit = base.must_visit.filter((x) => !d.exclude.includes(x))
    prefs.locked = (base.locked ?? []).filter((l) => !d.exclude.includes(l.attraction_id))
    changes.push(`leave out ${d.exclude.length} sight(s)`)
  }
  if (d.addMust.length) {
    prefs.must_visit = [...new Set([...prefs.must_visit, ...d.addMust])]
    prefs.skip = (prefs.skip ?? base.skip ?? []).filter((x) => !d.addMust.includes(x))
    changes.push(`add ${d.addMust.length} must-visit(s)`)
  }
  const hotel = d.hotel || baseHotel
  if (hotel !== baseHotel) changes.push('another hotel')
  return { prefs, hotel, errors, changes }
}

const stopsOf = (resp) => Object.fromEntries((resp?.result?.days ?? []).flatMap((d) => d.stops.map((s) => [s.attraction_id, { day: d.day, start: s.start }])))
const trip = (resp) => resp?.cost_summary?.trip ?? null

/** Before/after of two server responses. Differences are plain subtraction of server numbers; sights are matched by id. */
export function diffPlans(before, after) {
  const a = stopsOf(before), b = stopsOf(after)
  const added = Object.keys(b).filter((id) => !(id in a))
  const removed = Object.keys(a).filter((id) => !(id in b))
  const moved = Object.keys(a).filter((id) => id in b && (a[id].day !== b[id].day))
  const ta = trip(before), tb = trip(after)
  const d = (x, y) => (x === null || y === null || x === undefined || y === undefined ? null : y - x)
  const sameSights = !added.length && !removed.length
  return { added, removed, moved, sameSights,
    money: d(ta?.cash_total_with_rooms, tb?.cash_total_with_rooms), minutes: d(ta?.travel_minutes, tb?.travel_minutes), sights: Object.keys(b).length - Object.keys(a).length,
    note: sameSights ? null : 'The two plans visit different sights, so a difference in travel time or spending is not a like-for-like saving.' }
}
