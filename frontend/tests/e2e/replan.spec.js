import { expect, test } from '@playwright/test'
import { expectClean, planFromExample, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

/** Example trip -> Plan my trip -> Your trip (the best hotel is pre-selected). */
async function toItinerary(page) {
  await page.goto('/')
  await planFromExample(page)
  await expect(page.getByTestId('timeline')).toBeVisible()
}
const optionalStop = (page) => page.locator('[data-testid^=stop-]').filter({ hasNot: page.locator('.pill-must') }).first()
const mustStop = (page, id) => page.getByTestId(`stop-${id}`)

test('queue lock + remove, apply once, see the diff with warnings; then restore the previous plan', async ({ page }) => {
  const problems = watchConsole(page)
  await toItinerary(page)
  const replanCalls = []
  page.on('request', (r) => { if (r.url().endsWith('/replan')) replanCalls.push(JSON.parse(r.postData())) })

  const timelineBefore = await page.getByTestId('timeline').innerText()
  await page.locator('[data-testid^=stop-]').first().getByTestId('act-lock').click()
  await optionalStop(page).locator('summary').click()                  // Remove now lives in the "…" menu
  await optionalStop(page).getByTestId('act-remove').click()
  await expect(page.getByTestId('pending-count')).toHaveText('2 of 20')
  await expect(page.getByTestId('pending-list')).toContainText('Lock')
  await expect(page.getByTestId('pending-list')).toContainText('Remove')
  expect(replanCalls).toHaveLength(0) // nothing is sent until "Apply changes"

  await page.getByTestId('apply-changes').click()
  await expect(page.getByTestId('diff-view')).toBeVisible()
  expect(replanCalls).toHaveLength(1)
  expect(replanCalls[0].operations).toHaveLength(2)
  expect(replanCalls[0].confirm_remove_must_visit).toBe(false)
  await expect(page.getByTestId('diff-table')).toContainText('True cost')
  await expect(page.getByTestId('diff-warnings')).toBeVisible()
  await expect(page.getByTestId('diff-warnings')).toContainText('Not like-for-like')
  await expect(page.getByTestId('diff-true_cost_jpy').getByTestId('not-like-for-like')).toBeVisible()
  await expect(page.getByTestId('diff-removed')).toContainText('removed by you')
  await expect(page.getByTestId('locked-pill')).toHaveCount(1)
  await expect(page.getByTestId('pending-count')).toHaveText('0 of 20')

  await page.getByTestId('restore-previous').click()
  await expect(page.getByTestId('restored')).toBeVisible()
  await expect(page.getByTestId('diff-view')).toHaveCount(0)
  expect(await page.getByTestId('timeline').innerText()).toBe(timelineBefore)
  expect(replanCalls).toHaveLength(1) // restoring sent nothing
  expectClean(problems)
})

test('removing a must-visit shows the dialog and sends the flag only after explicit confirmation', async ({ page }) => {
  const problems = watchConsole(page)
  await toItinerary(page)
  const calls = []
  page.on('request', (r) => { if (r.url().endsWith('/replan')) calls.push(JSON.parse(r.postData())) })
  await mustStop(page, 'senso_ji').locator('summary').click()
  await mustStop(page, 'senso_ji').getByTestId('act-remove').click()
  await page.getByTestId('apply-changes').click()
  const dialog = page.getByTestId('confirm-dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog).toContainText('Senso-ji')
  await expect(dialog).toContainText('must-visit')
  expect(calls).toHaveLength(0)
  await page.getByTestId('dialog-cancel').click()
  await expect(dialog).toBeHidden()
  expect(calls).toHaveLength(0)
  await expect(page.getByTestId('pending-count')).toHaveText('1 of 20') // still queued, still not sent

  await page.getByTestId('apply-changes').click()
  await page.getByTestId('dialog-confirm').click()
  await expect(page.getByTestId('diff-view')).toBeVisible()
  expect(calls).toHaveLength(1)
  expect(calls[0].confirm_remove_must_visit).toBe(true)
  await expect(page.getByTestId('diff-warnings')).toContainText('Must-visit removed by user')
  await expect(page.getByTestId('diff-removed')).toContainText('was a must-visit')
  expectClean(problems)
})

test('an infeasible replan says the original plan is unchanged and keeps showing it', async ({ page }) => {
  const problems = watchConsole(page)
  await toItinerary(page)
  const before = await page.getByTestId('timeline').innerText()
  await page.getByText('More changes: budget and hotel').click()
  await page.getByLabel('Budget for sights and transport (JPY)').fill('100')
  await page.getByLabel('Strict limit (never exceed)').check()
  await page.getByRole('button', { name: 'Queue', exact: true }).first().click()
  await expect(page.getByTestId('pending-list')).toContainText('strict limit')
  await page.getByTestId('apply-changes').click()
  const note = page.getByTestId('replan-unchanged')
  await expect(note).toBeVisible()
  await expect(note).toContainText('Your original plan is unchanged')
  await expect(page.getByTestId('replan-conflicts')).toContainText('budget')
  await expect(page.getByTestId('error-panel')).toHaveCount(0)
  expect(await page.getByTestId('timeline').innerText()).toBe(before)
  await expect(page.getByTestId('pending-count')).toHaveText('1 of 20')
  await page.getByTestId('clear-queue').click()
  await expect(page.getByTestId('pending-count')).toHaveText('0 of 20')
  expectClean(problems)
})

test('sample mode: both natural-language boxes show the calm message and the manual flow keeps working', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await page.getByLabel(/For example: "3 days/).fill('3 days, relaxed, I love shrines')
  await page.getByTestId('nl-extract').click()
  const note = page.getByTestId('nl-unavailable')
  await expect(note).toContainText('The AI assistant is unavailable right now. Use the form below, everything else works.')
  await expect(page.locator('[role=alert]')).toHaveCount(0)
  await page.getByLabel('Days', { exact: true }).fill('2')
  await expect(page.getByTestId('plan-trip')).toBeEnabled()

  await toItinerary(page)
  await page.getByLabel(/For example: "move Senso-ji/).fill('drop the market')
  await page.getByTestId('proposal-button').click()
  await expect(page.getByTestId('proposal-unavailable')).toContainText('The AI assistant is unavailable right now.')
  await page.getByTestId('stop-senso_ji').getByTestId('act-lock').click()
  await expect(page.getByTestId('pending-count')).toHaveText('1 of 20')
  expectClean(problems)
})

test('explanations are opt-in; in sample mode they are a template summary with the warnings shown', async ({ page }) => {
  const calls = []
  page.on('request', (r) => { if (r.url().endsWith('/optimise')) calls.push(JSON.parse(r.postData())) })
  await toItinerary(page)
  expect(calls.every((c) => c.explain === false)).toBe(true) // nothing asks for an explanation by itself
  await page.getByTestId('explain-button').first().click()
  await expect(page.getByTestId('explain-badge')).toHaveText('Template summary')
  await expect(page.getByTestId('explain-text')).not.toBeEmpty()
  await expect(page.getByTestId('explain-warnings')).toBeVisible()
  expect(calls.at(-1).explain).toBe(true)
})

test('proof page renders the real generated data; example label and note are honest; 404 and How it works work', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await expect(page.getByTestId('load-example')).toContainText('high value of time')
  await expect(page.getByTestId('load-example')).toContainText('¥3,000')
  await expect(page.getByTestId('example-note')).toContainText('not typical')
  await page.getByTestId('example-note').getByRole('link', { name: 'Proof page' }).click()
  await expect(page).toHaveURL(/\/proof#hotel-value$/)
  await expect(page.getByTestId('hotel-value')).toBeInViewport()
  await expect(page.getByTestId('proof-meta')).toContainText('Code version')
  await expect(page.locator('[data-testid^=scn-]')).toHaveCount(15)
  await expect(page.getByTestId('read-first')).toContainText('Small comparable subset')
  await expect(page.getByTestId('not-shown')).toContainText('No significance testing')
  await expect(page.getByTestId('live-not-run')).toContainText('Not run yet')
  await expect(page.getByTestId('claims').locator('li').first()).not.toBeEmpty()
  await page.getByTestId('toggle-risks').click()
  expect(await page.locator('[data-testid=risk-table] tbody tr').count()).toBeGreaterThanOrEqual(74)

  await page.goto('/how-it-works')
  await expect(page.getByTestId('architecture').locator('svg')).toBeVisible()
  await expect(page.getByTestId('privacy')).toContainText('Place descriptions are never sent')
  await page.goto('/no-such-page')
  await expect(page.getByTestId('not-found')).toContainText('Page not found')
  expectClean(problems)
})

test('Reset clears everything held in the page', async ({ page }) => {
  await toItinerary(page)
  await page.getByTestId('reset').click()
  await expect(page).toHaveURL(/\/$/)
  await page.goto('/itinerary')
  await expect(page.getByTestId('itinerary-empty')).toBeVisible()
})

test('no request leaves the machine except map tiles, and nothing is written to browser storage', async ({ page }) => {
  const hosts = new Set()
  page.on('request', (r) => { const u = new URL(r.url()); if (!['localhost'].includes(u.hostname)) hosts.add(u.hostname) })
  await toItinerary(page)
  await page.getByTestId('explain-button').first().click()
  await page.goto('/proof')
  expect([...hosts].sort()).toEqual(['tile.openstreetmap.org'])
  const stored = await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length, cookies: document.cookie }))
  expect(stored).toEqual({ local: 0, session: 0, cookies: '' })
})

test('keyboard only: example trip -> plan -> lock a stop -> apply -> diff', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await expect(page.getByTestId('honesty-banner')).toBeVisible()
  const tabTo = async (predicate, max = 120) => {
    for (let i = 0; i < max; i++) {
      await page.keyboard.press('Tab')
      if (await page.evaluate(predicate)) return
    }
    throw new Error('never reached the target with the keyboard')
  }
  const active = (text) => `(() => { const e = document.activeElement; return !!e && (e.innerText || e.value || '').includes(${JSON.stringify(text)}) })()`
  await tabTo(() => document.activeElement?.getAttribute('data-testid') === 'load-example')
  await page.keyboard.press('Enter')
  await tabTo(() => document.activeElement?.getAttribute('data-testid') === 'plan-trip')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('timeline')).toBeVisible({ timeout: 45_000 })
  await tabTo(() => document.activeElement?.getAttribute('data-testid') === 'act-lock')
  await expect(page.locator(':focus')).toBeVisible()
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('pending-count')).toHaveText('1 of 20')
  await tabTo(() => document.activeElement?.getAttribute('data-testid') === 'apply-changes')
  await page.keyboard.press('Enter')
  await expect(page.getByTestId('diff-view')).toBeVisible()
  expectClean(problems)
})
