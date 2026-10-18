import { tripSection, setupSection, disclose, allDays, mapView, timelineView } from './helpers.js'
// Kuala Lumpur, National Mosque of Malaysia as a must-visit: its sample opening hours are unknown. Strict mode (the default) must not assume it is open,
// must say so BEFORE planning, explain the block in plain words, offer complete verified repairs, and keep provisional planning explicit and labelled.
import { expect, test } from '@playwright/test'
import { expectClean, PLAN_WAIT, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

async function chooseMosque(page) {
  await page.goto('/')
  await page.getByTestId('city-kuala_lumpur').click()
  await setupSection(page, 'sights')
  await page.locator('article[data-testid^="card-"]').first().waitFor()
  await setupSection(page, 'sights')
  await page.getByTestId('card-national_mosque_malaysia').locator('label', { hasText: 'Must go' }).click()
}

test('strict mode: warned before planning, blocked by missing information (not "impossible"), friendly text, complete verified repairs, no raw code up front', async ({ page }) => {
  const problems = watchConsole(page)
  await chooseMosque(page)
  await expect(page.getByTestId('unknown-hours-warning')).toContainText('opening hours unknown in the sample data')
  await expect(page.getByTestId('unknown-hours-warning')).toContainText('Strict mode (the default)')
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await allDays(page)
  const panel = page.getByTestId('conflict-panel')
  await expect(panel).toHaveAttribute('data-state', 'blocked_missing_info')
  await expect(page.getByTestId('status-chip')).toContainText('Blocked by missing information')
  await expect(page.getByTestId('status-chip')).not.toContainText('Not possible')
  await expect(page.getByTestId('conflict-title')).toContainText('some information is missing')
  await expect(page.getByTestId('conflict-friendly')).toContainText("We don't know when National Mosque of Malaysia is open")
  // the raw reason code is not in the visible headline or explanation, only in the collapsed technical details
  await expect(page.getByTestId('conflict-friendly')).not.toContainText('unknown_hours_not_allowed')
  await expect(page.getByTestId('technical-details')).not.toHaveAttribute('open', '')
  await tripSection(page, 'costs')
  for (const hotel of ['klcc_lantern', 'bukit_bintang_lane', 'bangsar_edge']) await expect(page.getByTestId(`switch-hotel_${hotel}`).locator('xpath=following-sibling::label[1]')).toContainText('Blocked by missing information')
  // every repair is a complete card: no blank items
  const cards = page.locator('[data-testid=alternatives] > li')
  expect(await cards.count()).toBeGreaterThanOrEqual(2)
  for (let i = 0; i < await cards.count(); i++) {
    const c = cards.nth(i)
    await expect(c.getByTestId('repair-title')).not.toBeEmpty()
    await expect(c.getByTestId('repair-why')).toContainText('Why it may help')
    await expect(c.getByTestId('repair-effect')).toContainText('Resulting plan')
    await expect(c.getByTestId('repair-verified')).toContainText('checked by the validator')
    await expect(c.getByRole('button', { name: 'Apply this change' })).toBeVisible()
  }
  // the feasibility report states the failure once and folds the detail away
  await tripSection(page, 'details')
  await expect(page.getByTestId('feasibility-report').getByTestId('failed-checks')).toHaveCount(0)
  // nothing was applied or removed by itself
  await expect(page.getByTestId('conflict-panel')).toBeVisible()
  expectClean(problems)
})

test('applying the provisional repair gives a conditional plan: labelled "Opening hours unverified", never called verified, with a check-before-travel reminder', async ({ page }) => {
  const problems = watchConsole(page)
  await chooseMosque(page)
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await allDays(page)
  await page.getByTestId('conflict-panel').locator('button[data-kind=allow_unknown_hours]').click()
  await expect(page.getByTestId('conditional-banner')).toContainText('Opening hours unverified', { timeout: PLAN_WAIT })
  await allDays(page)   // a changed plan opens on Day 1; the mosque may be on another day
  await expect(page.getByTestId('conditional-banner')).toContainText('Check the opening hours before you travel')
  await expect(page.getByTestId('conditional-banner')).toContainText('not a verified itinerary')
  await expect(page.getByTestId('status-chip').first()).toContainText('Feasible if opening hours are confirmed')
  await expect(page.getByTestId('tag-unknown-hours').first()).toContainText('Opening hours unverified')
  await tripSection(page, 'details')
  await expect(page.getByTestId('report-conditional')).toContainText('Conditional, not fully verified')
  expectClean(problems)
})

test('opting in before planning is explicit and reversible, and the plan is conditional', async ({ page }) => {
  await chooseMosque(page)
  await page.getByTestId('plan-provisionally').click()
  await expect(page.getByTestId('provisional-on')).toContainText('Opening hours unverified')
  await expect(page.getByTestId('unknown-hours-warning')).toHaveCount(0)
  await page.getByTestId('back-to-strict').click()
  await expect(page.getByTestId('unknown-hours-warning')).toBeVisible()
  await page.getByTestId('plan-provisionally').click()
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await allDays(page)
  await expect(page.getByTestId('conditional-banner')).toBeVisible({ timeout: PLAN_WAIT })
})

test('the AI repair box is inside the conflict panel; with no model available it says so, changes nothing, and the verified repair cards still work', async ({ page }) => {
  const problems = watchConsole(page)
  await chooseMosque(page)
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await allDays(page)
  const box = page.getByTestId('conflict-panel').getByTestId('repair-assistant')
  await expect(box).toBeVisible()
  await expect(box.getByTestId('repair-chip-0')).toContainText('National Mosque')
  await box.getByTestId('repair-chip-1').click()
  await expect(box.getByTestId('repair-text')).toHaveValue(/Keep my hotel/)
  await box.getByTestId('repair-ask').click()
  await expect(box.getByTestId('repair-unavailable')).toContainText('Your plan is unchanged', { timeout: PLAN_WAIT })
  await expect(page.getByTestId('conflict-panel')).toHaveAttribute('data-state', 'blocked_missing_info')      // nothing was applied
  await page.getByTestId('conflict-panel').locator('button[data-kind=allow_unknown_hours]').click()
  await expect(page.getByTestId('conditional-banner')).toBeVisible({ timeout: PLAN_WAIT })
  expectClean(problems)
})

test('travel style in words: with no model available the box says so and the form is untouched', async ({ page }) => {
  await page.goto('/')
  await setupSection(page, 'essentials')
  await disclose(page, 'profiles')
  await page.getByTestId('style-chip-0').click()
  await setupSection(page, 'essentials')
  await disclose(page, 'profiles')
  await page.getByTestId('style-ask').click()
  await setupSection(page, 'essentials')
  await disclose(page, 'profiles')
  await expect(page.getByTestId('style-unavailable')).toBeVisible({ timeout: PLAN_WAIT })
  await setupSection(page, 'essentials')
  await disclose(page, 'profiles')
  await expect(page.getByTestId('profile-effective')).toHaveCount(0)
})

test('phone width: the blocked-trip page and the Plan page do not scroll sideways, and the AI boxes are reachable', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  await chooseMosque(page)
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(await overflow()).toBeLessThanOrEqual(1)
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await allDays(page)
  await expect(page.getByTestId('repair-assistant')).toBeVisible()
  await expect(page.getByTestId('repair-ask')).toBeVisible()
  expect(await overflow()).toBeLessThanOrEqual(1)
})

test('keyboard: the repair box can be reached and used without a mouse, and each control has an accessible name', async ({ page }) => {
  await chooseMosque(page)
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await allDays(page)
  const ta = page.getByTestId('repair-text')
  await ta.focus()
  await page.keyboard.type('Keep my hotel but make it work')
  await page.keyboard.press('Tab')
  await expect(page.getByTestId('repair-keep-hotel')).toBeFocused()
  await page.keyboard.press('Space')
  await expect(page.getByTestId('repair-keep-hotel')).toBeChecked()
  await page.keyboard.press('Tab')
  await expect(page.getByTestId('repair-ask')).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('repair-proposal')).toBeVisible({ timeout: PLAN_WAIT })
  await expect(page.locator('#rp-h')).toBeFocused()
})
