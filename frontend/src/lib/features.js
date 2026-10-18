// What this page needs from the server. A server started from older code lacks some of these; the page says so instead of failing on one button with "Not found".
export const REQUIRED_FEATURES = ['check-itinerary', 'evaluate-itinerary', 'explore', 'copilot', 'parse-repair', 'apply-repair', 'parse-profile', 'min-active-days', 'plan-verification']

/** features: the array the server lists, or null/undefined when /version itself was not found (a much older server). */
export function missingFeatures(features) {
  const have = new Set(Array.isArray(features) ? features : [])
  return REQUIRED_FEATURES.filter((f) => !have.has(f))
}
