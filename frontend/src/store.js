// App state: a plain reactive module (no Pinia: the state is small and this keeps dependencies minimal).
// Everything lives in memory only: nothing is persisted by the browser (decision 10).
import { reactive, computed } from 'vue'
import * as api from './api/routes.js'
import { abortKey, ApiError, isAborted, setCityProvider, setRateLimitHandler, waitForServer } from './api/client.js'
import { cleanHotelText, clearedOnCitySwitch } from './lib/names.js'
import { setSupportedCurrencies } from './lib/format.js'
import { applyPatch, buildPreferences, DEFAULT_FORM, formFromDraft } from './lib/prefs.js'
import { addOp, buildReplanArgs, proposalToOps, removeOpAt } from './lib/replan.js'
import limits from './lib/limits.json'
import examples from './lib/examples.json'
import { interestsToThemes } from './lib/themes.js'

export const store = reactive({
  server: 'checking',            // checking | waking | ready | down
  serverError: null,
  health: null,                  // GET /health
  cities: [], cityId: 'tokyo', city: null, cityError: null,
  places: null, placesById: {}, hotelsById: {}, fx: null, placesSource: null, placesError: null,
  form: DEFAULT_FORM(),
  wishlist: {},                  // attraction id -> 'must' | 'nice' | 'skip'  (absent = nice)
  hotelIds: [],
  comparison: null, comparisonError: null, comparisonKey: null,
  chosenHotel: null,
  plan: null, planPrefs: null, planKey: null, planError: null,
  busy: { compare: false, sensitivity: false, optimise: false, replan: false, parse: false, proposal: false },
  sensitivityError: null, sensitivityCancelled: false, sensitivityStartedAt: 0,
  planFromReplan: false,
  queue: [], queueError: null, previous: null, lastReplan: null, lastReplanRequest: null, replanError: null, restored: false,
  parseResult: null, parseError: null, proposal: null, proposalError: null,
  explanations: { optimise: null, compare: null, replan: null }, explainError: null, explaining: null,
  rateLimitUntil: 0, now: Date.now(),
  theme: 'all',                  // the chosen theme tab on the Plan screen (UI only)
  interestThemes: [], parsedInterests: [],   // interests that only HIGHLIGHT sights (UI only; the planner uses Must / Include / Skip)
  selectedDay: 'all',            // the day chip on Your trip: 'all' or a day number (UI only)
  stage: null,                   // 'comparing' | 'planning' while the Plan-my-trip chain or a hotel switch runs
  comparisonPrefs: null, pendingHotel: null, solverBusyUntil: 0,
  pendingCity: null,             // a city the user asked to switch to; the confirmation dialog (App.vue) lists what will be cleared
})

// ---- the selected city is ONE value (store.cityId); the API client discards any response that names a different city ----
setCityProvider(() => store.cityId)

// ---- rate limit countdown (decision 9) and solver-busy countdown: one shared clock ----
let ticker = null
function startClock() {
  store.now = Date.now()
  if (ticker) return
  ticker = setInterval(() => {
    store.now = Date.now()
    if (store.now >= store.rateLimitUntil && store.now >= store.solverBusyUntil) { clearInterval(ticker); ticker = null }
  }, 500)
}
setRateLimitHandler((seconds) => {
  store.rateLimitUntil = Date.now() + seconds * 1000
  startClock()
})
export const rateLimited = computed(() => store.rateLimitUntil > store.now)
export const rateLimitSeconds = computed(() => Math.max(0, Math.ceil((store.rateLimitUntil - store.now) / 1000)))
export const solverBusyActive = computed(() => store.solverBusyUntil > store.now)
export const solverBusySeconds = computed(() => Math.max(0, Math.ceil((store.solverBusyUntil - store.now) / 1000)))
/** The server's single solver slot is taken (503 solver_busy): remember until when, so the screen can count down. Nothing is retried automatically. */
export function noteSolverBusy(err) {
  if (err?.code !== 'solver_busy') return
  store.solverBusyUntil = Date.now() + (err.retryAfter ?? err.details?.retry_after_seconds ?? 5) * 1000
  startClock()
}
/** True while this tab has a solver request in flight. Every solver action is disabled meanwhile: one tab never has two solves running. */
export const highlightThemes = computed(() => new Set([...store.interestThemes, ...interestsToThemes(store.parsedInterests)]))
export function toggleInterestTheme(id) {
  const i = store.interestThemes.indexOf(id)
  if (i >= 0) store.interestThemes.splice(i, 1)
  else store.interestThemes.push(id)
}
export const solverBusy = computed(() => store.busy.compare || store.busy.optimise || store.busy.replan || store.busy.sensitivity)

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
  await loadCities()
  await loadPlaces()
}

export async function refreshHealth() {
  try { store.health = await api.getHealth() } catch (e) { if (!isAborted(e)) store.health = null }
}

export async function loadCities() {
  store.cityError = null
  try {
    const d = await api.getCities()
    store.cities = d.cities
    setSupportedCurrencies(d.cities.map((c) => c.currency_code))  // the symbol rule needs every supported city's currency
    store.city = d.cities.find((c) => c.id === store.cityId) ?? d.cities.find((c) => c.id === 'tokyo') ?? d.cities[0] ?? null
    if (store.city && store.city.id !== store.cityId) store.cityId = store.city.id
  } catch (e) {
    if (!isAborted(e)) store.cityError = e
  }
}

export async function loadPlaces() {
  store.placesError = null
  store.places = null
  try {
    const d = await api.getPlaces(store.cityId)
    store.places = d.attractions
    store.placesById = Object.fromEntries(d.attractions.map((a) => [a.id, a]))
    store.hotelsById = Object.fromEntries(d.hotels.map((h) => [h.id, { ...h, name: cleanHotelText(h.name) }]))
    store.city = { ...(store.city ?? {}), ...(d.city ?? {}), sample_fx_to_display_currency: d.display_fx?.rate ?? store.city?.sample_fx_to_display_currency }
    store.fx = { ...(d.fx ?? {}), ...(d.display_fx ?? {}), currency_code: d.city?.currency_code, display_currency_code: d.display_fx?.currency_code }
    store.placesSource = { travel: d.travel_times_source, disclaimer: d.disclaimer }
  } catch (e) {
    if (!isAborted(e)) store.placesError = e
  }
}

/** Abort every request that could still answer for the previous city. */
function abortAllInFlight() {
  for (const k of ['places', 'compare', 'compare-sens', 'optimise', 'replan', 'parse', 'parse-replan', 'summary']) abortKey(k)
}

function clearComputedResults() {
  abortAllInFlight()
  store.comparison = null
  store.comparisonKey = null
  store.comparisonError = null
  store.sensitivityError = null
  store.chosenHotel = null
  store.plan = null
  store.planPrefs = null
  store.planKey = null
  store.planError = null
  store.hotelIds = []
  store.parseResult = null
  store.parseError = null
  store.proposal = null
  store.proposalError = null
  store.explanations = { optimise: null, compare: null, replan: null }
  store.explainError = null
  store.explaining = null
  store.sensitivityCancelled = false
  store.planFromReplan = false
  store.stage = null
  store.selectedDay = 'all'
  store.comparisonPrefs = null
  store.pendingHotel = null
  store.solverBusyUntil = 0
  resetReplanState()
}

export async function selectCity(cityId) {
  if (cityId === store.cityId) return
  abortAllInFlight()
  store.cityId = cityId
  store.city = store.cities.find((c) => c.id === cityId) ?? null
  store.places = null
  store.form = { ...DEFAULT_FORM(), budgetCurrency: store.city?.currency_code ?? 'JPY',
    valueOfTime: store.city?.id === 'seoul' ? 15000 : store.city?.id === 'singapore' ? 18 : store.city?.id === 'kuala_lumpur' ? 45 : 1000 }
  store.wishlist = {}
  store.theme = 'all'
  store.interestThemes = []
  store.parsedInterests = []
  store.placesById = {}
  store.hotelsById = {}
  clearComputedResults()
  await loadPlaces()
}

/** The ONLY way a screen asks for another city. It never switches by itself when there is work to lose: it opens the confirmation. */
export async function requestCitySwitch(cityId) {
  if (cityId === store.cityId) return
  if (clearedOnCitySwitch(store).length) { store.pendingCity = cityId; return }
  await selectCity(cityId)
}

// ---- trip input ----
export const stateOf = (id) => store.wishlist[id] ?? 'nice'
export function setWish(id, state) {
  if (state === 'nice') delete store.wishlist[id]
  else store.wishlist[id] = state
}

export function currentPrefs() {
  return buildPreferences(store.form, store.wishlist, store.city ?? store.fx?.jpy_per_sgd)
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
  store.sensitivityCancelled = false
  store.busy.compare = true
  store.busy.sensitivity = false
  store.comparisonError = null
  store.sensitivityError = null
  // Step 1: the fast comparison, so the table appears quickly.
  try {
    store.comparison = await api.compareHotels(prefs, ids, { sensitivity: false, cityId: store.cityId })
    store.comparisonKey = key
  } catch (e) { fail('comparisonError', e); return } finally { store.busy.compare = false }
  // Step 2: the same comparison plus the value-of-time sensitivity (the slow part). It supersedes step 1 only if the inputs have not changed.
  store.busy.sensitivity = true
  store.sensitivityCancelled = false
  store.sensitivityStartedAt = Date.now()
  try {
    const full = await api.compareHotels(prefs, ids, { sensitivity: true, cityId: store.cityId })
    if (store.comparisonKey === key) store.comparison = full
  } catch (e) { if (!isAborted(e)) store.sensitivityError = e instanceof ApiError ? e : new ApiError({ code: 'unexpected', message: 'Something unexpected went wrong.' }) }
  finally { store.busy.sensitivity = false }
}

/** Stop waiting for the slow value-of-time analysis. The comparison table already on screen stays valid. */
export function cancelSensitivity() {
  store.sensitivityCancelled = true
  abortKey('compare-sens')
}

/** Run the comparison only if the inputs changed (keeps navigation cheap against the rate limit). */
export async function ensureComparison() {
  const { prefs, errors } = currentPrefs()
  if (errors.length || store.hotelIds.length < 2) return
  if (store.comparison && store.comparisonKey === keyOf(prefs, store.hotelIds)) return
  await runCompare()
}

// ---- itinerary ----
export async function runOptimise(hotelId = store.chosenHotel) {
  const { prefs, errors } = currentPrefs()
  if (!hotelId) { store.planError = new ApiError({ code: 'invalid_input', message: 'Choose a hotel first.' }); return }
  if (errors.length) { store.planError = new ApiError({ code: 'invalid_input', message: errors.join(' ') }); return }
  store.busy.optimise = true
  store.planError = null
  try {
    const resp = await api.optimise(prefs, hotelId, { cityId: store.cityId })
    store.plan = resp
    store.planPrefs = prefs
    store.chosenHotel = hotelId           // the hotel and the plan change together; a failed request leaves both as they were
    store.planKey = keyOf(prefs, hotelId)
    if (store.selectedDay !== 'all' && store.selectedDay > resp.result.days.length) store.selectedDay = 'all'
    store.planFromReplan = false
    resetReplanState()
  } catch (e) { fail('planError', e); noteSolverBusy(store.planError) } finally { store.busy.optimise = false }
}

// ---- one action: "Plan my trip" (hotel comparison, then the itinerary), strictly one solver request at a time ----
let chainId = 0
/** Hotels to compare: the user's own selection if they made one (2 or 3), otherwise the first three the dataset lists (the API compares at most 3). */
function hotelsToCompare() {
  const own = store.hotelIds.filter((id) => store.hotelsById[id])
  if (own.length >= 2) return own.slice(0, 3)
  return Object.keys(store.hotelsById).slice(0, 3)
}

/**
 * Compare hotels (fast, no sensitivity), pre-select the best value, plan that hotel. Resolves true when a plan was produced.
 * Nothing is replaced until the new plan arrives: a failure (busy, rate limit, timeout) keeps the last good plan and comparison on screen.
 */
export async function planMyTrip() {
  if (solverBusy.value || rateLimited.value) return false
  const { prefs, errors } = currentPrefs()
  if (errors.length) { store.planError = new ApiError({ code: 'invalid_input', message: errors.join(' ') }); return false }
  const ids = hotelsToCompare()
  if (ids.length < 2) { store.planError = new ApiError({ code: 'invalid_input', message: 'This city needs at least two hotels to compare.' }); return false }
  const mine = ++chainId
  store.planError = null
  store.comparisonError = null
  store.solverBusyUntil = 0
  store.pendingHotel = null
  store.stage = 'comparing'
  store.busy.compare = true
  let comp
  try {
    comp = await api.compareHotels(prefs, ids, { sensitivity: false, cityId: store.cityId })
  } catch (e) {
    fail('comparisonError', e); noteSolverBusy(store.comparisonError)
    if (mine === chainId) store.stage = null
    return false
  } finally { store.busy.compare = false }
  if (mine !== chainId) return false     // cancelled meanwhile
  const best = comp.best_by_true_cost ?? comp.results?.find((r) => r.feasible)?.hotel_id ?? ids[0]
  store.stage = 'planning'
  await runOptimise(best)
  if (mine !== chainId) return false     // cancelled while planning: keep the last good result, commit nothing
  store.stage = null
  if (store.planError) return false
  store.comparison = comp
  store.comparisonKey = keyOf(prefs, ids)
  store.comparisonPrefs = prefs
  store.hotelIds = ids
  store.sensitivityError = null
  store.sensitivityCancelled = false
  return true
}

/** Stop waiting for a plan. The requests are aborted (the server stops solving when the connection closes) and the last good result stays. */
export function cancelPlanning() {
  chainId += 1
  abortKey('compare'); abortKey('optimise')
  store.stage = null
  store.busy.compare = false
  store.busy.optimise = false
}

/** Switch the plan to another compared hotel, in place: the current plan stays on screen (dimmed) until the new one arrives. */
export async function switchHotel(id) {
  if (solverBusy.value || rateLimited.value || id === store.chosenHotel) return
  store.pendingHotel = id
  store.stage = 'planning'
  await runOptimise(id)
  store.stage = null
  if (!store.planError) store.pendingHotel = null
}

/** The value-of-an-hour analysis. ONLY ever called from an explicit click: it holds the solver slot for several seconds. */
export async function runSensitivity() {
  if (solverBusy.value || rateLimited.value || !store.comparison || !store.comparisonPrefs) return
  const ids = [...store.hotelIds]
  store.busy.sensitivity = true
  store.sensitivityCancelled = false
  store.sensitivityError = null
  store.sensitivityStartedAt = Date.now()
  try {
    const full = await api.compareHotels(store.comparisonPrefs, ids, { sensitivity: true, cityId: store.cityId })
    if (store.comparisonKey === keyOf(store.comparisonPrefs, ids)) store.comparison = full
  } catch (e) {
    if (!isAborted(e)) { store.sensitivityError = e instanceof ApiError ? e : new ApiError({ code: 'unexpected', message: 'Something unexpected went wrong.' }); noteSolverBusy(store.sensitivityError) }
  } finally { store.busy.sensitivity = false }
}

/** Run /optimise only if the inputs changed since the last plan (avoids burning the rate limit when navigating back and forth). */
export async function ensurePlan() {
  const { prefs } = currentPrefs()
  if (store.plan && store.planFromReplan) return // a server-replanned plan is kept until the user recalculates or picks another hotel
  if (store.plan && store.planKey === keyOf(prefs, store.chosenHotel)) return
  await runOptimise()
}

export function chooseHotel(id) {
  if (id !== store.chosenHotel) store.planFromReplan = false
  store.chosenHotel = id
}

/** A conflict action (decision 4): apply the patch to the inputs, then re-run the same request. */
export async function applyAlternative(patch) {
  const next = applyPatch(store.form, store.wishlist, patch)
  store.form = next.form
  store.wishlist = next.wishlist
  await runOptimise()
}

// ---- demo helpers (decision: pre-tested requests, see tests) ----
export const currentCityExamples = computed(() => examples[store.cityId] ?? examples.tokyo)

export function loadExample(kind) {
  applyExample(kind)
}
function applyExample(kind) {
  const ex = currentCityExamples.value[kind]
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
  abortAllInFlight()
  chainId += 1
  store.theme = 'all'
  store.interestThemes = []
  store.parsedInterests = []
  store.selectedDay = 'all'
  store.stage = null
  store.comparisonPrefs = null
  store.pendingHotel = null
  store.solverBusyUntil = 0
  store.busy.compare = store.busy.optimise = store.busy.sensitivity = store.busy.replan = false
  store.planFromReplan = false
  store.parseResult = null
  store.proposal = null
  store.explanations = { optimise: null, compare: null, replan: null }
  resetReplanState()
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


// ---- replanning (edits go through the API only) ----
function resetReplanState() {
  store.queue = []
  store.queueError = null
  store.previous = null
  store.lastReplan = null
  store.lastReplanRequest = null
  store.replanError = null
  store.restored = false
  store.explanations.replan = null
  store.explanations.optimise = null
}

export function queueOp(op) {
  const r = addOp(store.queue, op)
  store.queue = r.queue
  store.queueError = r.error
  store.restored = false
}
export function unqueue(index) { store.queue = removeOpAt(store.queue, index); store.queueError = null }
export function clearQueue() { store.queue = []; store.queueError = null }

/**
 * Send the queued operations in ONE /replan call. The schedule is sent exactly as received. `confirmed` is the literal result of the
 * confirmation dialog; it is never set from natural language. A rejected or infeasible replan leaves the original plan untouched.
 */
export async function applyQueue({ confirmed = false } = {}) {
  if (!store.plan || !store.queue.length) return
  const args = buildReplanArgs({ prefs: store.planPrefs, currentResult: store.plan.result, queue: store.queue, confirmed, source: 'ui' })
  store.busy.replan = true
  store.replanError = null
  store.restored = false
  try {
    const r = await api.replan(args.prefs, args.currentResult, args.operations, { ...args.options, cityId: store.cityId })
    store.lastReplan = r
    store.lastReplanRequest = args
    store.explanations.replan = null
    if (r.status === 'applied') {
      store.previous = { plan: store.plan, prefs: store.planPrefs, hotel: store.chosenHotel, fromReplan: store.planFromReplan }
      store.plan = { result: r.schedule, cost_summary: r.cost_summary ?? null, feasibility_report: r.feasibility_report, approximate: r.approximate, nights_used: r.nights_used,
        nights_source: r.nights_source, approximate_note: r.approximate ? 'The solver stopped at its time limit without proving optimality: this plan is good but may not be the best.' : undefined }
      store.planPrefs = r.new_preferences
      store.chosenHotel = r.hotel_id
      store.planFromReplan = true
      store.queue = []
      store.queueError = null
    }
  } catch (e) { fail('replanError', e); noteSolverBusy(store.replanError) } finally { store.busy.replan = false }
}

/** Switch back to the previous server-produced plan held in memory. A plain swap of two server results; nothing is edited or recomputed. */
export function restorePrevious() {
  const p = store.previous
  if (!p) return
  store.plan = p.plan
  store.planPrefs = p.prefs
  store.chosenHotel = p.hotel
  store.planFromReplan = p.fromReplan
  store.previous = null
  store.lastReplan = null
  store.queue = []
  store.restored = true
}

// ---- natural language: both paths produce PROPOSALS ----
export const maxInputChars = limits.max_input_chars

export async function runParse(text) {
  if (text.length > maxInputChars) { store.parseError = new ApiError({ code: 'input_too_long', message: `That is ${text.length} characters; the limit is ${maxInputChars}. Please shorten it (nothing was sent).` }); return }
  store.busy.parse = true
  store.parseError = null
  try {
    const r = await api.parseText(text, Number(store.form.startWeekday), store.cityId)
    store.parseResult = r
    store.parsedInterests = r.draft?.interests ?? []
    if (r.draft) {
      const next = formFromDraft(r.draft, store.form, store.city?.currency_code)
      store.form = next.form
      store.wishlist = next.wishlist
    }
  } catch (e) { fail('parseError', e) } finally { store.busy.parse = false; await refreshHealth() }
}

/** The user picked a suggestion / candidate: put that sight on the wishlist in the state it was asked for. */
export function chooseName(id, state) { store.wishlist[id] = state }

export async function runProposal(text) {
  if (!store.plan) return
  if (text.length > maxInputChars) { store.proposalError = new ApiError({ code: 'input_too_long', message: `That is ${text.length} characters; the limit is ${maxInputChars}. Please shorten it (nothing was sent).` }); return }
  store.busy.proposal = true
  store.proposalError = null
  try { store.proposal = await api.parseReplanText(text, store.planPrefs, store.plan.result, store.cityId) } catch (e) { fail('proposalError', e) } finally { store.busy.proposal = false; await refreshHealth() }
}
export function discardProposal() { store.proposal = null; store.proposalError = null }
/** Queue the chosen operations of a proposal. Only operations move across: no confirmation flag, no execution. */
export function queueProposal(includeIdx) {
  for (const op of proposalToOps(store.proposal, includeIdx)) queueOp(op)
  store.proposal = null
}

// ---- explanations: opt-in per click (each uses AI budget), supporting text only ----
export async function explain(kind) {
  store.explainError = null
  store.explaining = kind
  try {
    let resp
    if (kind === 'optimise') resp = await api.optimise(store.planPrefs, store.chosenHotel, { explain: true, cityId: store.cityId })
    else if (kind === 'compare') { const { prefs } = currentPrefs(); resp = await api.compareHotels(prefs, [...store.hotelIds], { sensitivity: false, explain: true, cityId: store.cityId }) }
    else if (kind === 'replan' && store.lastReplanRequest) {
      const a = store.lastReplanRequest
      resp = await api.replan(a.prefs, a.currentResult, a.operations, { ...a.options, explain: true, cityId: store.cityId })
    }
    store.explanations[kind] = resp?.explanation ?? null
  } catch (e) { fail('explainError', e) } finally { store.explaining = null; await refreshHealth() }
}
