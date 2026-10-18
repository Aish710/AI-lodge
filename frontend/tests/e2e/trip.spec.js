// Final phase: themes, cost panel, day cards, event cards, connectors, map filters and linking, in a real browser against the real backend.
import { expect, test } from '@playwright/test'
import { expectClean, planFromExample, PLAN_WAIT, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })
const pinsOf = (page) => page.locator('[data-testid=trip-map] .leaflet-marker-icon')

for (const city of ['seoul', 'kuala_lumpur']) {
  test(`${city}: choose a theme, select sights, plan, see the theme mix and the cost per day`, async ({ page }) => {
    const problems = watchConsole(page)
    await page.goto('/')
    await page.getByTestId(`city-${city}`).click()
    await expect(page.locator('article[data-testid^="card-"]').first()).toBeVisible()
    const all = await page.locator('article[data-testid^="card-"]').count()
    await expect(page.getByTestId('tab-all')).toContainText(String(all))
    // a theme tab filters the grid; a theme with one sight still shows, marked limited
    await page.getByTestId('tab-food').click()
    await expect(page.getByTestId('tab-food')).toHaveAttribute('aria-selected', 'true')
    await expect(page.locator('article[data-testid^="card-"]')).toHaveCount(1)
    if (city === 'kuala_lumpur') await expect(page.getByTestId('tab-food')).toContainText('Limited in the sample data')
    await page.locator('article[data-testid^="card-"]').first().locator('label', { hasText: 'Must visit' }).click()
    await page.getByTestId('tab-sightseeing').click()
    await page.locator('article[data-testid^="card-"]').first().locator('label', { hasText: 'Must visit' }).click()
    await expect(page.getByTestId('theme-selected')).toContainText('1 Sightseeing')
    await expect(page.getByTestId('theme-selected')).toContainText('1 Food & drink')
    await page.getByTestId('tab-all').click()
    await expect(page.getByTestId('preview-mix')).toContainText('Sightseeing')
    await page.getByTestId('plan-trip').click()
    await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
    await expect(page.getByTestId('timeline')).toBeVisible()
    await expect(page.getByTestId('getting-around')).toBeVisible()
    await expect(page.getByTestId('cost-panel')).toContainText('Rooms')
    await expect(page.getByTestId('cost-day-1')).toBeVisible()
    await expect(page.getByTestId('trip-cash-total')).not.toBeEmpty()
    await expect(page.locator('[data-testid^=day-mix-]').first()).toContainText(/sightseeing|food|shopping/)
    await expect(page.getByTestId('two-figures')).toContainText('Cash cost')
    await expect(page.getByTestId('two-figures')).toContainText('Generalised cost')
    await expect(page.getByTestId('cost-panel')).not.toContainText(/(?<![A-Z])\$\d/)   // never a bare dollar sign
    expectClean(problems)
  })
}

test('day selector: one day shows only its cards and pins; All restores everything', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await planFromExample(page)
  const days = await page.locator('section.day-block').count()
  expect(days).toBeGreaterThan(1)
  const allPins = await pinsOf(page).count()
  await page.getByTestId('daychip-2').click()
  await expect(page.getByTestId('daychip-2')).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByTestId('daychip-2')).toContainText('selected')           // not colour alone
  await expect(page.locator('section.day-block')).toHaveCount(1)
  await expect(page.getByTestId('day-2')).toBeVisible()
  await expect.poll(() => pinsOf(page).count()).toBeLessThan(allPins)
  await page.getByTestId('daychip-all').click()
  await expect(page.locator('section.day-block')).toHaveCount(days)
  await expect.poll(() => pinsOf(page).count()).toBe(allPins)
  expectClean(problems)
})

test('map filter chips: icon, text and count; hotels and themes toggle pins; Saved shows only Must visit picks', async ({ page }) => {
  await page.goto('/')
  await planFromExample(page)
  const chips = page.getByTestId('map-chips')
  for (const [id, label] of [['sightseeing', 'Attractions'], ['food', 'Food'], ['shopping', 'Shopping'], ['hotels', 'Hotels'], ['saved', 'Saved'], ['booking', 'Needs booking']]) {
    await expect(chips.getByTestId(`chip-${id}`)).toContainText(label)
    await expect(chips.getByTestId(`chip-${id}`).locator('.theme-count')).toBeVisible()
  }
  await expect(chips).not.toContainText(/Airport|Station/)                          // the sample data has none
  const before = await pinsOf(page).count()
  await page.getByTestId('chip-hotels').click()
  await expect(page.getByTestId('chip-hotels')).toHaveAttribute('aria-pressed', 'false')
  await expect.poll(() => pinsOf(page).count()).toBe(before - 1)
  await page.getByTestId('chip-hotels').click()
  await page.getByTestId('chip-saved').click()
  const savedCount = Number(await page.getByTestId('chip-saved').locator('.theme-count').innerText())
  await expect.poll(() => pinsOf(page).count()).toBe(savedCount + 1)               // the Must visit stops plus the hotel
})

test('overlapping pins are spread apart so no stop hides behind another', async ({ page }) => {
  await page.route('**/data/places*', async (route) => {          // put two example sights at exactly the same coordinates
    const resp = await route.fetch(); const json = await resp.json()
    const a = json.attractions.find((x) => x.id === 'senso_ji'); const b = json.attractions.find((x) => x.id === 'meiji_jingu')
    b.lat = a.lat; b.lon = a.lon
    await route.fulfill({ response: resp, json })
  })
  await page.goto('/')
  await planFromExample(page)
  await expect(pinsOf(page).first()).toBeVisible()
  const centres = await pinsOf(page).evaluateAll((els) => els.map((e) => { const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] }))
  expect(centres.length).toBeGreaterThan(2)
  for (let i = 0; i < centres.length; i++) for (let j = i + 1; j < centres.length; j++) {
    const d = Math.hypot(centres[i][0] - centres[j][0], centres[i][1] - centres[j][1])
    expect(d, `pins ${i} and ${j} are apart`).toBeGreaterThan(12)
  }
})

test('card and pin are linked: hovering a card highlights its pin, and hovering a pin highlights its card', async ({ page }) => {
  await page.goto('/')
  await planFromExample(page)
  const card = page.locator('article.event-card').first()
  const id = (await card.getAttribute('data-testid')).replace('stop-', '')
  await card.hover()
  await expect(page.locator('[data-testid=trip-map] .pin-active')).toHaveCount(1)
  await page.mouse.move(0, 0)
  await expect(page.locator('[data-testid=trip-map] .pin-active')).toHaveCount(0)
  const pin = pinsOf(page).filter({ hasNot: page.locator('.pin-hotel') }).first()
  await pin.hover({ force: true })
  await expect(page.locator('article.event-card.is-active')).toHaveCount(1)
  await expect(page.getByTestId(`stop-${id}`)).toBeVisible()
})

test('event cards: tags, a cost line, a one-line connector between cards, and a "…" menu that queues a skip through the tray', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await planFromExample(page)
  await expect(page.locator('[data-testid^=connector-]').first()).toContainText('estimated')
  await expect(page.locator('[data-testid^=tags-]').first()).toContainText(/Must visit|Include if it fits/)
  await expect(page.locator('[data-testid^=cost-]').filter({ hasText: 'Admission' }).first()).toContainText(/Free|Price unknown|\d/)
  const optional = page.locator('article.event-card').filter({ hasText: 'Include if it fits' }).first()
  await expect(optional.getByTestId('act-lock')).toBeVisible()                       // the visible Lock button
  await expect(optional.getByTestId('act-remove')).toBeHidden()                      // Move / Skip live in the menu
  await optional.locator('summary').click()
  await optional.getByTestId('act-remove').click()
  await expect(page.getByTestId('pending-count')).toHaveText('1 of 20')
  await expect(page.getByTestId('pending-list')).toContainText('Remove')
  expectClean(problems)
})

test('keyboard only: day chips move with the arrow keys and the "…" menu opens with Enter', async ({ page }) => {
  await page.goto('/')
  await planFromExample(page)
  await page.getByTestId('daychip-1').focus()
  await page.keyboard.press('Space')
  await page.keyboard.press('ArrowRight')
  await expect(page.getByTestId('daychip-2')).toHaveAttribute('aria-selected', 'true')
  await expect(page.locator(':focus')).toHaveAttribute('data-testid', 'daychip-2')
  const summary = page.locator('article.event-card summary').first()
  await summary.focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('article.event-card details[open] [data-testid=act-remove]').first()).toBeVisible()
})

test('phone width: the day chips scroll sideways inside their own strip, the page itself does not', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 })
  await page.goto('/')
  await planFromExample(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true)
  await expect(page.getByTestId('day-selector')).toBeVisible()
  await expect(page.getByTestId('cost-panel')).toBeVisible()
})
