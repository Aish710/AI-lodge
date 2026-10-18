// One typed function per backend route. The UI imports these, never fetch().
import { request, SOLVE_TIMEOUT_MS } from './client.js'

// The city is never defaulted here: the store is the single source, and a missing city is a programming error, not Tokyo.
const city = (id) => { if (typeof id !== 'string' || !id) throw new Error('city_id is required'); return id }

/** @returns {Promise<{status:string, mode:'llm'|'sample', llm_configured:boolean, llm_mode:string, llm_limit_reached:boolean}>} */
export const getHealth = () => request('GET', '/health', { key: 'health', timeoutMs: 8000 })
export const getCities = () => request('GET', '/data/cities', { key: 'cities', timeoutMs: 15000 })
export const getSummary = (cityId) => request('GET', `/data/summary?city_id=${encodeURIComponent(city(cityId))}`, { key: 'summary', timeoutMs: 15000 })
/** Reference data: coordinates, prices, hours, provenance. Descriptions are never included. */
export const getPlaces = (cityId) => request('GET', `/data/places?city_id=${encodeURIComponent(city(cityId))}`, { key: 'places', timeoutMs: 15000 })

/** @param {import('./types.js').Preferences} preferences @returns {Promise<import('./types.js').OptimiseResponse>} */
export const optimise = (preferences, hotelId, { explain = false, cityId } = {}) =>
  request('POST', '/optimise', { key: 'optimise', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: city(cityId), preferences, hotel_id: hotelId, explain } })

/** Without sensitivity this is fast; with it the server spends up to its 10 s comparison budget, so the UI asks for it second. */
export const compareHotels = (preferences, hotelIds, { sensitivity = true, explain = false, cityId } = {}) =>
  request('POST', '/compare-hotels', { key: sensitivity ? 'compare-sens' : 'compare', timeoutMs: SOLVE_TIMEOUT_MS,
    body: { city_id: city(cityId), preferences, hotel_ids: hotelIds, include_sensitivity: sensitivity, explain } })

/** `currentResult` is sent exactly as received from the server; the client never edits a schedule. */
export const replan = (preferences, currentResult, operations, { confirmRemoveMustVisit = false, explain = false, cityId } = {}) =>
  request('POST', '/replan', { key: 'replan', timeoutMs: SOLVE_TIMEOUT_MS,
    body: { city_id: city(cityId), preferences, current_result: currentResult, operations, confirm_remove_must_visit: confirmRemoveMustVisit === true, explain } })

export const parseText = (text, startWeekday = null, cityId) =>
  request('POST', '/parse', { key: 'parse', timeoutMs: SOLVE_TIMEOUT_MS, body: startWeekday === null ? { city_id: city(cityId), text } : { city_id: city(cityId), text, start_weekday: startWeekday } })

export const parseReplanText = (text, preferences, currentResult, cityId) =>
  request('POST', '/parse-replan', { key: 'parse-replan', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: city(cityId), text, preferences, current_result: currentResult } })

/** Bounded budget/time alternatives (real optimiser runs, dominance-filtered). */
export const explore = (preferences, hotelIds, { cityId } = {}) =>
  request('POST', '/explore', { key: 'explore', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: city(cityId), preferences, hotel_ids: hotelIds } })

/** Your itinerary vs the optimiser for the same sights (and a full plan). `days` = arrays of attraction ids in the user's order. */
export const evaluateItinerary = (preferences, hotelId, days, { cityId } = {}) =>
  request('POST', '/evaluate-itinerary', { key: 'evaluate-itinerary', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: city(cityId), preferences, hotel_id: hotelId, days } })

/** AI-assisted repair: free text -> a PROPOSAL (nothing applied) that the server has tried on a copy. `keepHotel` is the person's own lock. */
export const parseRepair = (text, preferences, hotelId, keepHotel, cityId) =>
  request('POST', '/parse-repair', { key: 'parse-repair', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: city(cityId), text, preferences, hotel_id: hotelId, keep_hotel: keepHotel === true } })

/** Apply a confirmed repair. The server re-checks everything against the current plan; `confirmedIds` are the person's own ticks. */
export const applyRepair = (preferences, hotelId, keepHotel, baseFingerprint, actions, confirmedIds, cityId) =>
  request('POST', '/apply-repair', { key: 'apply-repair', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: city(cityId), preferences, hotel_id: hotelId, keep_hotel: keepHotel === true, base_fingerprint: baseFingerprint, actions, confirmed_ids: confirmedIds } })

/** AI-interpreted travel style: free text -> proposed settings (explicit or inferred). Nothing applied or solved. */
export const parseProfile = (text, current, userOverrides, cityId) =>
  request('POST', '/parse-profile', { key: 'parse-profile', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: city(cityId), text, current, user_overrides: userOverrides } })

/** Read-only contextual question. All plan evidence is rebuilt on the server. */
export const askCopilot = (preferences, currentResult, fingerprint, text, operation, cityId) =>
  request('POST', '/copilot', { key: 'copilot', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: city(cityId), preferences, current_result: currentResult, fingerprint, text, operation } })
