// One typed function per backend route. The UI imports these, never fetch().
import { request, SOLVE_TIMEOUT_MS } from './client.js'

/** @returns {Promise<{status:string, mode:'llm'|'sample', llm_configured:boolean, llm_mode:string, llm_limit_reached:boolean}>} */
export const getHealth = () => request('GET', '/health', { key: 'health', timeoutMs: 8000 })
export const getSummary = () => request('GET', '/data/summary', { key: 'summary', timeoutMs: 15000 })
/** Reference data: coordinates, prices, hours, provenance. Descriptions are never included. */
export const getPlaces = () => request('GET', '/data/places', { key: 'places', timeoutMs: 15000 })

/** @param {import('./types.js').Preferences} preferences @returns {Promise<import('./types.js').OptimiseResponse>} */
export const optimise = (preferences, hotelId, { explain = false } = {}) =>
  request('POST', '/optimise', { key: 'optimise', timeoutMs: SOLVE_TIMEOUT_MS, body: { preferences, hotel_id: hotelId, explain } })

/** Without sensitivity this is fast; with it the server spends up to its 10 s comparison budget, so the UI asks for it second. */
export const compareHotels = (preferences, hotelIds, { sensitivity = true, explain = false } = {}) =>
  request('POST', '/compare-hotels', { key: sensitivity ? 'compare-sens' : 'compare', timeoutMs: SOLVE_TIMEOUT_MS,
    body: { preferences, hotel_ids: hotelIds, include_sensitivity: sensitivity, explain } })

/** `currentResult` is sent exactly as received from the server; the client never edits a schedule. */
export const replan = (preferences, currentResult, operations, { confirmRemoveMustVisit = false, explain = false } = {}) =>
  request('POST', '/replan', { key: 'replan', timeoutMs: SOLVE_TIMEOUT_MS,
    body: { preferences, current_result: currentResult, operations, confirm_remove_must_visit: confirmRemoveMustVisit === true, explain } })

export const parseText = (text, startWeekday = null) =>
  request('POST', '/parse', { key: 'parse', timeoutMs: SOLVE_TIMEOUT_MS, body: startWeekday === null ? { text } : { text, start_weekday: startWeekday } })

export const parseReplanText = (text, preferences, currentResult) =>
  request('POST', '/parse-replan', { key: 'parse-replan', timeoutMs: SOLVE_TIMEOUT_MS, body: { text, preferences, current_result: currentResult } })
