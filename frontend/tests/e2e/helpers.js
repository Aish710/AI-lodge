import { expect } from '@playwright/test'

// The CORS header lets the map's one availability probe read the stubbed tile, as it can on the real server.
// 1x1 transparent PNG, used so tests do not depend on the public OpenStreetMap tile servers.
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64')

/** Collect console errors/warnings and uncaught exceptions. Assert with `expectClean(problems)`. */
export function watchConsole(page) {
  const problems = []
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) problems.push(`${m.type()}: ${m.text()}`) })
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`))
  return problems
}
export const expectClean = (problems) => expect(problems, problems.join('\n')).toEqual([])

export async function stubTiles(page) {
  await page.route('https://tile.openstreetmap.org/**', (r) => r.fulfill({ status: 200, contentType: 'image/png', body: PNG, headers: { 'access-control-allow-origin': '*' } }))
}

// Plan my trip runs the hotel comparison and then the planner; on a busy or slow machine that takes well over the default 15 s expect timeout.
export const PLAN_WAIT = 45_000

/** The new flow: choose the city's example on the Plan screen, press "Plan my trip", land on "Your trip". */
export async function planFromExample(page, kind = 'load-example') {
  await page.getByTestId(kind).click()
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
}
