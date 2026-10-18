// The default explanation of a plan: sentences built by code from the server's own numbers (cost summary, validator report, schedule). No AI text, no arithmetic beyond reading
// what the server returned. The AI explanation, when asked for, is an OPTIONAL extra under it; this summary is complete without it.

/** feasible | conditional | blocked_missing_info | infeasible -> short status wording. */
function statusLine(resp) {
  const r = resp?.result, rep = resp?.feasibility_report
  if (r?.status !== 'feasible') return { kind: 'bad', text: 'No feasible plan under the rules you set.' }
  if (rep?.verification === 'conditional') return { kind: 'warn', text: 'Feasible if the unverified opening hours are confirmed (provisional). The independent validator passed every other rule.' }
  if (rep?.overall === 'fail') return { kind: 'bad', text: 'The independent validator found a problem with this plan.' }
  return { kind: 'good', text: 'Feasible: the independent validator checked every rule against the sample data.' }
}

/**
 * @param resp  an /optimise (or applied repair) response
 * @param o     { money, mins, names: id->name, hotelName, wanted }  formatters and labels from the page
 * @returns {{status:{kind:string,text:string}, lines:{key:string,label:string,text:string}[]}}
 */
export function planSummary(resp, { money, mins, names = {}, hotelName = '', wanted = null } = {}) {
  const r = resp?.result
  if (!r) return null
  const trip = resp.cost_summary?.trip ?? null
  const days = r.days ?? []
  const stops = days.flatMap((d) => d.stops ?? [])
  const active = days.filter((d) => (d.stops ?? []).length).length
  const lines = []
  if (r.status === 'feasible') {
    lines.push({ key: 'coverage', label: 'Sights', text: `${stops.length}${wanted ? ` of ${wanted}` : ''} sight${stops.length === 1 ? '' : 's'} over ${days.length} day${days.length === 1 ? '' : 's'} (${active} with activities) at ${hotelName || 'the chosen hotel'}.` })
    if (trip) {
      const parts = `sights and transport ${money(trip.cash_total)} + rooms ${money(trip.rooms)} (${trip.nights} night${trip.nights === 1 ? '' : 's'} at a demo hotel's sample rate)`
      lines.push({ key: 'spending', label: 'Modelled spending', text: `${money(trip.cash_total_with_rooms)} including rooms: ${parts}. Not a quote.` })
    } else lines.push({ key: 'spending', label: 'Modelled spending', text: `${money(resp.result.totals.total_jpy)} for sights and transport (rooms not available).` })
    lines.push({ key: 'travel', label: 'Estimated travel', text: `${mins(r.totals.travel_minutes)} in total, estimated from straight-line distances.` })
    const unknown = (trip?.unknown_price_ids ?? r.totals.unknown_cost_items ?? []).map((id) => names[id] ?? id)
    if (unknown.length) lines.push({ key: 'unknown', label: 'Not included', text: `The admission price is unknown for ${unknown.join(', ')}; it is excluded from every total, not counted as free.` })
  }
  return { status: statusLine(resp), lines }
}

/** What the AI attempt amounted to. `attempted` = a model call was made; `accepted` = its wording passed every check and is what is shown. They are different things. */
export function aiOutcome(explanation) {
  if (!explanation) return { state: 'none', label: 'No AI wording requested' }
  const attempted = (explanation.call_count ?? 0) > 0
  const accepted = explanation.source === 'llm'
  if (accepted) return { state: 'accepted', attempted, label: explanation.cited ? 'AI wording accepted: every claim cited and checked' : 'AI wording accepted: numbers checked' }
  if (attempted) return { state: 'rejected', attempted, label: 'AI wording was tried but not used' }
  return { state: 'not_used', attempted, label: 'No AI wording (AI off or unavailable)' }
}

/** One plain sentence for each rejection reason code the server reports (no jargon). */
export function rejectionText(token) {
  const t = String(token)
  if (/^S\d+: a number used for the wrong item/.test(t)) return `A sentence used a correct figure for the wrong thing (${t.replace(/^.*\((.*)\)$/, '$1')}).`
  if (/not supported by the cited facts/.test(t)) return `A sentence contained a number or name that the plan's facts do not support (${t.replace(/^.*\((.*)\)$/, '$1')}).`
  if (/uncited/.test(t)) return 'A sentence did not say which fact it rests on.'
  if (/unknown fact id/.test(t)) return 'A sentence cited a fact that does not exist.'
  if (/claim the data cannot support/.test(t)) return 'A sentence made a claim the sample data cannot support.'
  if (/internal text/.test(t)) return 'A sentence contained text that looked like internal instructions.'
  if (/^name:/.test(t)) return `A place from another city was mentioned (${t.slice(5)}).`
  if (/^format$|^length$/.test(t)) return 'The reply was not in the expected format.'
  return `A check failed (${t}).`
}
