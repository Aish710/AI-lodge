// Pure helpers for the Trip Trade-off Explorer. Every number shown comes from a real /compare-hotels response (baselines);
// nothing here optimises, estimates or re-ranks. Money is local currency, formatted by the caller.

export const VOT_FACTORS = [0.5, 1, 2, 4]

/** Value-of-time options as multiples of the city's own default (so they mean the same thing in every currency). */
export function votOptions(cityDefault) {
  const base = Number(cityDefault) > 0 ? Number(cityDefault) : 1000
  return VOT_FACTORS.map((k) => ({ factor: k, value: Math.round(base * k) }))
}

/** Rows for the A/B/C table, straight from the response. Components are kept separate; `score` is NOT spending. */
export function entryRows(baselines) {
  return (baselines?.entries ?? []).map((e) => ({
    key: e.key, label: e.label, feasible: e.feasible, hotel: e.hotel_name, hotelId: e.hotel_id, area: e.area,
    rooms: e.accommodation_jpy, admissions: e.admissions_jpy, transport: e.transport_jpy, spend: e.known_spend_jpy,
    minutes: e.travel_minutes, timeValue: e.travel_time_value_jpy,
    omitted: e.omitted_optional ?? [], charge: e.omitted_charge_jpy, unknown: e.unknown_price_items ?? [],
    score: e.score_jpy, sameAs: e.same_hotel_as ?? [],
  }))
}

/** A plain-sentence reason for the recommended hotel, built from the three rows. `money` and `mins` are formatters. */
export function whyHotel(baselines, money, mins) {
  const rows = entryRows(baselines)
  const by = Object.fromEntries(rows.map((r) => [r.key, r]))
  const joint = rows.find((r) => /joint/i.test(r.key)) ?? by.joint
  const cheap = rows.find((r) => /cheap/i.test(r.key)) ?? by.cheapest
  const conv = rows.find((r) => /conven/i.test(r.key)) ?? by.convenience
  if (!joint || !joint.feasible) return { lines: ['No feasible plan was found for these settings.'], change: false }
  const lines = []
  const sameCheap = cheap?.feasible && cheap.hotelId === joint.hotelId
  const sameConv = conv?.feasible && conv.hotelId === joint.hotelId
  if (sameCheap && sameConv) lines.push(`${joint.hotel} is the cheapest hotel, the most convenient hotel and the best overall: there is no trade-off between them for this trip.`)
  else if (sameCheap) lines.push(`${joint.hotel} is both the cheapest hotel and the best overall choice. ${conv?.feasible ? `${conv.hotel} would save ${mins(Math.max(0, joint.minutes - conv.minutes))} of estimated travel but its total score is ${money(conv.score - joint.score)} worse.` : ''}`.trim())
  else if (sameConv) lines.push(`${joint.hotel} is the most convenient hotel and the best overall choice. ${cheap?.feasible ? `${cheap.hotel} has lower known spending (${money(joint.spend - cheap.spend)} less) but its total score is ${money(cheap.score - joint.score)} worse.` : ''}`.trim())
  else lines.push(`${joint.hotel} is neither the cheapest nor the most convenient hotel, but it has the best total score at this value of time.`)
  if (joint.omitted.length) lines.push(`${joint.omitted.length} optional sight(s) are left out because including them costs more than they are worth at this value of time.`)
  const change = !(sameCheap && sameConv)
  return { lines, change }
}

/** Does the recommended hotel differ between two explorer runs? Used to say plainly when nothing changed. */
export function rankingChanged(a, b) {
  if (!a || !b) return false
  return a.best !== b.best
}

/** One explorer run, reduced to what the history table shows. */
export function summariseRun(vot, comparison) {
  const rows = entryRows(comparison?.baselines)
  return { vot, best: comparison?.best_by_true_cost ?? null, rows, at: Date.now() }
}

/** Keep the newest `max` valid plan states; same-id entries are replaced, never duplicated. */
export function pushState(list, state, max = 8) {
  const next = [state, ...list.filter((s) => s.id !== state.id)]
  return next.slice(0, max)
}
