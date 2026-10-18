// Travel profiles: editable presets over settings the planner really enforces (pace, activities a day, estimated travel a day, value of an hour).
// A profile never touches must-visits, hotels, budgets or anything the planner cannot enforce. A value the user types is theirs: switching profile does not overwrite it.
import data from './profiles.json'

export const PROFILES = data.profiles
export const FIELDS = ['pace', 'maxActivities', 'maxDailyTravel', 'valueOfTime']
export const FIELD_LABEL = { pace: 'Pace', maxActivities: 'Activities a day', maxDailyTravel: 'Estimated travel a day (min)', valueOfTime: 'Value of an hour' }

export const emptyProfile = () => ({ id: null, applied: {}, user: {} })
const same = (a, b) => String(a) === String(b)

/** The values a profile proposes for this city. */
export function proposed(profile, cityDefaultVot) {
  return { pace: profile.pace, maxActivities: profile.maxActivities, maxDailyTravel: profile.maxDailyTravel, valueOfTime: Math.round((Number(cityDefaultVot) || 1000) * profile.votFactor) }
}

/** Choose a profile. Fields the user has set themselves keep their value; the rest take the profile's. Returns new copies (inputs are not mutated). */
export function applyProfile(form, state, profileId, cityDefaultVot) {
  const prof = PROFILES.find((p) => p.id === profileId)
  if (!prof) return { form, state }
  const want = proposed(prof, cityDefaultVot)
  const f = { ...form }, applied = {}
  for (const k of FIELDS) {
    if (state.user[k]) continue
    f[k] = want[k]; applied[k] = want[k]
  }
  return { form: f, state: { id: profileId, applied: { ...applied }, user: { ...state.user } } }
}

/** Notice edits made after a profile was applied: a field that no longer equals what the profile set is now the user's own. */
export function syncOverrides(form, state) {
  const user = { ...state.user }
  for (const k of FIELDS) if (k in state.applied && !same(form[k], state.applied[k])) user[k] = true
  return { ...state, user }
}

export function clearOverrides(state) { return { ...state, user: {} } }

export function profileName(state) {
  const p = PROFILES.find((x) => x.id === state.id)
  if (!p) return 'Not chosen'
  return Object.keys(state.user).length ? `${p.label} + your changes (custom)` : p.label
}

/** What the planner will actually use, and where each value came from. */
export function effective(form, state, cityDefaultVot) {
  const prof = PROFILES.find((x) => x.id === state.id)
  const want = prof ? proposed(prof, cityDefaultVot) : {}
  return FIELDS.map((k) => ({ field: k, label: FIELD_LABEL[k], value: form[k] === '' ? (k === 'maxActivities' ? 'pace decides' : 'no limit') : form[k],
    source: state.user[k] ? 'you' : k in state.applied ? 'profile' : 'default', profileWould: want[k] }))
}
