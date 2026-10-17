// Loads the synced proof files. If anything is missing the page says so; there are no placeholder numbers anywhere.
import { countUserTestRows, parseClaims, parseRiskTable, playwrightSummary, sectionBullets, testSummary, vitestSummary } from './mdparse.js'

export const PROOF_BASE = '/proof-data/'   // not '/proof/': that would collide with the /proof page route on a static host

async function getText(fetchImpl, name) {
  const r = await fetchImpl(PROOF_BASE + name, { cache: 'no-store' })
  if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`)
  return r.text()
}

/** @returns {Promise<{state:'unavailable', reason:string} | {state:'ready', manifest:object, data:object, missing:object[]}>} */
export async function loadProof(fetchImpl = (...a) => fetch(...a)) {
  let manifest
  try {
    const r = await fetchImpl(PROOF_BASE + 'manifest.json', { cache: 'no-store' })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    manifest = await r.json()
    if (!Array.isArray(manifest?.copied)) throw new Error('manifest has no file list')
  } catch (e) {
    return { state: 'unavailable', reason: `The proof files are not part of this build (${e.message}). Run "npm run sync-proof" after generating them, then build again.` }
  }
  const has = (n) => manifest.copied.includes(n)
  const text = async (n) => (has(n) ? getText(fetchImpl, n) : null)
  const fetchVersion = async () => { try { return JSON.parse(await getText(fetchImpl, 'current-version.json')) } catch { return null } }
  const json = async (n) => { const t = await text(n); return t === null ? null : JSON.parse(t) }
  try {
    const [results, resultsMd, claimsMd, hardening, safety, backendTests, latestBackendTests, live, selfcheck, selfcheckHistory, goldFirst, goldAfter, goldMock, version, vitest, pw, front, lh, utCsv, utSummary, verification, redteam, redteamLive] = await Promise.all([
      json('eval-results.json'), text('eval-results.md'), text('README-claims.md'), text('hardening-results.md'), text('SAFETY_LOG.md'),
      text('backend-tests-full.md'), text('backend-tests-latest.md'), text('llm-live-eval.md'), text('ai-selfcheck.md'), text('ai-selfcheck-history.md'), text('gold-results-live-first-run.md'), text('gold-results-live-after-fix.md'), text('gold-results-mock.md'), fetchVersion(), json('frontend-vitest.json'), json('frontend-playwright.json'), json('frontend-test-summary.json'), json('lighthouse-summary.json'),
      text('user-test-results.csv'), text('user-test-summary.md'), json('verification-counts.json'), json('redteam-results.json'), text('redteam-live.md')])
    return { state: 'ready', manifest, missing: manifest.missing ?? [], data: {
      results, claims: claimsMd ? parseClaims(claimsMd) : null, notShown: resultsMd ? sectionBullets(resultsMd, 'WHAT THESE NUMBERS DO NOT SHOW') : null,
      hardeningMd: hardening, risks: safety ? parseRiskTable(safety) : null, live, selfcheck, selfcheckHistory, goldFirst, goldAfter, goldMock, promptVersion: version?.prompt_version ?? null, verification, redteam, redteamLive,
      tests: { backend: backendTests ? testSummary(backendTests) : null, backendLatest: latestBackendTests ? testSummary(latestBackendTests) : null,
        vitest: vitestSummary(vitest), playwright: playwrightSummary(pw), frontend: front }, lighthouse: lh,
      // the card is shown with results ONLY when the CSV has participant rows; otherwise it says "not run yet"
      userTest: { rows: utCsv ? countUserTestRows(utCsv) : 0, summary: utSummary } } }
  } catch (e) {
    return { state: 'unavailable', reason: `A proof file could not be read (${e.message}).` }
  }
}

// ---- derived "read this first" notes. Every number comes from the proof JSON; the thresholds below are judgement calls. ----
export const THRESHOLDS = { smallSubsetShare: 0.5, tieShare: 0.25, rareEffectShare: 0.25 }

export function readThisFirst(metrics, n) {
  const notes = []
  const t = metrics.travel
  for (const [key, label] of [['naive', 'input-order baseline'], ['nn', 'nearest-neighbour baseline']]) {
    const c = t[key]
    if (c.n_comparable < c.n_trips * THRESHOLDS.smallSubsetShare) notes.push(`Small comparable subset: only ${c.n_comparable} of ${c.n_trips} trips scheduled the same sights as the ${label}, so the travel comparison rests on those ${c.n_comparable}.`)
  }
  const nn = t.nn
  if (nn.n_comparable && nn.equal / nn.n_comparable >= THRESHOLDS.tieShare) notes.push(`The nearest-neighbour baseline often ties: it matched the optimiser exactly on ${nn.equal} of ${nn.n_comparable} comparable trips.`)
  const pl = metrics.placement
  if (pl.solver.placed < Math.min(pl.naive.placed, pl.nn.placed)) notes.push(`The optimiser schedules fewer sights than the baselines (${pl.solver.placed} vs ${pl.naive.placed} and ${pl.nn.placed} of ${pl.requested} requested) because it skips optional sights that cost more than they are worth.`)
  const v = metrics.hotel_value.vots?.['1000']
  if (v && v.n_eligible && v.cheapest_by_rate_not_best / v.n_eligible < THRESHOLDS.rareEffectShare) notes.push(`The hotel finding is weak on random trips: at the default value of time the lowest-rate hotel was not the best by true cost in only ${v.cheapest_by_rate_not_best} of ${v.n_eligible} trips.`)
  const au = metrics.must_visit.infeasible_audit
  if (Object.keys(au.by_code).length === 1) notes.push(`The audit of infeasibility reports covers only one kind of conflict (${Object.keys(au.by_code)[0].replace(/_/g, ' ')}) in these ${n} trips.`)
  return notes
}

/** A live report is "current" only if it was made with the CURRENT prompt version. Missing -> not run; another version -> not run on this version. */
export function liveStatus(text, currentVersion) {
  if (!text) return { state: 'missing', version: null }
  const v = text.match(/PROMPT_VERSION:\s*`([^`]+)`/)?.[1] ?? null
  if (currentVersion && v && v !== currentVersion) return { state: 'stale', version: v }
  return { state: 'current', version: v }
}
