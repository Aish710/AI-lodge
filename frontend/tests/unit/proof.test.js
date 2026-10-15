import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { MissingProofError, syncProof } from '../../scripts/sync-proof.mjs'
import { buildSummary } from '../../scripts/write-test-summaries.mjs'
import { loadProof, readThisFirst, THRESHOLDS } from '../../src/lib/proof.js'
import { countUserTestRows, parseBlocks, parseClaims, parseRiskTable, plain, sectionBullets, testSummary } from '../../src/lib/mdparse.js'
import { createMemoryHistory, createRouter } from 'vue-router'
import Proof from '../../src/views/Proof.vue'

const testRouter = () => createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })

const ROOT = resolve(process.cwd(), '..')
const read = (p) => readFileSync(join(ROOT, p), 'utf8')
const tmp = []
const mk = () => { const d = mkdtempSync(join(tmpdir(), 'ev-')); tmp.push(d); return d }
afterAll(() => tmp.forEach((d) => rmSync(d, { recursive: true, force: true })))

describe('sync-proof script', () => {
  it('copies the generated files and records what is missing in the manifest (optional files are not an error)', () => {
    const dest = mk()
    const r = syncProof({ root: ROOT, dest })
    for (const n of ['eval-results.json', 'eval-results.md', 'README-claims.md', 'hardening-results.md', 'SAFETY_LOG.md', 'backend-tests-full.md', 'frontend-test-summary.json']) {
      expect(r.copied).toContain(n)
      expect(readFileSync(join(dest, n), 'utf8').length).toBeGreaterThan(100)
    }
    const manifest = JSON.parse(readFileSync(join(dest, 'manifest.json'), 'utf8'))
    expect(manifest.copied).toEqual(r.copied)
    expect(manifest.missing.every((m) => m.required === false)).toBe(true)
  })
  it('fails clearly in --strict mode when a required file is missing, naming it', () => {
    const root = mk()
    mkdirSync(join(root, 'docs'))
    writeFileSync(join(root, 'docs', 'README-claims.md'), 'x')
    expect(() => syncProof({ root, dest: mk(), strict: true })).toThrow(MissingProofError)
    expect(() => syncProof({ root, dest: mk(), strict: true })).toThrow(/docs\/eval-results\.json/)
  })
  it('without --strict it still writes a manifest listing the missing required files, so the page can say so', () => {
    const root = mk()
    const dest = mk()
    const r = syncProof({ root, dest })
    expect(r.copied).toEqual([])
    expect(r.missing.filter((m) => m.required).length).toBeGreaterThan(0)
    expect(existsSync(join(dest, 'manifest.json'))).toBe(true)
  })
})

describe('frontend test summary script', () => {
  it('summarises Vitest and Playwright result files with the git hash', () => {
    const s = buildSummary({ gitHash: 'abc123', now: '2026-10-14T00:00:00.000Z' })
    expect(s.git_hash).toBe('abc123')
    expect(s.suites.map((x) => x.suite)).toContain('Vitest')
    expect(s.suites.map((x) => x.suite)).toContain('Playwright')
    expect(s.suites.every((x) => x.total === x.passed + x.failed + x.skipped)).toBe(true)
  })
})

describe('markdown readers use plain text and the real files', () => {
  it('plain() strips markdown and never produces HTML', () => {
    expect(plain('**bold** `code` [text](http://x) *it*')).toBe('bold code text it')
  })
  it('reads every risk row from SAFETY_LOG.md', () => {
    const rows = parseRiskTable(read('docs/SAFETY_LOG.md'))
    expect(rows.length).toBeGreaterThanOrEqual(74)
    expect(rows[0]).toMatchObject({ n: 1 })
    expect(rows.every((x) => x.risk && x.safeguard && x.test)).toBe(true)
    expect(new Set(rows.map((x) => x.n)).size).toBe(rows.length)
  })
  it('reads the claim sentences verbatim', () => {
    const md = read('docs/README-claims.md')
    const claims = parseClaims(md)
    expect(claims.length).toBeGreaterThanOrEqual(10)
    for (const c of claims) expect(md).toContain(c.text)
  })
  it('reads the "do not show" bullets and the test summary header', () => {
    expect(sectionBullets(read('docs/eval-results.md'), 'WHAT THESE NUMBERS DO NOT SHOW').length).toBeGreaterThanOrEqual(8)
    const s = testSummary(read('backend/tests/results/latest-full.md'))
    expect(s.total).toBe(s.passed + s.failed)
    expect(s.total).toBeGreaterThan(200)
  })
  it('turns tables into blocks', () => {
    const b = parseBlocks('# T\n\n| A | B |\n|---|---|\n| 1 | **2** |\n\n- x\n- y\n\ntext')
    expect(b.map((x) => x.type)).toEqual(['h', 'table', 'ul', 'p'])
    expect(b[1]).toEqual({ type: 'table', head: ['A', 'B'], rows: [['1', '2']] })
  })
})

function servedFrom(dir) {
  return vi.fn(async (url) => {
    const name = String(url).replace('/proof-data/', '')
    const f = join(dir, name)
    if (!existsSync(f)) return { ok: false, status: 404, text: async () => '', json: async () => ({}) }
    const t = readFileSync(f, 'utf8')
    return { ok: true, status: 200, text: async () => t, json: async () => JSON.parse(t) }
  })
}

describe('loadProof', () => {
  let dir
  beforeAll(() => { dir = mk(); syncProof({ root: ROOT, dest: dir }) })
  it('says so when the proof is not part of the build (no placeholders)', async () => {
    const r = await loadProof(async () => ({ ok: false, status: 404 }))
    expect(r.state).toBe('unavailable')
    expect(r.reason).toMatch(/not part of this build/)
    expect(r.reason).toMatch(/sync-proof/)
  })
  it('says so when a listed file cannot be read', async () => {
    const f = servedFrom(dir)
    const broken = vi.fn(async (u) => (String(u).endsWith('eval-results.json') ? { ok: true, status: 200, text: async () => '{not json' } : f(u)))
    const r = await loadProof(broken)
    expect(r.state).toBe('unavailable')
    expect(r.reason).toMatch(/could not be read/)
  })
  it('loads the real files', async () => {
    const r = await loadProof(servedFrom(dir))
    expect(r.state).toBe('ready')
    expect(r.data.results.scenarios).toHaveLength(15)
    expect(r.data.risks.length).toBeGreaterThanOrEqual(74)
    expect(r.data.tests.backend.total).toBeGreaterThan(200)
    expect(r.data.tests.backend.runType).toMatch(/full backend suite/)
    expect(r.data.live).toBeNull()
  })
  it('derives the weak-result notes from the data, not from typed numbers', async () => {
    const r = await loadProof(servedFrom(dir))
    const m = r.data.results.metrics
    const notes = readThisFirst(m, m.n_trips)
    expect(notes.length).toBeGreaterThanOrEqual(3)
    const joined = notes.join(' ')
    expect(joined).toContain(`only ${m.travel.naive.n_comparable} of ${m.travel.naive.n_trips} trips`)
    expect(THRESHOLDS.smallSubsetShare).toBe(0.5)
    // a fabricated metrics object changes the notes (they are computed)
    const calm = JSON.parse(JSON.stringify(m)); calm.travel.naive.n_comparable = calm.travel.naive.n_trips; calm.travel.nn.n_comparable = calm.travel.nn.n_trips; calm.travel.nn.equal = 0
    expect(readThisFirst(calm, calm.n_trips).join(' ')).not.toContain('Small comparable subset')
  })
})

describe('Proof page', () => {
  let dir
  beforeAll(() => { dir = mk(); syncProof({ root: ROOT, dest: dir }) })
  it('renders the real proof: scenarios, metrics with N, not-shown list, risks, claims verbatim, hash and date', async () => {
    vi.stubGlobal('fetch', servedFrom(dir))
    const w = mount(Proof, { global: { plugins: [testRouter()], stubs: { 'router-link': true } } })
    await flushPromises(); await flushPromises()
    const results = JSON.parse(readFileSync(join(dir, 'eval-results.json'), 'utf8'))
    expect(w.findAll('[data-testid^=scn-]')).toHaveLength(15)
    expect(w.get('[data-testid=proof-commit]').text()).toBe(results.meta.commit)
    expect(w.get('[data-testid=proof-meta]').text()).toContain(results.meta.date)
    expect(w.get('[data-testid=read-first]').text()).toContain('Small comparable subset')
    expect(w.get('[data-testid=travel-table]').text()).toContain(`${results.metrics.travel.nn.n_comparable} of ${results.metrics.travel.nn.n_trips}`)
    expect(w.get('[data-testid=hotel-value]').text()).toContain('fictional')
    expect(w.get('[data-testid=not-shown]').text()).toContain('Sample data')
    expect(w.get('[data-testid=not-shown]').text()).toContain('No significance testing')
    expect(w.get('[data-testid=not-shown]').text()).toContain('judgement-call modelling constant')
    const claims = readFileSync(join(dir, 'README-claims.md'), 'utf8')
    for (const li of w.findAll('[data-testid=claims] li')) expect(claims).toContain(li.text())
    await w.get('[data-testid=toggle-risks]').trigger('click')
    expect(w.findAll('[data-testid=risk-table] tbody tr').length).toBeGreaterThanOrEqual(74)
    expect(w.get('[data-testid=live-not-run]').text()).toContain('Not run yet')
    expect(w.get('[data-testid=hardening]').text()).toContain('abuse cases passed')
    expect(w.html()).not.toMatch(/<script/i)
    vi.unstubAllGlobals()
  })
  it('says the proof is missing instead of showing placeholders', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 404 })))
    const w = mount(Proof, { global: { plugins: [testRouter()], stubs: { 'router-link': true } } })
    await flushPromises()
    expect(w.get('[data-testid=proof-unavailable]').text()).toContain('Proof is not available in this build')
    expect(w.find('[data-testid=scenarios]').exists()).toBe(false)
    vi.unstubAllGlobals()
  })
  it('warns when the proof run came from uncommitted code', async () => {
    const bad = mk(); syncProof({ root: ROOT, dest: bad })
    const j = JSON.parse(readFileSync(join(bad, 'eval-results.json'), 'utf8')); j.meta.commit = 'abc1234 + uncommitted changes'
    writeFileSync(join(bad, 'eval-results.json'), JSON.stringify(j))
    vi.stubGlobal('fetch', servedFrom(bad))
    const w = mount(Proof, { global: { plugins: [testRouter()], stubs: { 'router-link': true } } })
    await flushPromises(); await flushPromises()
    expect(w.get('[data-testid=dirty-warning]').text()).toContain('uncommitted')
    vi.unstubAllGlobals()
  })
  it('warns when frontend tests were run on a different version', async () => {
    const bad = mk(); syncProof({ root: ROOT, dest: bad })
    const j = JSON.parse(readFileSync(join(bad, 'frontend-test-summary.json'), 'utf8')); j.git_hash = 'different-front'
    writeFileSync(join(bad, 'frontend-test-summary.json'), JSON.stringify(j))
    vi.stubGlobal('fetch', servedFrom(bad))
    const w = mount(Proof, { global: { plugins: [testRouter()], stubs: { 'router-link': true } } })
    await flushPromises(); await flushPromises()
    expect(w.get('[data-testid=frontend-stale-warning]').text()).toContain('Frontend tests run on a different version')
    vi.unstubAllGlobals()
  })
})

describe('User test card (never pre-filled)', () => {
  const header = 'participant_id,date,city,completed_task,task_seconds,manual_estimate_minutes,q1_clear,q2_trust,q3_understood,q4_useful,q5_would_use,quote'
  const mountWith = async (dir) => {
    vi.stubGlobal('fetch', servedFrom(dir))
    const w = mount(Proof, { global: { plugins: [testRouter()], stubs: { 'router-link': true } } })
    await flushPromises(); await flushPromises()
    return w
  }
  it('counts only data rows, never the header', () => {
    expect(countUserTestRows(header + '\n')).toBe(0)
    expect(countUserTestRows(header + '\n,,,,,,,,,,,\n')).toBe(0)
    expect(countUserTestRows(header + '\nP1,d,tokyo,yes,100,20,3,3,3,3,3,ok\nP2,d,tokyo,no,,10,1,1,1,1,1,\n')).toBe(2)
    expect(countUserTestRows(undefined)).toBe(0)
  })
  it('with the shipped (empty) template the card says "Not run yet" and shows no figures', async () => {
    const dir = mk(); syncProof({ root: ROOT, dest: dir })
    expect(readFileSync(join(dir, 'user-test-results.csv'), 'utf8').trim()).toBe(header)
    const w = await mountWith(dir)
    expect(w.get('[data-testid=user-test]').text()).toContain('Not run yet')
    expect(w.find('[data-testid=user-test-none]').exists()).toBe(true)
    expect(w.get('[data-testid=user-test]').text()).not.toMatch(/\d+ participant/)
    vi.unstubAllGlobals()
  })
  it('when the results file is missing altogether it still says "Not run yet"', async () => {
    const dir = mk(); syncProof({ root: ROOT, dest: dir })
    rmSync(join(dir, 'user-test-results.csv')); rmSync(join(dir, 'user-test-summary.md'))
    const m = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8')); m.copied = m.copied.filter((n) => !n.startsWith('user-test'))
    writeFileSync(join(dir, 'manifest.json'), JSON.stringify(m))
    const w = await mountWith(dir)
    expect(w.find('[data-testid=user-test-none]').exists()).toBe(true)
    vi.unstubAllGlobals()
  })
  it('with rows it shows N and the generated summary (quotes verbatim, as plain text)', async () => {
    const dir = mk(); syncProof({ root: ROOT, dest: dir })
    writeFileSync(join(dir, 'user-test-results.csv'), header + '\nP1,d,tokyo,yes,100,20,3,3,3,3,3,Too many <b>boxes</b>\n')
    writeFileSync(join(dir, 'user-test-summary.md'), '# User test summary\n\nN = 1 participants.\n\n## What people said (verbatim)\n\n- "Too many <b>boxes</b>" (P1)\n')
    const w = await mountWith(dir)
    const card = w.get('[data-testid=user-test]')
    expect(w.find('[data-testid=user-test-none]').exists()).toBe(false)
    expect(card.text()).toContain('1 participant')
    expect(card.text()).toContain('Too many <b>boxes</b>')      // shown as text
    expect(card.html()).not.toContain('<b>boxes</b>')           // never rendered as HTML
    vi.unstubAllGlobals()
  })
})
