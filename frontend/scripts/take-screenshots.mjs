// Produces named, consistent PNGs in docs/screenshots/ from the REAL backend (sample mode) and a production build of the frontend.
// Usage (from frontend/):  node scripts/take-screenshots.mjs [--offline-tiles]
// It starts its own servers (backend :8010, frontend preview :4180), so nothing needs to be running. Map tiles come from OpenStreetMap
// when the network allows; with --offline-tiles (or if tiles fail) a blank tile is used and the screenshot map background is empty.
import { spawn } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const here = dirname(fileURLToPath(import.meta.url))
const FRONT = resolve(here, '..')
const BACK = resolve(FRONT, '../backend')
const OUT = resolve(FRONT, '../docs/screenshots')
const API = 'http://localhost:8010'
const APP = 'http://localhost:4180'
const offlineTiles = process.argv.includes('--offline-tiles')
mkdirSync(OUT, { recursive: true })

const procs = []
const run = (cmd, cwd, env = {}) => { const p = spawn(cmd, { cwd, shell: true, env: { ...process.env, ...env }, stdio: 'ignore', detached: true }); procs.push(p); return p }
const stopAll = () => procs.forEach((p) => { try { process.kill(-p.pid) } catch { /* already gone */ } })
async function waitFor(url, ms = 90_000) {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) { try { if ((await fetch(url)).ok) return } catch { /* not up yet */ } await new Promise((r) => setTimeout(r, 400)) }
  throw new Error(`timed out waiting for ${url}`)
}

const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64')
const shot = async (page, name, opts = {}) => { await page.screenshot({ path: join(OUT, name), ...opts }); console.log('wrote', name) }

async function newPage(browser, viewport) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  if (offlineTiles) await page.route('https://tile.openstreetmap.org/**', (r) => r.fulfill({ status: 200, contentType: 'image/png', body: PNG }))
  return page
}
const tilesLoaded = (page) => page.waitForFunction(() => !document.querySelector('.leaflet-container') || document.querySelectorAll('.leaflet-tile-loaded').length > 0 && !document.querySelector('.leaflet-tile:not(.leaflet-tile-loaded)'), null, { timeout: 15_000 }).catch(() => {})
const settle = async (page) => { await page.waitForLoadState('networkidle').catch(() => {}); await tilesLoaded(page); await page.waitForTimeout(500) }
/** Full-page capture without relying on Playwright's resize-and-capture (which changes the map size while tiles are loading). */
async function fullShot(page, name) {
  const w = page.viewportSize().width
  const h = await page.evaluate(() => Math.ceil(document.documentElement.scrollHeight))
  await page.setViewportSize({ width: w, height: h })
  await settle(page)
  await shot(page, name)
}

try {
  run('.venv/bin/uvicorn app.main:app --port 8010 --log-level warning', BACK, { RATE_LIMIT_EXPENSIVE_PER_MIN: '500', RATE_LIMIT_PER_MIN: '1000', RATE_LIMIT_CHEAP_PER_MIN: '5000', LLM_API_KEY: '', LLM_MODEL: '', ALLOWED_ORIGINS: APP })
  run(`VITE_API_BASE_URL=${API} npx vite build --outDir dist-shots && npx vite preview --outDir dist-shots --port 4180 --strictPort`, FRONT)
  await waitFor(`${API}/health`)
  await waitFor(APP, 120_000)
  const browser = await chromium.launch()

  // 1 create trip
  let page = await newPage(browser, { width: 1280, height: 900 })
  await page.goto(APP)
  await page.getByRole('heading', { name: 'Plan your trip' }).waitFor()
  await settle(page)
  await fullShot(page, '01-create-trip.png')

  // 2 wishlist (a few choices made so the states are visible)
  await page.getByTestId('next-wishlist').click()
  await page.getByTestId('card-senso_ji').waitFor()
  await page.getByTestId('card-senso_ji').locator('label', { hasText: 'Must visit' }).click()
  await page.getByTestId('card-meiji_jingu').locator('label', { hasText: 'Must visit' }).click()
  await page.getByTestId('card-shibuya_sky').locator('label', { hasText: 'Not interested' }).click()
  await settle(page)
  await fullShot(page, '02-wishlist.png')

  // 3 hotel comparison (example trip, wait for the sensitivity section)
  await page.goto(APP)
  await page.getByTestId('load-example').click()
  await page.getByTestId('comparison-table').waitFor()
  await page.getByTestId('sensitivity').waitFor({ timeout: 60_000 })
  await settle(page)
  await fullShot(page, '03-hotel-comparison.png')

  // 4 + 5 itinerary with map, feasibility report
  await page.locator('button.btn-primary', { hasText: 'Use this hotel' }).click()
  await page.getByTestId('timeline').waitFor()
  await page.locator('.leaflet-container .pin').first().waitFor()
  await settle(page)
  await fullShot(page, '04-itinerary-map.png')
  await page.getByTestId('feasibility-report').scrollIntoViewIfNeeded()
  await shot(page, '05-feasibility-report.png', { clip: await page.getByTestId('feasibility-report').boundingBox() })

  // 7 impossible trip -> conflict panel
  await page.goto(APP)
  await page.getByTestId('load-impossible').click()
  await page.getByTestId('conflict-panel').waitFor()
  await settle(page)
  await fullShot(page, '07-impossible-conflict.png')

  // 9 mobile itinerary (375 px)
  const mobile = await newPage(browser, { width: 375, height: 812 })
  await mobile.goto(APP)
  await mobile.getByTestId('load-example').click()
  await mobile.locator('button.btn-primary', { hasText: 'Use this hotel' }).click()
  await mobile.getByTestId('timeline').waitFor()
  await mobile.locator('.leaflet-container .pin').first().waitFor()
  await settle(mobile)
  await fullShot(mobile, '09-mobile-itinerary.png')
  await browser.close()
} finally {
  stopAll()
}
