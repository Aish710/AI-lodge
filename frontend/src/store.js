// App state: a plain reactive module (no Pinia: the state is small and this keeps dependencies minimal).
// Everything lives in memory only: nothing is persisted by the browser (decision 10).
import { reactive, computed } from 'vue'
import * as api from './api/routes.js'
import { abortKey, ApiError, isAborted, setRateLimitHandler, waitForServer } from './api/client.js'
import { applyPatch, buildPreferences, DEFAULT_FORM } from './lib/prefs.js'
import examples from './lib/examples.json'

export const store = reactive({
  server: 'checking',            // checking | waking | ready | down
  serverError: null,
  health: null,                  // GET /health
  places: null, placesById: {}, hotelsById: {}, fx: null, placesSource: null, placesError: null,
  form: DEFAULT_FORM(),
  wishlist: {},                  // attraction id -> 'must' | 'nice' | 'skip'  (absent = nice)
  hotelIds: [],
  comparison: null, comparisonError: null, comparisonKey: null,
  chosenHotel: null,
  plan: null, planPrefs: null, planKey: null, planError: null,
  busy: { compare: false, sensitivity: false, optimise: false },
  sensitivityError: null,
  rateLimitUntil: 0, now: Date.now(),
})

// ---- rate limit countdown (decision 9) ----
let ticker = null
setRateLimitHandler((seconds) => {
  store.rateLimitUntil = Date.now() + seconds * 1000
  store.now = Date.now()
  if (!ticker) {
    ticker = setInterval(() => {
      store.now = Date.now()
      if (store.now >= store.rateLimitUntil) { clearInterval(ticker); ticker = null }
    }, 500)
  }
})
export const rateLimited = computed(() => store.rateLimitUntil > store.now)
export const rateLimitSeconds = computed(() => Math.max(0, Math.ceil((store.rateLimitUntil - store.now) / 1000)))

// ---- boot: cold-start aware (decision 9) ----
export async function boot({ ping } = {}) {
  store.server = 'checking'
  store.serverError = null
  try {
    const { health } = await waitForServer({ onWaking: () => { if (store.server === 'checking') store.server = 'waking' }, ...(ping ? { ping } : {}) })
    store.health = health
    store.server = 'ready'
  } catch (e) {
    if (isAborted(e)) return
    store.server = 'down'
    store.serverError = e
    return
  }
  await loadPlaces()
}

export async function refreshHealth() {
  try { store.health = await api.getHealth() } catch (e) { if (!isAborted(e)) store.health = null }
}

export async function loadPlaces() {
  store.placesError = null
  try {
    const d = await api.getPlaces()
    store.places = d.attractions
    store.placesById = Object.fromEntries(d.attractions.map((a) => [a.id, a]))
    store.hotelsById = Object.fromEntries(d.hotels.map((h) => [h.id, h]))
    store.fx = d.fx
    store.placesSource = { travel: d.travel_times_source, disclaimer: d.disclaimer }
  } catch (e) {
    if (!isAborted(e)) store.placesError = e
  }
}

// ---- trip input ----
export const stateOf = (id) => store.wishlist[id] ?? 'nice'
export function setWish(id, state) {
  if (state === 'nice') delete store.wishlist[id]
  else store.wishlist[id] = state
}

export function currentPrefs() {
  return buildPreferences(store.form, store.wishlist, store.fx?.jpy_per_sgd)
}

const keyOf = (prefs, extra) => JSON.stringify([prefs, extra])
const fail = (slot, e) => { if (!isAborted(e)) store[slot] = e instanceof ApiError ? e : new ApiError({ code: 'unexpected', message: 'Something unexpected went wrong.' }) }

// ---- hotel comparison ----
export async function runCompare() {
  const { prefs, errors } = currentPrefs()
  if (errors.length) { store.comparisonError = new ApiError({ code: 'invalid_input', message: errors.join(' ') }); return }
  if (store.hotelIds.length < 2 || store.hotelIds.length > 3) { store.comparisonError = new ApiError({ code: 'invalid_input', message: 'Choose two or three hotels to compare.' }); return }
  const ids = [...store.hotelIds]
  const key = keyOf(prefs, ids)
  abortKey('compare-sens')
  store.busy.compare = true
  store.busy.sensitivity = false
  store.comparisonError = null
  store.sensitivityError = null
  // Step 1: the fast comparison, so the table appears quickly.
  try {
    store.comparison = await api.compareHotels(prefs, ids, { sensitivity: false })
    store.comparisonKey = key
  } catch (e) { fail('comparisonError', e); return } finally { store.busy.compare = false }
  // Step 2: the same comparison plus the value-of-time sensitivity (the slow part). It supersedes step 1 only if the inputs have not changed.
  store.busy.sensitivity = true
  try {
    const full = await api.compareHotels(prefs, ids, { sensitivity: true })
    if (store.comparisonKey === key) store.comparison = full
  } catch (e) { if (!isAborted(e)) store.sensitivityError = e instanceof ApiError ? e : new ApiError({ code: 'unexpected', message: 'Something unexpected went wrong.' }) }
  finally { store.busy.sensitivity = false }
}

/** Run the comparison only if the inputs changed (keeps navigation cheap against the rate limit). */
export async function ensureComparison() {
  const { prefs, errors } = currentPrefs()
  if (errors.length || store.hotelIds.length < 2) return
  if (store.comparison && store.comparisonKey === keyOf(prefs, store.hotelIds)) return
  await runCompare()
}

// ---- itinerary ----
export async function runOptimise() {
  const { prefs, errors } = currentPrefs()
  if (!store.chosenHotel) { store.planError = new ApiError({ code: 'invalid_input', message: 'Choose a hotel first.' }); return }
  if (errors.length) { store.planError = new ApiError({ code: 'invalid_input', message: errors.join(' ') }); return }
  store.busy.optimise = true
  store.planError = null
  try {
    const resp = await api.optimise(prefs, store.chosenHotel)
    store.plan = resp
    store.planPrefs = prefs
    store.planKey = keyOf(prefs, store.chosenHotel)
  } catch (e) { fail('planError', e) } finally { store.busy.optimise = false }
}

/** Run /optimise only if the inputs changed since the last plan (avoids burning the rate limit when navigating back and forth). */
export async function ensurePlan() {
  const { prefs } = currentPrefs()
  if (store.plan && store.planKey === keyOf(prefs, store.chosenHotel)) return
  await runOptimise()
}

export function chooseHotel(id) { store.chosenHotel = id }

/** A conflict action (decision 4): apply the patch to the inputs, then re-run the same request. */
export async function applyAlternative(patch) {
  const next = applyPatch(store.form, store.wishlist, patch)
  store.form = next.form
  store.wishlist = next.wishlist
  await runOptimise()
}

// ---- demo helpers (decision: pre-tested requests, see tests) ----
export function loadExample(kind) {
  const ex = examples[kind]
  store.form = { ...DEFAULT_FORM(), ...ex.form }
  store.wishlist = { ...ex.wishlist }
  store.hotelIds = [...ex.hotel_ids]
  store.chosenHotel = ex.hotel_id
  store.comparison = null
  store.plan = null
  store.planKey = null
  store.planError = null
  store.comparisonError = null
}

export function resetAll() {
  store.form = DEFAULT_FORM()
  store.wishlist = {}
  store.hotelIds = []
  store.comparison = null
  store.chosenHotel = null
  store.plan = null
  store.planKey = null
  store.planError = null
  store.comparisonError = null
}
