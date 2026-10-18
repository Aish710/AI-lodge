// "What the AI understood": plain rows built ONLY from the validated draft the server returned (never from raw model text).
import { formatLocalMoney, WEEKDAY_NAMES, WEEKDAYS } from './format.js'

/** Which form control changes each assumed default (ids in Plan.vue). */
const FIELD_OF_DEFAULT = [['budget', 'f-budget'], ['value of time', 'f-vot'], ['pace', 'f-pace'], ['day start', 'f-start'], ['day end', 'f-end']]

export function assumedList(defaults = []) {
  // a walking limit is not something the planner enforces, so it is never listed as a setting the AI "assumed"
  return defaults.filter((text) => !/^max walking/i.test(text)).map((text) => ({ text, field: FIELD_OF_DEFAULT.find(([k]) => text.toLowerCase().startsWith(k))?.[1] ?? null }))
}

const defaulted = (defaults, key) => defaults.some((d) => d.toLowerCase().startsWith(key))

/** One row per field the AI actually set (a field filled by a default is listed under "I assumed" instead). */
/** Fields the PLANNER really uses (so only these are listed as "Applied to the form"): days, budget, pace, value of time, must-see and not-interested places, the first day. */
export const PLANNER_FIELDS = ['days', 'budget', 'pace', 'vot', 'must', 'skip', 'weekday', 'nights']
export const FIELD_CONTROL = { days: 'f-days', budget: 'f-budget', pace: 'f-pace', vot: 'f-vot', must: 'sights-h', skip: 'sights-h', weekday: 'f-weekday', nights: 'f-nights' }

export function appliedRows(result, opts = {}) {
  return understoodRows(result, opts).filter((r) => PLANNER_FIELDS.includes(r.field))
}

export function understoodRows(result, { places = [], currency = 'JPY' } = {}) {
  const d = result?.draft
  if (!d) return []
  const defaults = result.defaults_applied ?? []
  const name = (id) => places.find((p) => p.id === id)?.name ?? id
  const rows = [{ field: 'days', label: 'Days', value: String(d.days) }]
  if (d.budget != null && !defaulted(defaults, 'budget')) rows.push({ field: 'budget', label: 'Budget', value: `${formatLocalMoney(d.budget, currency)}${d.strict_budget ? ' (strict)' : ' (soft target)'}` })
  if (!defaulted(defaults, 'pace')) rows.push({ field: 'pace', label: 'Pace', value: d.pace })
  if (d.value_of_time_per_hour != null && !defaulted(defaults, 'value of time') && !defaulted(defaults, 'value of time:') && result.extracted_json?.value_of_time != null) rows.push({ field: 'vot', label: 'Value of an hour of your time', value: formatLocalMoney(d.value_of_time_per_hour, currency) })
  if (d.must_visit?.length) rows.push({ field: 'must', label: 'Must visit', value: d.must_visit.map(name).join(', ') })
  if (d.skip?.length) rows.push({ field: 'skip', label: 'Not interested in', value: d.skip.map(name).join(', ') })
  if (d.interests?.length) rows.push({ field: 'interests', label: 'Interests (highlight only)', value: d.interests.join(', ') })
  if (d.nights != null) rows.push({ field: 'nights', label: 'Nights', value: String(d.nights) })
  if (d.start_weekday != null && result.draft && result.extracted_json?.start_weekday != null) rows.push({ field: 'weekday', label: 'First day', value: WEEKDAY_NAMES[WEEKDAYS[d.start_weekday]] ?? '' })
  return rows
}
