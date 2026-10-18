// The itinerary builder (real drag-and-drop between days, live feedback, keyboard use), the modelled cash total including rooms, the deduplicated "To check" block and the minimum-active-days rule.
import { expect, test } from '@playwright/test'
import { expectClean, planFromExample, PLAN_WAIT, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

// A real drag with the mouse, started from the stop's handle (the middle of a stop can be a button or the "Move to" menu, which are not drag handles).
async function dragStop(page, stop, day) {
  const a = await stop.locator('.ic-handle').boundingBox(), b = await day.boundingBox()
  await page.mouse.move(a.x + 4, a.y + 4); await page.mouse.down()
  await page.mouse.move(a.x + 20, a.y + 20, { steps: 4 }); await page.mouse.move(b.x + b.width / 2, b.y + b.height - 8, { steps: 10 })
  await page.mouse.up()
}

async function openBuilder(page) {
  await page.goto('/')
  await planFromExample(page)
  await page.getByTestId('ic-toggle').click()
  await expect(page.getByTestId('ic-day-1')).toBeVisible()
  await expect(page.getByTestId('ic-live')).toContainText(/Your draft/, { timeout: PLAN_WAIT })
}

test('drag a sight to another day: the lists change, the draft is re-checked live, and a screen-reader announcement is made', async ({ page }) => {
  const problems = watchConsole(page)
  await openBuilder(page)
  const day1 = page.getByTestId('ic-day-1'), day2 = page.getByTestId('ic-day-2')
  const before1 = await day1.locator('[data-testid^="ic-stop-"]').count()
  const before2 = await day2.locator('[data-testid^="ic-stop-"]').count()
  expect(before1).toBeGreaterThan(0)
  const stop = day1.locator('[data-testid^="ic-stop-"]').first()
  const id = (await stop.getAttribute('data-testid')).replace('ic-stop-', '')
  await dragStop(page, stop, day2)
  await expect(day2.locator(`[data-testid="ic-stop-${id}"]`)).toBeVisible()
  await expect(day1.locator('[data-testid^="ic-stop-"]')).toHaveCount(before1 - 1)
  await expect(day2.locator('[data-testid^="ic-stop-"]')).toHaveCount(before2 + 1)
  await expect(page.getByTestId('ic-announce')).toContainText('is now day 2')
  await expect(page.getByTestId('ic-live')).toContainText(/Your draft (works|has a problem)/, { timeout: PLAN_WAIT })
  expectClean(problems)
})

test('live feedback shows each stop\'s time and states the problem on the stop that cannot happen', async ({ page }) => {
  await openBuilder(page)
  const all = page.locator('[data-testid^="ic-stop-"]')
  const n = await all.count()
  // move every sight onto day 1: whether or not it fits, the page must say so on the stop or in the status line, never silently
  for (let i = 1; i < 3; i++) {
    const dayStops = page.getByTestId(`ic-day-${i + 1}`).locator('[data-testid^="ic-stop-"]')
    while (await dayStops.count()) await dragStop(page, dayStops.first(), page.getByTestId('ic-day-1'))
  }
  await expect(page.getByTestId('ic-day-1').locator('[data-testid^="ic-stop-"]')).toHaveCount(n)
  await expect(page.getByTestId('ic-live')).toContainText(/Your draft (works|has a problem)/, { timeout: PLAN_WAIT })
  const text = await page.getByTestId('ic-live').innerText()
  if (/has a problem/.test(text)) expect(await page.locator('[data-testid^="ic-problem-"]').count() + (text.match(/Check failed|does not fit|closed/g) ?? []).length).toBeGreaterThan(0)
  else await expect(page.locator('[data-testid^="ic-time-"]').first()).toBeVisible()
})

test('keyboard only: focus a stop control, move it, hear it, and keep focus', async ({ page }) => {
  await openBuilder(page)
  await page.getByLabel('Add an attraction to day 1').selectOption({ index: 1 })
  const add = page.getByTestId('ic-day-1').getByRole('button', { name: 'Add', exact: true })
  await add.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('ic-day-1').locator('[data-testid^="ic-stop-"]')).toHaveCount(2)
  const down = page.getByRole('button', { name: /^Move .* later on day 1$/ }).first()
  await down.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('ic-announce')).toContainText('position 2')
  expect(await page.evaluate(() => document.activeElement?.tagName)).toBe('BUTTON')
})

test('the Compare button still compares the same sights after drag-and-drop edits and says so honestly', async ({ page }) => {
  await openBuilder(page)
  const day1 = page.getByTestId('ic-day-1')
  await dragStop(page, day1.locator('[data-testid^="ic-stop-"]').first(), page.getByTestId('ic-day-3'))
  await page.getByTestId('ic-compare').click()
  await expect(page.getByTestId('ic-table')).toBeVisible({ timeout: PLAN_WAIT })
  await expect(page.getByTestId('ic-verdict')).not.toBeEmpty()
  await expect(page.getByTestId('ic-table')).toContainText('Generalised cost')
})

test('the spending tile includes rooms, shows its parts, and "To check before you go" lists each unverified item once', async ({ page }) => {
  await page.goto('/')
  await planFromExample(page)
  await expect(page.getByTestId('kpi-total')).toBeVisible()
  await expect(page.getByTestId('kpi-total-parts')).toContainText('rooms')
  await expect(page.getByTestId('totals')).toContainText('Active days')
  // no duplicated "unknown price" sentence in the totals line and none per day
  await expect(page.getByTestId('totals')).not.toContainText('unknown price(s), not included')
  const ttc = page.getByTestId('things-to-check')
  if (await ttc.count()) {
    for (const key of ['hours', 'price', 'booking']) expect(await ttc.getByTestId(`check-${key}`).count()).toBeLessThanOrEqual(1)
  }
})

test('minimum active days: the rule is applied by the planner and shown, and the form refuses a value above the trip length', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('load-example').click()
  await page.getByTestId('advanced').locator('summary').click()
  await page.getByTestId('min-active-days').fill('99')
  await expect(page.getByTestId('form-errors')).toContainText('Minimum active days')
  await page.getByTestId('min-active-days').fill('3')
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await expect(page.getByTestId('totals')).toContainText(/Active days 3 of 3/)
})

test('phone width: the builder fits without sideways scrolling and its controls are all reachable', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  await openBuilder(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(1)
  await expect(page.getByRole('button', { name: /^Move .* later on day 1$/ }).first()).toBeVisible()
})

test('classic mode (for the usability study): no drag handles and no live feedback, the same arrow controls, the same optimiser comparison', async ({ page }) => {
  await page.goto('/?builder=classic')
  await planFromExample(page)
  await page.getByTestId('ic-toggle').click()
  await expect(page.getByTestId('ic-day-1')).toBeVisible()
  await expect(page.locator('.ic-handle')).toHaveCount(0)
  await expect(page.getByTestId('ic-live')).toHaveCount(0)
  await expect(page.getByRole('button', { name: /^Move .* later on day 1$/ }).first()).toBeVisible()
  await page.getByTestId('ic-compare').click()
  await expect(page.getByTestId('ic-table')).toBeVisible({ timeout: PLAN_WAIT })
})
