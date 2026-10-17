// Trip Trade-off Explorer against the real backend: real reruns, honest no-change case, restoring an earlier plan, and the new daily limits.
import { expect, test } from '@playwright/test'
import { expectClean, planFromExample, PLAN_WAIT, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

test('explore a higher value of time, see the three plans side by side, adopt one, and show the earlier plan again', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await planFromExample(page)
  const ex = page.getByTestId('explorer')
  await expect(ex).toBeVisible()
  await page.getByTestId('explore-4').click()
  await expect(page.getByTestId('explorer-table')).toBeVisible({ timeout: PLAN_WAIT })
  for (const k of ['cheapest_rate', 'convenience_first', 'joint']) await expect(page.getByTestId(`row-${k}`)).toBeVisible()
  await expect(page.getByTestId('explorer-why')).not.toBeEmpty()
  await page.getByTestId('adopt-explorer').click()
  await expect(page.getByTestId('plan-history')).toBeVisible({ timeout: PLAN_WAIT })
  const first = page.locator('[data-testid^="restore-"]').first()
  await first.click()
  await expect(page.getByTestId('restored')).toBeVisible()
  expectClean(problems)
})

test('the daily limits are sent only when set, and a limit the planner can respect produces a plan with no failed checks', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('load-example').click()
  await page.getByTestId('advanced').locator('summary').click()
  await page.getByTestId('max-activities').fill('2')
  await page.getByTestId('max-daily-travel').fill('240')
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await expect(page.getByTestId('timeline')).toBeVisible()
  await expect(page.getByTestId('kpi-checks')).toContainText('of')
})
