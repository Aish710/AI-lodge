import { afterAll, describe, expect, it } from 'vitest'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { execFileSync } from 'node:child_process'
import { ReleaseValidationError, validateRelease } from '../../scripts/validate-release.mjs'

const tmp = []
const mk = () => { const d = mkdtempSync(join(tmpdir(), 'rel-')); tmp.push(d); return d }
afterAll(() => tmp.forEach((d) => rmSync(d, { recursive: true, force: true })))

function minimalDist(rev = null) {
  const root = mk()
  const dist = join(root, 'dist')
  mkdirSync(join(dist, 'proof-data'), { recursive: true })
  writeFileSync(join(dist, '_headers'), '/*\n  Content-Security-Policy: default-src self\n')
  writeFileSync(join(dist, '_redirects'), '/*  /index.html  200\n')
  writeFileSync(join(dist, 'proof-data', 'manifest.json'), '{}\n')
  writeFileSync(join(dist, 'proof-data', 'backend-tests-full.md'), '# full\n')
  writeFileSync(join(dist, 'proof-data', 'hardening-results.md'), '# hardening\n')
  writeFileSync(join(dist, 'proof-data', 'eval-results.json'), JSON.stringify({ meta: { commit: rev ?? 'unknown' } }))
  writeFileSync(join(dist, 'proof-data', 'frontend-test-summary.json'), JSON.stringify({ git_hash: rev ?? 'unknown', suites: [] }))
  return { root, dist }
}

describe('validate-release', () => {
  it('requires an HTTPS production API URL', () => {
    const { root, dist } = minimalDist()
    expect(() => validateRelease({ root, dist, apiBase: '' })).toThrow(ReleaseValidationError)
    expect(() => validateRelease({ root, dist, apiBase: 'http://localhost:8000' })).toThrow(/HTTPS/)
  })
  it('rejects possible secrets in built assets', () => {
    const { root, dist } = minimalDist()
    writeFileSync(join(dist, 'assets.js'), 'const key="sk-ant-FAKEFAKEFAKEFAKEFAKEFAKEFAKE"')
    expect(() => validateRelease({ root, dist, apiBase: 'https://api.example.com' })).toThrow(/possible secret/)
  })
  it('passes with required artifacts and an HTTPS API URL', () => {
    const { root, dist } = minimalDist()
    expect(validateRelease({ root, dist, apiBase: 'https://api.example.com' })).toMatchObject({ ok: true, apiOrigin: 'https://api.example.com' })
  })
  it('rejects a frontend test summary from another revision', () => {
    const rev = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: '..', encoding: 'utf8' }).trim()
    const { dist } = minimalDist(rev)
    writeFileSync(join(dist, 'proof-data', 'frontend-test-summary.json'), JSON.stringify({ git_hash: 'different-front', suites: [] }))
    expect(() => validateRelease({ root: '..', dist, apiBase: 'https://api.example.com' })).toThrow(/frontend test summary/)
  })
})
