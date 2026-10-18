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
  await disclose(page, 'worked-examples')
  await page.getByTestId(kind).click()
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
}

// Navigate through the consumer interface before exercising a tool. Tests retain
// their API/safety assertions; this only replaces the former single long page.
export async function tripSection(page, section) {
  const tab = page.getByTestId(`trip-tab-${section}`)
  if (await tab.count() && await tab.getAttribute('aria-selected') !== 'true') await tab.click()
}
export async function setupSection(page, section) {
  const step = page.getByTestId(`setup-${section}`)
  if (await step.count() && await step.getAttribute('aria-current') !== 'step') await step.click()
}
export async function disclose(page, id) {
  const details = page.getByTestId(id)
  if (await details.count() && await details.getAttribute('open') === null) await details.locator('summary').first().click()
}
export async function allDays(page) {
  if (await page.getByTestId('daychip-all').count()) await page.getByTestId('daychip-all').click()
}
export async function mapView(page) {
  await tripSection(page, 'itinerary')
  const button = page.getByRole('button', { name: 'Map', exact: true })
  if (page.viewportSize()?.width < 768 && await button.getAttribute('aria-pressed') !== 'true') await button.click()
}
export async function timelineView(page) {
  await tripSection(page, 'itinerary')
  const button = page.getByRole('button', { name: 'Timeline', exact: true })
  if (page.viewportSize()?.width < 768 && await button.getAttribute('aria-pressed') !== 'true') await button.click()
}
