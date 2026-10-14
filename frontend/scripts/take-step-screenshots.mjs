// Every step (Trip, Sights, Hotels, Itinerary) for two different cities, on desktop and on a phone, plus the Proof and How it works pages.
// Real backend (sample mode) and a production build. Output: docs/screenshots/steps/<city>-<step>-<desktop|mobile>.png
// Usage (from frontend/):  node scripts/take-step-screenshots.mjs [--offline-tiles]
import { spawn } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const here = dirname(fileURLToPath(import.meta.url))
const FRONT = resolve(here, '..')
const BACK = resolve(FRONT, '../backend')
const OUT = resolve(FRONT, '../docs/screenshots/steps')
const API = 'http://localhost:8010'
const APP = 'http://localhost:4181'
const offlineTiles = process.argv.includes('--offline-tiles')
const CITIES = ['tokyo', 'seoul']
const VIEWPORTS = { desktop: { width: 1280, height: 900 }, mobile: { width: 375, height: 812 } }
mkdirSync(OUT, { recursive: true })

const procs = []
const run = (cmd, cwd, env = {}) => { const p = spawn(cmd, { cwd, shell: true, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p) }
const stopAll = () => procs.forEach((p) => { try { process.kill(-p.pid) } catch { /* already gone */ } })
async function waitFor(url, ms = 120_000) {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) { try { if ((await fetch(url)).ok) return } catch { /* not up yet */ } await new Promise((r) => setTimeout(r, 400)) }
  throw new Error(`timed out waiting for ${url}`)
}
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64')
const tilesLoaded = (page) => page.waitForFunction(() => !document.querySelector('.leaflet-container') || (document.querySelectorAll('.leaflet-tile-loaded').length > 0 && !document.querySelector('.leaflet-tile:not(.leaflet-tile-loaded)')), null, { timeout: 15_000 }).catch(() => {})
const wait = (locator, timeout = 60_000) => locator.waitFor({ state: 'visible', timeout })
const written = []
async function shot(page, name) {
  await page.evaluate(() => window.scrollTo(0, 0))
  await tilesLoaded(page)
  await page.waitForTimeout(300)
  await page.screenshot({ path: join(OUT, name), fullPage: true })
  written.push(name)
  console.log('wrote', name)
}

async function flow(browser, city, device) {
  const ctx = await browser.newContext({ viewport: VIEWPORTS[device], deviceScaleFactor: 1, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  if (offlineTiles) await page.route('https://tile.openstreetmap.org/**', (r) => r.fulfill({ status: 200, contentType: 'image/png', body: PNG }))
  const tag = `${city}`
  await page.goto(APP)
  await wait(page.getByTestId('city-chip'))
  if (city !== 'tokyo') { await page.getByTestId(`city-${city}`).click(); await page.getByTestId('city-chip').filter({ hasText: city === 'seoul' ? 'Seoul' : city }).waitFor() }
  await shot(page, `${tag}-1-trip-${device}.png`)
  await page.getByTestId('next-wishlist').click()
  await wait(page.locator('article[data-testid^="card-"]').first())
  await page.locator('article[data-testid^="card-"]').first().locator('label', { hasText: 'Must visit' }).click()
  await shot(page, `${tag}-2-sights-${device}.png`)
  await page.getByTestId('next-hotels').click()
  await wait(page.getByTestId('comparison-table'))
  await wait(page.getByTestId('sensitivity'), 90_000).catch(() => {})
  await shot(page, `${tag}-3-hotels-${device}.png`)
  await page.locator('button.btn-primary', { hasText: 'Use this hotel' }).click()
  await wait(page.getByTestId('timeline'))
  await wait(page.locator('.leaflet-container .pin').first())
  await shot(page, `${tag}-4-itinerary-${device}.png`)
  if (city === CITIES[0]) {
    await page.goto(`${APP}/proof`); await wait(page.getByTestId('scn-15')); await shot(page, `proof-${device}.png`)
    await page.goto(`${APP}/how-it-works`); await wait(page.getByTestId('architecture')); await shot(page, `how-it-works-${device}.png`)
  }
  await ctx.close()
}

try {
  run('.venv/bin/uvicorn app.main:app --port 8010 --log-level warning', BACK, { RATE_LIMIT_EXPENSIVE_PER_MIN: '500', RATE_LIMIT_PER_MIN: '1000', RATE_LIMIT_CHEAP_PER_MIN: '5000', LLM_API_KEY: '', LLM_MODEL: '', ALLOWED_ORIGINS: APP, SOLVER_CONCURRENCY: '1' })
  run(`node scripts/sync-proof.mjs && VITE_API_BASE_URL=${API} npx vite build --outDir dist-steps && npx vite preview --outDir dist-steps --port 4181 --strictPort`, FRONT)
  await waitFor(`${API}/health`)
  await waitFor(APP)
  const browser = await chromium.launch()
  for (const city of CITIES) for (const device of Object.keys(VIEWPORTS)) await flow(browser, city, device)
  await browser.close()
  console.log(`${written.length} screenshots written to docs/screenshots/steps/`)
} finally {
  stopAll()
}
