// Form + wishlist -> the Preferences object the API expects. The only place that builds request preferences.
export const DEFAULT_FORM = () => ({
  days: 3,
  budgetAmount: '',          // blank = no budget
  budgetCurrency: 'JPY',     // 'JPY' | 'SGD'
  strictBudget: false,
  pace: 'balanced',
  startWeekday: 2,           // Wednesday
  dayStart: '09:00',
  dayEnd: '19:00',
  valueOfTime: 1000,         // JPY per hour
  nightsOverride: false,
  nights: 2,
  allowUnknownHours: false,
  maxActivities: '',         // blank = use the pace preset's cap
  maxDailyTravel: '',        // blank = no limit; minutes of ESTIMATED travel per day
  minActiveDays: '',         // blank = no requirement; otherwise at least this many days must have an activity (a hard rule)
})

export function budgetInLocal(form, cityOrRate) {
  const raw = form.budgetAmount
  if (raw === '' || raw === null || raw === undefined) return null
  const n = Number(raw)
  if (!Number.isFinite(n) || n < 0) return NaN
  const local = cityOrRate?.currency_code ?? 'JPY'
  const display = cityOrRate?.display_currency_code ?? 'SGD'
  const rate = cityOrRate?.sample_fx_to_display_currency ?? (typeof cityOrRate === 'number' ? 1 / cityOrRate : null)
  if (form.budgetCurrency === local) return Math.round(n)
  if (form.budgetCurrency === display) return rate ? Math.round(n / rate) : NaN
  if (form.budgetCurrency === 'SGD' && local === 'JPY' && typeof cityOrRate === 'number') return Math.round(n * cityOrRate)
  return NaN
}
export const budgetInJpy = budgetInLocal

export function nightsUsed(form) {
  return form.nightsOverride ? Number(form.nights) : Number(form.days) - 1
}

/** Returns {prefs, errors}. Errors are plain sentences for the form. */
export function buildPreferences(form, wishlist, cityOrRate) {
  const errors = []
  const local = cityOrRate?.currency_code ?? 'JPY'
  const display = cityOrRate?.display_currency_code ?? 'SGD'
  const rate = cityOrRate?.sample_fx_to_display_currency ?? (typeof cityOrRate === 'number' ? 1 / cityOrRate : null)
  const days = Number(form.days)
  if (!Number.isInteger(days) || days < 1 || days > 7) errors.push('Trip length must be between 1 and 7 days.')
  if (form.dayEnd <= form.dayStart) errors.push('The day must end after it starts.')
  const budget = budgetInLocal(form, cityOrRate)
  if (Number.isNaN(budget) && form.budgetCurrency === display && !rate) errors.push(`The ${display} rate has not loaded yet.`)
  else if (Number.isNaN(budget)) errors.push('Budget must be a number of zero or more.')
  if (budget !== null && !Number.isNaN(budget) && ![local, display].includes(form.budgetCurrency)) errors.push(`Budget currency must be ${local} or ${display}.`)
  if (form.strictBudget && budget === null) errors.push('A strict budget needs an amount.')
  if (form.nightsOverride && !(Number.isInteger(Number(form.nights)) && form.nights >= 0 && form.nights <= 30)) errors.push('Nights must be a whole number from 0 to 30.')
  const act = form.maxActivities
  if (act !== '' && act !== null && act !== undefined && !(Number.isInteger(Number(act)) && Number(act) >= 1 && Number(act) <= 8)) errors.push('Maximum activities per day must be a whole number from 1 to 8.')
  const trv = form.maxDailyTravel
  if (trv !== '' && trv !== null && trv !== undefined && !(Number.isInteger(Number(trv)) && Number(trv) >= 20 && Number(trv) <= 720)) errors.push('Maximum estimated travel per day must be a whole number of minutes from 20 to 720.')
  const mad = form.minActiveDays
  if (mad !== '' && mad !== null && mad !== undefined && !(Number.isInteger(Number(mad)) && Number(mad) >= 1 && Number(mad) <= days)) errors.push('Minimum active days must be a whole number from 1 to the number of days.')
  const must = Object.keys(wishlist).filter((id) => wishlist[id] === 'must')
  const skip = Object.keys(wishlist).filter((id) => wishlist[id] === 'skip')
  const prefs = {
    days, budget: Number.isNaN(budget) ? null : budget, strict_budget: Boolean(form.strictBudget && budget !== null && !Number.isNaN(budget)),
    pace: form.pace, interests: [], must_visit: must, skip, day_start: form.dayStart, day_end: form.dayEnd,
    value_of_time_per_hour: Number(form.valueOfTime), max_walking_minutes_per_day: 90, start_weekday: Number(form.startWeekday),
    allow_unknown_hours: Boolean(form.allowUnknownHours), nights: form.nightsOverride ? Number(form.nights) : null, locked: [],
  }
  // Optional limits are sent only when set, so an unset form builds exactly the request it always did.
  if (act !== '' && act !== null && act !== undefined && !errors.length) prefs.max_activities_per_day = Number(act)
  if (trv !== '' && trv !== null && trv !== undefined && !errors.length) prefs.max_daily_travel_minutes = Number(trv)
  if (mad !== '' && mad !== null && mad !== undefined && !errors.length) prefs.min_active_days = Number(mad)
  return { prefs, errors }
}

/** Apply a conflict-action patch (from rules.conflictActions) to the form + wishlist. Returns new copies. */
export function applyPatch(form, wishlist, patch) {
  const f = { ...form }
  const w = { ...wishlist }
  if ('days' in patch) f.days = patch.days
  if ('strict_budget' in patch) f.strictBudget = patch.strict_budget
  if ('allow_unknown_hours' in patch) f.allowUnknownHours = patch.allow_unknown_hours
  if ('day_end' in patch) f.dayEnd = patch.day_end
  if ('demote_must_visit' in patch) w[patch.demote_must_visit] = 'nice'
  if ('max_activities_per_day' in patch) f.maxActivities = patch.max_activities_per_day === null ? '' : String(patch.max_activities_per_day)
  if ('max_daily_travel_minutes' in patch) f.maxDailyTravel = patch.max_daily_travel_minutes === null ? '' : String(patch.max_daily_travel_minutes)
  if ('pace' in patch) f.pace = patch.pace
  return { form: f, wishlist: w }
}

/** A /parse draft (a PROPOSAL) -> editable form + wishlist. Nothing is submitted; the user reviews and edits first. */
/** `localCurrency` is the city's own currency code: a draft budget is always in local units. */
export function formFromDraft(draft, base = DEFAULT_FORM(), localCurrency = 'JPY') {
  const form = { ...base, days: draft.days, strictBudget: Boolean(draft.strict_budget), pace: draft.pace, startWeekday: draft.start_weekday,
    dayStart: draft.day_start, dayEnd: draft.day_end, valueOfTime: draft.value_of_time_per_hour, allowUnknownHours: false,
    budgetAmount: draft.budget === null || draft.budget === undefined ? '' : String(draft.budget), budgetCurrency: localCurrency,
    nightsOverride: draft.nights !== null && draft.nights !== undefined, nights: draft.nights ?? Math.max(draft.days - 1, 0) }
  const wishlist = {}
  for (const id of draft.must_visit ?? []) wishlist[id] = 'must'
  for (const id of draft.skip ?? []) wishlist[id] = 'skip'
  return { form, wishlist }
}

/** After a server-applied repair: bring the form and the wishlist in line with the preferences that were really used, so Recalculate and the next edit start from them. Pure. */
export function formFromPrefs(form, wishlist, prefs) {
  const f = { ...form, pace: prefs.pace, dayEnd: prefs.day_end, valueOfTime: prefs.value_of_time_per_hour, allowUnknownHours: Boolean(prefs.allow_unknown_hours), strictBudget: Boolean(prefs.strict_budget),
    maxActivities: prefs.max_activities_per_day ?? '', maxDailyTravel: prefs.max_daily_travel_minutes ?? '', minActiveDays: prefs.min_active_days ?? '' }
  const w = { ...wishlist }
  for (const id of Object.keys(w)) if (w[id] === 'must' && !(prefs.must_visit ?? []).includes(id)) w[id] = 'nice'
  for (const id of prefs.must_visit ?? []) w[id] = 'must'
  for (const id of Object.keys(w)) if (w[id] === 'skip' && !(prefs.skip ?? []).includes(id)) w[id] = 'nice'
  for (const id of prefs.skip ?? []) w[id] = 'skip'
  return { form: f, wishlist: w }
}
