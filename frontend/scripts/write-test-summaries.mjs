import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { execFileSync } from 'node:child_process'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..', '..')

function rev() {
  try { return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim() } catch { return null }
}

function readJson(rel) {
  const p = resolve(root, rel)
  if (!existsSync(p)) return null
  return JSON.parse(readFileSync(p, 'utf8'))
}

function vitest(j) {
  if (!j) return null
  const duration = (j.testResults ?? []).reduce((sum, r) => sum + Math.max(0, (r.endTime ?? r.startTime ?? 0) - (r.startTime ?? 0)), 0)
  return {
    suite: 'Vitest',
    total: j.numTotalTests ?? 0,
    passed: j.numPassedTests ?? 0,
    failed: j.numFailedTests ?? 0,
    skipped: (j.numPendingTests ?? 0) + (j.numTodoTests ?? 0),
    duration_ms: duration,
    timestamp: j.startTime ? new Date(j.startTime).toISOString() : new Date().toISOString(),
  }
}

function playwright(j) {
  if (!j) return null
  return {
    suite: 'Playwright',
    total: (j.stats?.expected ?? 0) + (j.stats?.unexpected ?? 0) + (j.stats?.skipped ?? 0) + (j.stats?.flaky ?? 0),
    passed: (j.stats?.expected ?? 0) + (j.stats?.flaky ?? 0),
    failed: j.stats?.unexpected ?? 0,
    skipped: j.stats?.skipped ?? 0,
    duration_ms: Math.round(j.stats?.duration ?? 0),
    timestamp: j.stats?.startTime ?? new Date().toISOString(),
  }
}

export function buildSummary({ gitHash = rev(), now = new Date().toISOString() } = {}) {
  const suites = [vitest(readJson('frontend/test-results/vitest.json')), playwright(readJson('frontend/test-results/playwright.json'))].filter(Boolean)
  return { timestamp: now, git_hash: gitHash, suites }
}

export function writeSummary({ out = resolve(root, 'docs', 'test-summary-frontend.json'), summary = buildSummary() } = {}) {
  mkdirSync(dirname(out), { recursive: true })
  writeFileSync(out, JSON.stringify(summary, null, 2) + '\n')
  return summary
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const summary = writeSummary()
  console.log(`frontend test summary: ${summary.suites.length} suite(s), ${summary.git_hash ?? 'unknown revision'}`)
}
