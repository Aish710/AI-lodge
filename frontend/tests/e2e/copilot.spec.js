import { expect, test } from '@playwright/test'
import { planFromExample, stubTiles, watchConsole, expectClean } from './helpers.js'

for (const width of [1280, 390]) {
  test(`copilot on ${width}px: deterministic questions, checked costs, workflow handoff`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await stubTiles(page)
    const problems = watchConsole(page)
    await page.goto('/')
    await planFromExample(page)
    const panel = page.getByTestId('trip-copilot')
    await expect(panel).toBeVisible()
    await panel.getByRole('button', { name: 'Why this plan?', exact: true }).click()
    await expect(panel.getByTestId('copilot-answer')).toContainText('Nothing applied')
    await expect(panel.getByTestId('copilot-answer')).toContainText('Required attractions')
    await panel.getByRole('button', { name: 'Why expensive?', exact: true }).click()
    await expect(panel.getByTestId('copilot-answer')).toContainText('Illustrative room cost')
    await expect(panel.getByTestId('copilot-answer')).toContainText('Unknown admissions are excluded, not free')
    await panel.getByRole('button', { name: 'Open Trade-off Explorer', exact: true }).click()
    await expect(page.getByTestId('explorer')).toBeFocused()
    expectClean(problems)
  })
}
