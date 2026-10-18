import { tripSection, setupSection, disclose, allDays, mapView, timelineView } from './helpers.js'
// Serves the production build with the REAL generated _headers and _redirects (what a static host would apply) and checks that the
// Content-Security-Policy does not break the app: no violations, the map and the flow still work.
import { createServer } from 'node:http'
import { existsSync, readFileSync } from 'node:fs'
import { extname, join, resolve } from 'node:path'
import { expect, test } from '@playwright/test'
import { stubTiles } from './helpers.js'

const DIST = resolve(process.cwd(), 'dist-e2e')
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json', '.woff2': 'font/woff2', '.md': 'text/markdown' }

function parseHeaders(text) {
  const out = {}
  let current = null
  for (const line of text.split('\n')) {
    if (!line.trim()) continue
    if (!line.startsWith(' ')) { current = line.trim(); out[current] = {}; continue }
    const i = line.indexOf(':')
    out[current][line.slice(0, i).trim()] = line.slice(i + 1).trim()
  }
  return out
}

let server, base, rules
test.beforeAll(async () => {
  rules = parseHeaders(readFileSync(join(DIST, '_headers'), 'utf8'))
  expect(readFileSync(join(DIST, '_redirects'), 'utf8').trim()).toBe('/*  /index.html  200')
  server = createServer((req, res) => {
    const path = decodeURIComponent(new URL(req.url, 'http://x').pathname)
    let file = join(DIST, path)
    if (!existsSync(file) || path.endsWith('/')) file = join(DIST, 'index.html') // the SPA rewrite
    for (const [h, v] of Object.entries(rules['/*'])) res.setHeader(h, v)
    res.setHeader('Content-Type', TYPES[extname(file)] ?? 'application/octet-stream')
    res.end(readFileSync(file))
  })
  await new Promise((r) => server.listen(4175, r))
  base = 'http://localhost:4175'
})
test.afterAll(() => server?.close())

test('the generated CSP allows only self, the tile server and the API, and the app works under it', async ({ page }) => {
  const csp = rules['/*']['Content-Security-Policy']
  expect(csp).toContain("script-src 'self'")
  expect(csp).toContain('connect-src \'self\' http://localhost:8010')
  expect(csp).toContain('img-src \'self\' data: https://tile.openstreetmap.org')
  expect(csp).not.toMatch(/\*|unsafe-eval|script-src[^;]*unsafe-inline/)
  expect(rules['/*']['X-Content-Type-Options']).toBe('nosniff')
  expect(rules['/*']['Referrer-Policy']).toBe('no-referrer')

  const problems = []
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) problems.push(m.text()) })
  page.on('pageerror', (e) => problems.push(e.message))
  await stubTiles(page)
  await page.goto(base + '/')
  await disclose(page, 'worked-examples')
  await page.getByTestId('load-impossible').click()
  await page.getByTestId('plan-trip').click()                  // SPA route reached through the app
  await expect(page.getByTestId('conflict-panel')).toBeVisible()
  await page.getByTestId('conflict-panel').locator('button[data-kind=allow_unknown_hours]').click()
  await expect(page.locator('.leaflet-container .pin').first()).toBeVisible()
  await page.goto(base + '/proof')                          // deep link: needs the rewrite
  await expect(page.getByTestId('scenarios')).toBeVisible()
  await page.goto(base + '/no/such/path')
  await expect(page.getByTestId('not-found')).toBeVisible()
  expect(problems.filter((p) => /Content Security Policy|CSP|Refused to/i.test(p))).toEqual([])
  expect(problems).toEqual([])
})
