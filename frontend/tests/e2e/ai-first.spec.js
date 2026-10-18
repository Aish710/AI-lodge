import { tripSection, setupSection, disclose, allDays, mapView, timelineView } from './helpers.js'
import { expect, test } from '@playwright/test'
import { expectClean, planFromExample, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

test('the optional Describe card opens; example prompts fill the box and send nothing; the AI-off popover is calm', async ({ page }) => {
  const problems = watchConsole(page)
  const sent = []
  page.on('request', (r) => { if (r.method() === 'POST') sent.push(r.url()) })
  await page.goto('/')
  await disclose(page, 'setup-ai')
  const heading = page.getByTestId('nl-panel').getByRole('heading').first()
  await expect(heading).toContainText('Where to, friend?')
  await disclose(page, 'setup-ai')
  await page.getByTestId('ex-wrong-city').click()
  await disclose(page, 'setup-ai')
  await expect(page.locator('#nl-text')).toHaveValue(/Seoul/)
  await disclose(page, 'setup-ai')
  await page.getByTestId('ex-vague').click()
  await disclose(page, 'setup-ai')
  await expect(page.locator('#nl-text')).toHaveValue(/museum/)
  expect(sent).toEqual([])
  await page.getByTestId('ai-popover-button').first().click()
  await expect(page.getByTestId('ai-popover')).toContainText('AI off: the form works the same.')
  await page.keyboard.press('Escape')
  await disclose(page, 'setup-ai')
  await page.getByTestId('nl-extract').click()
  await disclose(page, 'setup-ai')
  await expect(page.getByTestId('nl-unavailable')).toBeVisible()
  expectClean(problems)
})

test('Your trip: the AI Planner contains the change box with plan-based example chips that only fill it', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await planFromExample(page)
  await allDays(page)
  const sent = []
  page.on('request', (r) => { if (r.method() === 'POST') sent.push(r.url()) })
  await tripSection(page, 'ai')
  await page.getByTestId('more-ai-edit').locator('summary').click()
  await tripSection(page, 'ai')
  await expect(page.getByTestId('replan-chips')).toBeVisible()
  await tripSection(page, 'ai')
  await page.getByTestId('replan-chip-1').click()
  await tripSection(page, 'ai')
  await expect(page.locator('#pr-text')).toHaveValue(/^Skip /)
  expect(sent).toEqual([])
  await tripSection(page, 'ai')
  await expect(page.locator('#trip-panel-ai').getByTestId('explain-button').first()).toHaveText('Tell me why!')
  expectClean(problems)
})
