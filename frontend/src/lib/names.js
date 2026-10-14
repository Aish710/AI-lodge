// The data keeps "(fictional)" in hotel names (it is a provenance fact). The interface shows a "Demo hotel" tag instead, so the
// suffix is removed from every name and every server sentence before display. Nothing else about the text is touched.
export const cleanHotelText = (text) => (typeof text === 'string' ? text.replace(/\s*\(fictional\)/gi, '') : text)

/** Everything a city switch discards, as plain labels for the confirmation dialog. Only items that currently exist are listed. */
export function clearedOnCitySwitch(s) {
  const out = []
  const sights = Object.keys(s.wishlist ?? {}).length
  if (sights) out.push(`your wishlist (${sights} marked ${sights === 1 ? 'sight' : 'sights'})`)
  if (s.hotelIds?.length || s.chosenHotel) out.push('your hotel selection')
  if (s.comparison) out.push('the hotel comparison')
  if (s.plan) out.push('the itinerary')
  if (s.queue?.length) out.push(`pending changes (${s.queue.length})`)
  if (s.previous || s.lastReplan) out.push('the replan history')
  return out
}
