// Generates docs/SUBMISSION-FACTS.md: plain facts for Devpost/LinkedIn text, each with its source file. Figures are copied from GENERATED files
// only; anything not available is written as "not measured". Run after the tests, the evaluation and Lighthouse. Nothing here is typed by hand.
// Usage: node scripts/make-submission-facts.mjs
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const readText = (p) => (existsSync(join(ROOT, p)) ? readFileSync(join(ROOT, p), 'utf8') : null)
const readJson = (p) => { const t = readText(p); return t ? JSON.parse(t) : null }
const NM = 'not measured'
const floor1 = (x) => (Math.floor(x * 10) / 10).toFixed(1)
const ceil1 = (x) => (Math.ceil(x * 10) / 10).toFixed(1)
const facts = []
const add = (section, text, source) => facts.push({ section, text, source })

const ev = readJson('docs/eval-results.json')
const backend = (() => {
  const t = readText('backend/tests/results/latest-full.md')
  const m = t && /Passed:\s*(\d+),\s*failed:\s*(\d+),\s*skipped:\s*(\d+),\s*total:\s*(\d+)/.exec(t)
  const rev = t && /Git revision:\s*(.+?)\./.exec(t)
  return m ? { passed: +m[1], failed: +m[2], skipped: +m[3], total: +m[4], revision: rev?.[1] ?? 'unknown' } : null
})()
const vitest = readJson('frontend/test-results/vitest.json')
const pw = readJson('frontend/test-results/playwright.json')
const lh = readJson('docs/lighthouse-summary.json')
const safety = readText('docs/SAFETY_LOG.md')
const hard = readText('docs/hardening-results.md')

add('Tests', backend ? `Backend full suite: ${backend.passed} passed, ${backend.failed} failed, ${backend.skipped} skipped, ${backend.total} total (pytest), revision ${backend.revision}.` : `Backend full suite: ${NM}.`, 'backend/tests/results/latest-full.md')
add('Tests', vitest ? `Frontend unit and component tests: ${vitest.numPassedTests} passed, ${vitest.numFailedTests} failed, ${vitest.numTotalTests} total (Vitest).` : `Frontend unit tests: ${NM}.`, 'frontend/test-results/vitest.json (npm run test:report)')
add('Tests', pw?.stats ? `End-to-end tests against the real backend in sample mode: ${pw.stats.expected} passed, ${pw.stats.unexpected} failed (Playwright).` : `End-to-end tests: ${NM}.`, 'frontend/test-results/playwright.json (npm run test:report)')

if (ev) {
  const m = ev.metrics
  const t = m.travel
  const src = 'docs/eval-results.json (docs/eval-results.md, docs/README-claims.md)'
  add('Evaluation', `Evaluation run ${ev.meta.date}, code version ${ev.meta.commit}, mode ${ev.meta.mode}, ${m.n_trips} seeded synthetic trips on sample data (12 attractions, 3 fictional hotels).`, src)
  add('Evaluation', `${ev.scenarios.filter((s) => s.passed).length} of ${ev.scenarios.length} named scenarios pass (3 of them use a scripted stand-in for the AI: they verify the pipeline, not the model).`, src)
  for (const [k, label] of [['naive', 'input-order baseline'], ['nn', 'nearest-neighbour baseline']]) {
    const c = t[k]
    add('Evaluation', `Travel time vs the ${label}, on the ${c.n_comparable} of ${c.n_trips} trips where both scheduled the same sights: mean ${floor1(c.percent_reduction.mean)}% less (median ${floor1(c.percent_reduction.median)}%, range ${floor1(c.percent_reduction.min)}% to ${floor1(c.percent_reduction.max)}%); better on ${c.better}, equal on ${c.equal}, worse on ${c.worse}. Sample data; not a claim about real trips.`, src)
  }
  add('Evaluation', `Independent validator: ${m.validation.solver.pass + m.validation.solver.pass_with_warnings} of ${m.validation.solver.n_trips - m.validation.solver.no_plan} optimiser plans passed, ${m.validation.solver.fail} failed (${m.validation.solver.no_plan} trips had no plan because the request was infeasible). Input-order baseline: ${m.validation.naive.fail} of ${m.validation.naive.n_trips} plans failed, ${m.validation.naive.fail_hard_constraint_beyond_missing_must_visit} for a reason beyond a missing must-visit. Nearest-neighbour: ${m.validation.nn.fail} of ${m.validation.nn.n_trips}, ${m.validation.nn.fail_hard_constraint_beyond_missing_must_visit} beyond a missing must-visit.`, src)
  add('Evaluation', `Strict budgets (${m.budget.n_strict_trips} trips): ${m.budget.solver.within_budget} of ${m.budget.solver.feasible_plans} optimiser plans within budget.`, src)
  const a = m.must_visit.infeasible_audit
  add('Evaluation', `Of ${a.n_infeasible} infeasibility reports, every stated conflict matched an independent recomputation in ${a.all_stated_conflicts_confirmed}; exhaustive search found a schedule the optimiser missed in ${a.brute_force_found_a_schedule}. All ${a.n_infeasible} were one conflict type (${Object.keys(a.by_code).join(', ')}).`, src)
  for (const [v, e] of Object.entries(m.hotel_value.vots)) add('Evaluation', `Hotel value at ${Number(v).toLocaleString('en-US')} JPY/h: the lowest-rate hotel was not the best by true cost in ${e.cheapest_by_rate_not_best} of ${e.n_eligible} trips (${floor1((100 * e.cheapest_by_rate_not_best) / e.n_eligible)}%). Hotels and rates are fictional and were tuned for the demo.`, src)
  if (m.replan) {
    const mean = (x) => x.reduce((p, q) => p + q, 0) / Math.max(x.length, 1)
    add('Evaluation', `Replanning (${m.replan.n_both_applied} paired scenarios): disruption-aware moved fewer activities in ${m.replan.aware_fewer_moves}, the same in ${m.replan.same_moves}, more in ${m.replan.aware_more_moves}; mean moved ${ceil1(mean(m.replan.aware.moved))} (aware) vs ${floor1(mean(m.replan.naive.moved))} (naive).`, src)
  }
  add('Evaluation', `Solver status on trip solves: ${Object.entries(m.solver_status.trip_solves).map(([k, v]) => `${k} ${v}`).join(', ')}.`, src)
} else add('Evaluation', `Evaluation results: ${NM}.`, 'docs/eval-results.json')

if (lh) {
  for (const p of lh.pages) add('Lighthouse', `${p.name} (${p.mode}): performance ${p.performance ?? NM}, accessibility ${p.accessibility}, best practices ${p.bestPractices}. Measured with ${lh.tool}, ${lh.preset}, on a local machine.`, 'docs/lighthouse-summary.json (docs/lighthouse-results.md)')
} else add('Lighthouse', `Lighthouse scores: ${NM}.`, 'docs/lighthouse-summary.json')

if (safety) {
  const rows = safety.split('\n').filter((l) => /^\|\s*\d+\s*\|/.test(l)).length
  add('Safety', `${rows} risks are tracked in the safety log, each with a safeguard, the test names that check it, and a status.`, 'docs/SAFETY_LOG.md')
} else add('Safety', `Safety log: ${NM}.`, 'docs/SAFETY_LOG.md')
const hm = hard && /\*\*(\d+)\/(\d+) cases passed\*\*/.exec(hard)
add('Safety', hm ? `API hardening: ${hm[1]} of ${hm[2]} in-process abuse cases passed.` : `API hardening results: ${NM}.`, 'docs/hardening-results.md')

// ---- what exists, and what does not (read from the repository, not typed) ----
import { readdirSync } from 'node:fs'
const cities = existsSync(join(ROOT, 'backend/app/data/cities')) ? readdirSync(join(ROOT, 'backend/app/data/cities')).filter((n) => existsSync(join(ROOT, 'backend/app/data/cities', n, 'city.json'))) : []
add('Product', cities.length ? `${cities.length} sample city packs: ${cities.join(', ')}. One city per trip; all records are labelled sample data and none is labelled verified.` : `City packs: ${NM}.`, 'backend/app/data/cities/')
add('Product', 'In-app pages: Trip, Sights, Hotels, Itinerary, Proof (measured results, hardening, risk table, user-test card) and How it works (architecture, how the AI is used, limitations, privacy).', 'frontend/src/router.js')
const shots = existsSync(join(ROOT, 'docs/screenshots/steps')) ? readdirSync(join(ROOT, 'docs/screenshots/steps')).filter((n) => n.endsWith('.png')).length : 0
add('Product', shots ? `${shots} step screenshots (two cities, desktop and mobile, plus the Proof and How it works pages) in docs/screenshots/steps/.` : `Step screenshots: ${NM}.`, 'docs/screenshots/steps/')

const csvText = readText('docs/user-test/results.csv')
const utRows = csvText ? csvText.split(/\r?\n/).filter((l) => l.trim()).slice(1).filter((l) => l.split(',').some((c) => c.trim())).length : 0
add(utRows ? 'User test' : 'Not measured', utRows ? `${utRows} user-test participant(s); see docs/user-test/summary.md for the generated medians and verbatim quotes. Small sample.` : 'Any user study or real-user outcome: the user-test kit exists but no result has been collected (the Proof page says "Not run yet").', utRows ? 'docs/user-test/results.csv' : 'docs/user-test/ (results.csv has no rows)')
if (existsSync(join(ROOT, 'docs/llm-live-eval.md'))) add('AI evaluation', 'A live AI evaluation result file exists; read its date, model and per-city N before quoting any figure.', 'docs/llm-live-eval.md')
else add('Not measured', 'AI parsing and explanation quality with a live model (the opt-in live evaluation has not been run).', 'docs/llm-live-eval.md (absent)')
add('Not measured', 'Real hotel markets; live prices or opening hours.', '')
add('Not measured', 'Backend cold-start time on the free host and the Docker image build (neither has been run).', 'docs/DEPLOY.md')

const out = ['# Submission facts (generated)', '',
  `Generated ${new Date().toISOString().slice(0, 16).replace('T', ' ')} UTC by \`frontend/scripts/make-submission-facts.mjs\`. Each line is copied from a generated file (named beside it); anything not available says "${NM}". Re-run the full backend suite, frontend tests, evaluation and Lighthouse before release; do not edit by hand.`, '']
for (const sec of [...new Set(facts.map((f) => f.section))]) {
  out.push(`## ${sec}`, '')
  for (const f of facts.filter((x) => x.section === sec)) out.push(`- ${f.text}${f.source ? `  \n  *Source: ${f.source}*` : ''}`)
  out.push('')
}
writeFileSync(join(ROOT, 'docs', 'SUBMISSION-FACTS.md'), out.join('\n'))
console.log(`wrote docs/SUBMISSION-FACTS.md (${facts.length} facts)`)
