// One typed function per backend route. The UI imports these, never fetch().
import { request, SOLVE_TIMEOUT_MS } from './client.js'

/** @returns {Promise<{status:string, mode:'llm'|'sample', llm_configured:boolean, llm_mode:string, llm_limit_reached:boolean}>} */
export const getHealth = () => request('GET', '/health', { key: 'health', timeoutMs: 8000 })
export const getCities = () => request('GET', '/data/cities', { key: 'cities', timeoutMs: 15000 })
export const getSummary = (cityId = 'tokyo') => request('GET', `/data/summary?city_id=${encodeURIComponent(cityId)}`, { key: 'summary', timeoutMs: 15000 })
/** Reference data: coordinates, prices, hours, provenance. Descriptions are never included. */
export const getPlaces = (cityId = 'tokyo') => request('GET', `/data/places?city_id=${encodeURIComponent(cityId)}`, { key: 'places', timeoutMs: 15000 })

/** @param {import('./types.js').Preferences} preferences @returns {Promise<import('./types.js').OptimiseResponse>} */
export const optimise = (preferences, hotelId, { explain = false, cityId = 'tokyo' } = {}) =>
  request('POST', '/optimise', { key: 'optimise', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: cityId, preferences, hotel_id: hotelId, explain } })

/** Without sensitivity this is fast; with it the server spends up to its 10 s comparison budget, so the UI asks for it second. */
export const compareHotels = (preferences, hotelIds, { sensitivity = true, explain = false, cityId = 'tokyo' } = {}) =>
  request('POST', '/compare-hotels', { key: sensitivity ? 'compare-sens' : 'compare', timeoutMs: SOLVE_TIMEOUT_MS,
    body: { city_id: cityId, preferences, hotel_ids: hotelIds, include_sensitivity: sensitivity, explain } })

/** `currentResult` is sent exactly as received from the server; the client never edits a schedule. */
export const replan = (preferences, currentResult, operations, { confirmRemoveMustVisit = false, explain = false, cityId = 'tokyo' } = {}) =>
  request('POST', '/replan', { key: 'replan', timeoutMs: SOLVE_TIMEOUT_MS,
    body: { city_id: cityId, preferences, current_result: currentResult, operations, confirm_remove_must_visit: confirmRemoveMustVisit === true, explain } })

export const parseText = (text, startWeekday = null, cityId = 'tokyo') =>
  request('POST', '/parse', { key: 'parse', timeoutMs: SOLVE_TIMEOUT_MS, body: startWeekday === null ? { city_id: cityId, text } : { city_id: cityId, text, start_weekday: startWeekday } })

export const parseReplanText = (text, preferences, currentResult, cityId = 'tokyo') =>
  request('POST', '/parse-replan', { key: 'parse-replan', timeoutMs: SOLVE_TIMEOUT_MS, body: { city_id: cityId, text, preferences, current_result: currentResult } })
