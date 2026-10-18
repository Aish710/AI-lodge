// Kuala Lumpur, National Mosque of Malaysia as a must-visit: its sample opening hours are unknown. Strict mode (the default) must not assume it is open,
// must say so BEFORE planning, explain the block in plain words, offer complete verified repairs, and keep provisional planning explicit and labelled.
import { expect, test } from '@playwright/test'
import { expectClean, PLAN_WAIT, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

async function chooseMosque(page) {
  await page.goto('/')
  await page.getByTestId('city-kuala_lumpur').click()
  await page.locator('article[data-testid^="card-"]').first().waitFor()
  await page.getByTestId('card-national_mosque_malaysia').locator('label', { hasText: 'Must visit' }).click()
}

test('strict mode: warned before planning, blocked by missing information (not "impossible"), friendly text, complete verified repairs, no raw code up front', async ({ page }) => {
  const problems = watchConsole(page)
  await chooseMosque(page)
  await expect(page.getByTestId('unknown-hours-warning')).toContainText('opening hours unknown in the sample data')
  await expect(page.getByTestId('unknown-hours-warning')).toContainText('Strict mode (the default)')
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  const panel = page.getByTestId('conflict-panel')
  await expect(panel).toHaveAttribute('data-state', 'blocked_missing_info')
  await expect(page.getByTestId('status-chip')).toContainText('Blocked by missing information')
  await expect(page.getByTestId('status-chip')).not.toContainText('Not possible')
  await expect(page.getByTestId('conflict-title')).toContainText('some information is missing')
  await expect(page.getByTestId('conflict-friendly')).toContainText("We don't know when National Mosque of Malaysia is open")
  // the raw reason code is not in the visible headline or explanation, only in the collapsed technical details
  await expect(page.getByTestId('conflict-friendly')).not.toContainText('unknown_hours_not_allowed')
  await expect(page.getByTestId('technical-details')).not.toHaveAttribute('open', '')
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
  await page.getByTestId('conflict-panel').locator('button[data-kind=allow_unknown_hours]').click()
  await expect(page.getByTestId('conditional-banner')).toContainText('Opening hours unverified', { timeout: PLAN_WAIT })
  await expect(page.getByTestId('conditional-banner')).toContainText('Check the opening hours before you travel')
  await expect(page.getByTestId('conditional-banner')).toContainText('not a verified itinerary')
  await expect(page.getByTestId('status-chip').first()).toContainText('Feasible if opening hours are confirmed')
  await expect(page.getByTestId('tag-unknown-hours').first()).toContainText('Opening hours unverified')
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
  await expect(page.getByTestId('conditional-banner')).toBeVisible({ timeout: PLAN_WAIT })
})
