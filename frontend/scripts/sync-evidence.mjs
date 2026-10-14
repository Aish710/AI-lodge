// Copies the generated evidence files into public/evidence-data/ so the built app can show them. Nothing is edited or typed by hand.
// Usage: node scripts/sync-evidence.mjs [--strict]
//   default: copies what exists, writes manifest.json listing what is missing (the Evidence page then says so instead of showing placeholders)
//   --strict: exits 1 with a clear message if any REQUIRED file is missing (use before a submission build)
import { copyFileSync, existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
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
  { name: 'frontend-vitest.json', src: 'frontend/test-results/vitest.json', required: false },
  { name: 'frontend-playwright.json', src: 'frontend/test-results/playwright.json', required: false },
  { name: 'lighthouse-summary.json', src: 'docs/lighthouse-summary.json', required: false },
]

export class MissingEvidenceError extends Error {}

/** @returns {{copied: string[], missing: {name: string, src: string, required: boolean}[]}} */
export function syncEvidence({ root, dest, strict = false, files = FILES } = {}) {
  const copied = []
  const missing = []
  rmSync(dest, { recursive: true, force: true })
  mkdirSync(dest, { recursive: true })
  for (const f of files) {
    const from = join(root, f.src)
    if (existsSync(from)) { copyFileSync(from, join(dest, f.name)); copied.push(f.name) } else missing.push({ name: f.name, src: f.src, required: f.required })
  }
  const requiredMissing = missing.filter((m) => m.required)
  if (strict && requiredMissing.length) {
    throw new MissingEvidenceError(`Evidence is missing: ${requiredMissing.map((m) => m.src).join(', ')}. Generate it first (backend: python scripts/run_evaluation.py --full; pytest) and run this again.`)
  }
  writeFileSync(join(dest, 'manifest.json'), JSON.stringify({ copied, missing }, null, 2) + '\n')
  return { copied, missing }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const here = dirname(fileURLToPath(import.meta.url))
  const root = resolve(here, '..', '..')
  try {
    const r = syncEvidence({ root, dest: resolve(here, '..', 'public', 'evidence-data'), strict: process.argv.includes('--strict') })
    console.log(`evidence: copied ${r.copied.length} file(s)` + (r.missing.length ? `; not available: ${r.missing.map((m) => m.name).join(', ')}` : ''))
  } catch (e) {
    if (e instanceof MissingEvidenceError) { console.error(`ERROR: ${e.message}`); process.exit(1) }
    throw e
  }
}
