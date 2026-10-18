import { expect, test } from '@playwright/test'
import { expectClean, planFromExample, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

test('the Describe card is first; example prompts fill the box and send nothing; the AI-off popover is calm', async ({ page }) => {
  const problems = watchConsole(page)
  const sent = []
  page.on('request', (r) => { if (r.method() === 'POST') sent.push(r.url()) })
  await page.goto('/')
  const heading = page.locator('main h2').first()
  await expect(heading).toContainText('Ask the AI to set up your trip')
  await page.getByTestId('ex-wrong-city').click()
  await expect(page.locator('#nl-text')).toHaveValue(/Seoul/)
  await page.getByTestId('ex-vague').click()
  await expect(page.locator('#nl-text')).toHaveValue(/museum/)
  expect(sent).toEqual([])
  await page.getByTestId('ai-popover-button').first().click()
  await expect(page.getByTestId('ai-popover')).toContainText('AI off: the form works the same.')
  await page.keyboard.press('Escape')
  await page.getByTestId('nl-extract').click()
  await expect(page.getByTestId('nl-unavailable')).toBeVisible()
  expectClean(problems)
})

test('Your trip: the AI change box is near the top with plan-based example chips that only fill it', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await planFromExample(page)
  const sent = []
  page.on('request', (r) => { if (r.method() === 'POST') sent.push(r.url()) })
  await page.getByTestId('more-ai-edit').locator('summary').click()
  await expect(page.getByTestId('replan-chips')).toBeVisible()
  await page.getByTestId('replan-chip-1').click()
  await expect(page.locator('#pr-text')).toHaveValue(/^Skip /)
  expect(sent).toEqual([])
  await expect(page.getByTestId('explain-button').first()).toHaveText('Explain this plan')
  expectClean(problems)
})
