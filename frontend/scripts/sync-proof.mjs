// Copies the generated proof files into public/proof-data/ so the built app can show them. Nothing is edited or typed by hand.
// Usage: node scripts/sync-proof.mjs [--strict]
//   default: copies what exists, writes manifest.json listing what is missing (the Proof page then says so instead of showing placeholders)
//   --strict: exits 1 with a clear message if any REQUIRED file is missing (use before a submission build)
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { llmFingerprint } from './llm-fingerprint.mjs'
import { fileURLToPath, pathToFileURL } from 'node:url'

export const FILES = [
  { name: 'eval-results.json', src: 'docs/eval-results.json', required: true },
  { name: 'eval-results.md', src: 'docs/eval-results.md', required: true },
  { name: 'README-claims.md', src: 'docs/README-claims.md', required: true },
  { name: 'hardening-results.md', src: 'docs/hardening-results.md', required: true },
  { name: 'SAFETY_LOG.md', src: 'docs/SAFETY_LOG.md', required: true },
  { name: 'backend-tests-full.md', src: 'backend/tests/results/latest-full.md', required: true },
  { name: 'backend-tests-latest.md', src: 'backend/tests/results/latest.md', required: false },
  { name: 'llm-live-eval.md', src: 'docs/llm-live-eval.md', required: false },
  { name: 'ai-selfcheck.md', src: 'docs/ai-selfcheck.md', required: false },
  { name: 'ai-selfcheck-history.md', src: 'docs/ai-selfcheck-history.md', required: false },
  { name: 'gold-results-live-first-run.md', src: 'docs/eval/gold-results-live-first-run.md', required: false },
  { name: 'redteam-live-first-run.md', src: 'docs/redteam-live-first-run.md', required: false },
  { name: 'gold-results-mock.md', src: 'docs/eval/gold-results-mock.md', required: false },
  { name: 'frontend-vitest.json', src: 'frontend/test-results/vitest.json', required: false },
  { name: 'frontend-playwright.json', src: 'frontend/test-results/playwright.json', required: false },
  { name: 'frontend-test-summary.json', src: 'docs/test-summary-frontend.json', required: true },
  { name: 'lighthouse-summary.json', src: 'docs/lighthouse-summary.json', required: false },
  { name: 'redteam-results.json', src: 'docs/redteam-results.json', required: false },
  { name: 'redteam-live.md', src: 'docs/redteam-live.md', required: false },
  { name: 'redteam-human.csv', src: 'docs/user-test/redteam-human.csv', required: false },
  { name: 'baseline-results.json', src: 'docs/baseline-results.json', required: false },
  { name: 'verification-counts.json', src: 'docs/data-verification/counts.json', required: false },
  { name: 'user-test-results.csv', src: 'docs/user-test/results.csv', required: false },
  { name: 'user-test-summary.md', src: 'docs/user-test/summary.md', required: false },
]

export class MissingProofError extends Error {}

/** @returns {{copied: string[], missing: {name: string, src: string, required: boolean}[]}} */
export function syncProof({ root, dest, strict = false, files = FILES } = {}) {
  const copied = []
  const missing = []
  rmSync(dest, { recursive: true, force: true })
  mkdirSync(dest, { recursive: true })
  for (const f of files) {
    const from = join(root, f.src)
    if (existsSync(from)) { copyFileSync(from, join(dest, f.name)); copied.push(f.name) } else missing.push({ name: f.name, src: f.src, required: f.required })
  }
  // The LATEST gold run: the newest timestamped `gold-results-live-<UTC>-<label>.md` that is not the first run (score_gold.py writes a new file every run, so no copying by hand).
  const evalDir = join(root, 'docs', 'eval')
  const latest = existsSync(evalDir) ? readdirSync(evalDir).filter((n) => /^gold-results-live-\d{8}T\d{6}Z-.+\.md$/.test(n) && !/-first-run\.md$/.test(n)).sort().at(-1) : null
  if (latest) { copyFileSync(join(evalDir, latest), join(dest, 'gold-results-live-final.md')); copied.push('gold-results-live-final.md') }
  else missing.push({ name: 'gold-results-live-final.md', src: 'docs/eval/gold-results-live-<time>-<label>.md', required: false })
  // The independent holdout: the newest LIVE results file (the rule-based "-mock" files are never shown as AI results).
  const hold = existsSync(evalDir) ? readdirSync(evalDir).filter((n) => /^holdout-results-\d{8}T\d{6}Z-.+\.md$/.test(n) && !n.endsWith('-mock.md')).sort().at(-1) : null
  if (hold) { copyFileSync(join(evalDir, hold), join(dest, 'holdout-results-latest.md')); copied.push('holdout-results-latest.md') }
  const requiredMissing = missing.filter((m) => m.required)
  if (strict && requiredMissing.length) {
    throw new MissingProofError(`Proof is missing: ${requiredMissing.map((m) => m.src).join(', ')}. Generate it first (backend: python scripts/run_evaluation.py --full; pytest) and run this again.`)
  }
  // The CURRENT prompt version, so the Proof page can say "not run on this version" for a live report made with another one.
  const pv = existsSync(join(root, 'backend/app/llm/prompts.py')) ? readFileSync(join(root, 'backend/app/llm/prompts.py'), 'utf8').match(/PROMPT_VERSION\s*=\s*"([^"]+)"/)?.[1] : null
  writeFileSync(join(dest, 'current-version.json'), JSON.stringify({ prompt_version: pv ?? null, llm_fingerprint: llmFingerprint(root) }) + '\n')
  writeFileSync(join(dest, 'manifest.json'), JSON.stringify({ copied, missing }, null, 2) + '\n')
  return { copied, missing }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const here = dirname(fileURLToPath(import.meta.url))
  const root = resolve(here, '..', '..')
  try {
    const r = syncProof({ root, dest: resolve(here, '..', 'public', 'proof-data'), strict: process.argv.includes('--strict') })
    console.log(`proof: copied ${r.copied.length} file(s)` + (r.missing.length ? `; not available: ${r.missing.map((m) => m.name).join(', ')}` : ''))
  } catch (e) {
    if (e instanceof MissingProofError) { console.error(`ERROR: ${e.message}`); process.exit(1) }
    throw e
  }
}
