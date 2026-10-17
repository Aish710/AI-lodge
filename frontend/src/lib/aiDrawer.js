// "What the AI did": built ONLY from fields the API already returns (never the system prompt, place descriptions or any key).
// kind: 'parse' | 'proposal' | 'explain'
const CODE_DID = {
  parse: ['Cleaned your text before it was sent (no place descriptions are ever sent)', "Matched every name to this city's places", 'Checked the destination city', 'Worked out currencies and amounts', 'Filled the defaults you did not give'],
  proposal: ['Cleaned your text before it was sent', "Matched every name to this city's places", 'Turned the AI\'s proposal into plain sentences', 'Kept every operation unapplied until you add it and press Apply'],
  explain: ['Computed every number and name in the facts', 'Checked each number, time and name in the AI text against those facts', 'Added the planner warnings word for word'],
}

export function drawerModel(kind, r, { health = null } = {}) {
  if (!r) return null
  const calls = r.call_count ?? 0
  const llm = kind === 'explain' ? r.source === 'llm' : r.mode === 'llm'
  const changes = []
  if (kind === 'explain') {
    if (r.reason) changes.push({ what: 'The AI text was not used', why: r.reason })
    const rej = r.grounding?.rejected_tokens ?? []
    if (rej.length) changes.push({ what: `Code rejected ${rej.length} item(s) in the AI text: ${rej.join(', ')}`, why: 'They did not match the computed facts, so a template summary was shown instead.' })
    if (r.warnings?.length) changes.push({ what: `Code added ${r.warnings.length} warning(s) word for word`, why: 'Warnings come from the planner, never from the AI.' })
  } else {
    for (const u of r.unresolved_names ?? []) changes.push({ what: `"${u.input}" was dropped`, why: `Not a place in this city's data, so it cannot be scheduled${u.suggestions?.length ? `; offered: ${u.suggestions.map((s) => s.name).join(', ')}` : ''}.` })
    for (const a of r.ambiguities ?? []) changes.push({ what: `"${a.input}" was not guessed`, why: `It could mean ${a.candidates.length} places (${a.candidates.map((c) => c.name).join(', ')}), so you are asked to choose.` })
    if (r.defaults_applied?.length) changes.push({ what: `Defaults filled in by code: ${r.defaults_applied.join('; ')}`, why: 'You did not say them, and the AI is not allowed to invent them.' })
    for (const c of r.currency_confirmations ?? []) changes.push({ what: 'An amount was not guessed', why: c.message ?? 'The currency symbol was ambiguous, so you are asked to confirm.' })
    if (r.switch_offer) changes.push({ what: `Nothing was planned for this request`, why: `It named ${r.switch_offer.display_name}, but this trip is for another city. Code offers a switch; it never switches by itself.` })
    if (r.destination?.message && !r.switch_offer) changes.push({ what: "Destination check", why: r.destination.message })
    if (kind === 'proposal' && r.requires_confirmation) changes.push({ what: 'A must-visit removal is flagged', why: 'Only your confirmation can allow it; the AI cannot set it.' })
  }
  return {
    calls, llm,
    source: kind === 'explain' ? (llm ? 'AI-written, then checked by code' : 'Template summary written by code') : (llm ? 'Read by the AI, then checked by code' : 'AI off: nothing was sent to a model'),
    promptVersion: kind === 'explain' ? null : (r.prompt_version || null),
    model: llm ? (health?.llm_model ?? null) : null, host: llm ? (health?.llm_endpoint ?? null) : null,
    raw: kind === 'explain' ? null : (r.extracted_json ?? null),
    changes, codeDid: CODE_DID[kind],
  }
}
