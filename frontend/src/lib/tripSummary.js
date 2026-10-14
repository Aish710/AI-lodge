import paceCaps from './pacecaps.json'
import { budgetInLocal, DEFAULT_FORM, nightsUsed } from './prefs.js'
import { formatDisplayMoney, formatLocalMoney, WEEKDAYS } from './format.js'

const PACE_LABELS = { relaxed: 'Relaxed', balanced: 'Balanced', packed: 'Packed' }
const PACE_CAP = paceCaps

export function formHasSettings(form) {
  const d = DEFAULT_FORM()
  return Object.keys(d).some((k) => form[k] !== d[k])
}

export function hasUnsavedWork(store) {
  return formHasSettings(store.form) || Object.keys(store.wishlist ?? {}).length > 0 || Boolean(store.chosenHotel || store.plan)
}

export function tripSummaryParts(store) {
  const form = store.form
  const city = store.city ?? {}
  const local = city.currency_code ?? 'JPY'
  const weekday = WEEKDAYS[Number(form.startWeekday)] ?? 'wed'
  const budget = budgetInLocal(form, city)
  const budgetText = budget === null || Number.isNaN(budget)
    ? 'no budget set'
    : `budget ${formatLocalMoney(budget, local)}${formatDisplayMoney(budget, city) !== 'unknown' ? ` (≈ ${formatDisplayMoney(budget, city)} at sample rate)` : ''}`
  const nights = nightsUsed(form)
  return [
    `${form.days} ${Number(form.days) === 1 ? 'day' : 'days'}`,
    `starts ${weekday[0].toUpperCase()}${weekday.slice(1)}`,
    `${form.dayStart}-${form.dayEnd}`,
    budgetText,
    PACE_LABELS[form.pace] ?? form.pace,
    `${formatLocalMoney(Number(form.valueOfTime), local)}/h`,
    `${nights} ${nights === 1 ? 'night' : 'nights'}${form.nightsOverride ? ' (custom)' : ''}`,
  ]
}

export function tripSummaryText(store) {
  return tripSummaryParts(store).join(' · ')
}

export function typicalDatasetTripCost(store) {
  const places = Array.isArray(store.places) ? store.places : []
  if (!places.length) return null
  const costs = places
    .map((p) => p.admission_cost)
    .filter((v) => Number.isFinite(v) && v >= 0)
    .sort((a, b) => a - b)
  if (!costs.length) return null
  const cap = Math.max(1, Math.min(places.length, (PACE_CAP[store.form.pace] ?? 3) * Number(store.form.days || 1)))
  const typicalAdmission = costs[Math.floor(costs.length / 2)]
  return typicalAdmission * cap
}

export function budgetSanityHint(store) {
  const budget = budgetInLocal(store.form, store.city)
  const typical = typicalDatasetTripCost(store)
  if (budget === null || Number.isNaN(budget) || !typical || typical <= 0) return ''
  return budget > typical * 20
    ? 'That budget is much higher than this trip is likely to cost. Did you mean a smaller number?'
    : ''
}
