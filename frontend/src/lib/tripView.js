// Small view helpers for the Your trip screen. They only reshape values the server already computed; nothing here sums money.
import { mixText } from './themes.js'
import { humanMinutes } from './format.js'
import { toMinutes } from './time.js'

export const stopDuration = (s) => toMinutes(s.end) - toMinutes(s.start)

/** "2 sightseeing, 1 food & drink" for the stops of one day. */
export function dayMix(day, placesById) {
  return mixText(day.stops.map((s) => placesById[s.attraction_id]).filter(Boolean), { lower: true })
}

/** One plain line about a day, from the flags the server attached to its stops (nothing is inferred). */
export function dayStatus(day) {
  if (!day.stops.length) return 'No activities this day.'
  const flags = day.stops.flatMap((s) => s.uncertainty_flags ?? [])
  const parts = []
  const n = (f) => flags.filter((x) => x === f).length
  if (n('opening_hours_unknown')) parts.push(`${n('opening_hours_unknown')} with unknown opening hours`)
  if (n('price_unknown')) parts.push(`${n('price_unknown')} with an unknown price`)
  if (n('advance_booking_required')) parts.push(`${n('advance_booking_required')} needing advance booking`)
  return parts.length ? `Check: ${parts.join(', ')}.` : 'No warnings on this day.'
}

export const tags = (s, lockedIds = []) => {
  const f = s.uncertainty_flags ?? []
  return {
    must: !!s.is_must_visit, include: !s.is_must_visit, booking: f.includes('advance_booking_required'),
    unknownHours: f.includes('opening_hours_unknown'), locked: lockedIds.includes(s.attraction_id),
  }
}
export const fareLine = (minutes, fareText) => `Travel ${humanMinutes(minutes)} · ${fareText} · estimated`
