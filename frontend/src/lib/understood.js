// "What the AI understood": plain rows built ONLY from the validated draft the server returned (never from raw model text).
import { formatLocalMoney, WEEKDAY_NAMES, WEEKDAYS } from './format.js'

/** Which form control changes each assumed default (ids in Plan.vue). */
const FIELD_OF_DEFAULT = [['budget', 'f-budget'], ['value of time', 'f-vot'], ['pace', 'f-pace'], ['day start', 'f-start'], ['day end', 'f-end'], ['max walking', 'f-start']]

export function assumedList(defaults = []) {
  return defaults.map((text) => ({ text, field: FIELD_OF_DEFAULT.find(([k]) => text.toLowerCase().startsWith(k))?.[1] ?? null }))
}

const defaulted = (defaults, key) => defaults.some((d) => d.toLowerCase().startsWith(key))

/** One row per field the AI actually set (a field filled by a default is listed under "I assumed" instead). */
export function understoodRows(result, { places = [], currency = 'JPY' } = {}) {
  const d = result?.draft
  if (!d) return []
  const defaults = result.defaults_applied ?? []
  const name = (id) => places.find((p) => p.id === id)?.name ?? id
  const rows = [{ field: 'days', label: 'Days', value: String(d.days) }]
  if (d.budget != null && !defaulted(defaults, 'budget')) rows.push({ field: 'budget', label: 'Budget', value: `${formatLocalMoney(d.budget, currency)}${d.strict_budget ? ' (strict)' : ' (soft target)'}` })
  if (!defaulted(defaults, 'pace')) rows.push({ field: 'pace', label: 'Pace', value: d.pace })
  if (d.must_visit?.length) rows.push({ field: 'must', label: 'Must visit', value: d.must_visit.map(name).join(', ') })
  if (d.skip?.length) rows.push({ field: 'skip', label: 'Not interested in', value: d.skip.map(name).join(', ') })
  if (d.interests?.length) rows.push({ field: 'interests', label: 'Interests (highlight only)', value: d.interests.join(', ') })
  if (d.nights != null) rows.push({ field: 'nights', label: 'Nights', value: String(d.nights) })
  if (d.start_weekday != null && result.draft && result.extracted_json?.start_weekday != null) rows.push({ field: 'weekday', label: 'First day', value: WEEKDAY_NAMES[WEEKDAYS[d.start_weekday]] ?? '' })
  return rows
}
