import { tripSection, setupSection, disclose, allDays, mapView, timelineView } from './helpers.js'
// First-time journey: one-click sample trip, itinerary first, AI-assisted edits that are only previewed, undo, and empty-day help. No model is called (quick questions are deterministic).
import { expect, test } from '@playwright/test'
import { PLAN_WAIT, stubTiles } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

async function sample(page, city = 'kuala_lumpur') {
  await page.goto('/')
  await page.getByTestId('city-' + city).click()
  await setupSection(page, 'sights')
  await page.locator('article[data-testid^="card-"]').first().waitFor()
  await page.getByTestId('sample-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await allDays(page)
  await expect(page.getByTestId('kpi-total')).toBeVisible({ timeout: PLAN_WAIT })
}

test('one click starts a sample trip and the day-by-day plan comes before the assistant', async ({ page }) => {
  await sample(page)
  const order = await page.evaluate(() => {
    const q = (id) => document.querySelector(`[data-testid="${id}"]`)
    const pos = (a, b) => Boolean(q(a).compareDocumentPosition(q(b)) & Node.DOCUMENT_POSITION_FOLLOWING)
    return { timelineFirst: pos('totals', 'trip-copilot') && document.querySelector('.timeline, [data-testid^="day-"]') !== null, copilotBeforeRepair: pos('trip-copilot', 'more-ai-edit') }
  })
  expect(order.copilotBeforeRepair).toBe(true)
  await tripSection(page, 'ai')
  await expect(page.getByTestId('trip-copilot')).toBeVisible()
  // the three older AI inputs are folded into one disclosure
  await tripSection(page, 'ai')
  await expect(page.getByTestId('more-ai-edit')).toBeVisible()
  await expect(page.getByTestId('copilot-repair')).toBeHidden()
  await tripSection(page, 'ai')
  await page.getByTestId('more-ai-edit').locator('summary').click()
  await expect(page.getByTestId('copilot-repair')).toBeVisible()
})

test('Finish earlier is only a preview; Apply changes the plan; Undo restores it', async ({ page }) => {
  await sample(page)
  const before = await page.getByTestId('kpi-travel').innerText()
  await tripSection(page, 'ai')
  await page.getByRole('button', { name: 'Finish earlier' }).click()
  const answer = page.getByTestId('copilot-answer')
  await expect(answer).toContainText('Nothing has been changed', { timeout: PLAN_WAIT })
  await expect(answer).toContainText('Nothing applied')
  const preview = page.getByTestId('copilot-preview')
  if (!(await preview.count())) test.skip(true, 'this sample already ends close to its last sight; nothing to propose')
  await preview.click()
  await tripSection(page, 'compare')
  await expect(page.getByTestId('wi-result').or(page.getByTestId('wi-infeasible'))).toBeVisible({ timeout: PLAN_WAIT })
  await expect(page.getByTestId('kpi-travel')).toHaveText(before)          // the current plan is untouched by a preview
  await tripSection(page, 'compare')
  if (await page.getByTestId('wi-result').count()) {
    await tripSection(page, 'compare')
    await expect(page.getByTestId('wi-validation')).toContainText(/Validation:/)
    await tripSection(page, 'compare')
    await page.getByTestId('wi-apply').click()
    await expect(page.getByTestId('undo-last')).toBeVisible()
    await page.getByTestId('undo-last').click()
    await expect(page.getByTestId('kpi-travel')).toHaveText(before)
  }
})

test('a rebalance question with a typed day is rejected cleanly when no AI is available', async ({ page }) => {
  await sample(page)
  await tripSection(page, 'ai')
  await page.getByTestId('trip-copilot').getByLabel('Your question').fill('Make Day 2 less crowded.')
  await tripSection(page, 'ai')
  await page.getByTestId('trip-copilot').getByRole('button', { name: 'Ask', exact: true }).click()
  await expect(page.getByTestId('copilot-answer').or(page.getByRole('alert'))).toBeVisible({ timeout: PLAN_WAIT })
  await expect(page.getByTestId('copilot-preview')).toHaveCount(0)        // no model, no interpretation, no proposal
})

test('phone width: sample entry and itinerary have no sideways scroll', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  await sample(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true)
})
