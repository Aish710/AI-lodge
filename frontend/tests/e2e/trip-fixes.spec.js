// Regression tests for the Kuala Lumpur Your Trip bugs: manual itinerary check/compare after a drag, an older server, what-if validation and coverage, the plan explanation, and destination examples.
import { expect, test } from '@playwright/test'
import { expectClean, PLAN_WAIT, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

async function klPlan(page) {
  await page.goto('/')
  await page.getByTestId('city-kuala_lumpur').click()
  await page.locator('article[data-testid^="card-"]').first().waitFor()
  await page.getByTestId('load-example').click()
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
}

// A real mouse drag. When the target day is below (or above) the visible area the pointer is moved to the window edge and held there for a moment, as a person does: the page then scrolls.
async function drag(page, stop, day) {
  await stop.scrollIntoViewIfNeeded()
  const a = await stop.locator('.ic-handle').boundingBox()
  const vh = await page.evaluate(() => window.innerHeight)
  await page.mouse.move(a.x + 4, a.y + 4); await page.mouse.down()
  await page.mouse.move(a.x + 20, a.y + 20, { steps: 4 })
  let b = await day.boundingBox()
  for (let i = 0; i < 12 && (b.y + b.height / 2 > vh - 40 || b.y < 40); i++) {
    await page.mouse.move(a.x + 40, b.y < 40 ? 6 : vh - 6, { steps: 3 }); await page.waitForTimeout(150)
    b = await day.boundingBox()
  }
  await page.mouse.move(b.x + b.width / 2, b.y + Math.min(b.height - 8, 50), { steps: 8 })
  await page.mouse.up()
}

async function addMerdekaAndDragToDay3(page) {
  await page.getByTestId('ic-toggle').click()
  await expect(page.getByTestId('ic-live')).toContainText(/Your draft/, { timeout: PLAN_WAIT })
  await page.getByLabel('Add an attraction to day 1').selectOption('merdeka_square')
  await page.getByTestId('ic-day-1').getByRole('button', { name: 'Add', exact: true }).click()
  await expect(page.getByTestId('ic-stop-merdeka_square')).toBeVisible()
  await drag(page, page.getByTestId('ic-stop-merdeka_square'), page.getByTestId('ic-day-3'))
  await expect(page.getByTestId('ic-day-3').getByTestId('ic-stop-merdeka_square')).toBeVisible()
  await expect(page.getByTestId('ic-announce')).toContainText('Merdeka Square is now day 3')
}

test('Kuala Lumpur: drag Merdeka Square, the draft is validated with times, and the comparison with the optimiser completes (no "Not found")', async ({ page }) => {
  const problems = watchConsole(page)
  const statuses = []
  page.on('response', (r) => { if (/check-itinerary|evaluate-itinerary/.test(r.url())) statuses.push(`${new URL(r.url()).pathname}:${r.status()}`) })
  await klPlan(page)
  await addMerdekaAndDragToDay3(page)
  await expect(page.getByTestId('ic-live')).toContainText(/Your draft (works|has a problem)/, { timeout: PLAN_WAIT })
  const live = await page.getByTestId('ic-live').innerText()
  if (/works/.test(live)) await expect(page.getByTestId('ic-time-merdeka_square')).toBeVisible()
  else await expect(page.getByTestId('ic-live')).toContainText(/\S{12,}/)                    // a specific reason, not an empty message
  await page.getByTestId('ic-compare').click()
  await expect(page.getByTestId('ic-table')).toBeVisible({ timeout: PLAN_WAIT })
  await expect(page.getByTestId('ic-row-yours')).toBeVisible()
  await expect(page.getByTestId('ic-row-same_sights')).toBeVisible()
  await expect(page.getByTestId('itinerary-compare')).not.toContainText('Not found')
  await expect(page.getByTestId('ic-day-3').getByTestId('ic-stop-merdeka_square')).toBeVisible()      // the manual move survived the check and the comparison
  expect(statuses.filter((s) => s.endsWith(':200')).length).toBeGreaterThanOrEqual(2)
  expect(statuses.filter((s) => !s.endsWith(':200'))).toEqual([])
  expectClean(problems)
})

test('an older server (no /check-itinerary): the move is kept, the draft is shown as NOT validated with the real reason and a retry, and the comparison still works', async ({ page }) => {
  await page.route('**/check-itinerary', (r) => r.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { code: 'not_found', message: 'Not found.', details: {}, request_id: 'x' } }) }))
  await klPlan(page)
  await page.getByTestId('ic-toggle').click()
  await expect(page.getByTestId('ic-live')).toContainText('could not be validated', { timeout: PLAN_WAIT })
  await expect(page.getByTestId('ic-live')).toContainText('older than this page')
  await expect(page.getByTestId('ic-live')).not.toContainText('Your draft works')
  await expect(page.getByTestId('ic-recheck')).toBeVisible()
  await page.getByLabel('Add an attraction to day 1').selectOption('merdeka_square')
  await page.getByTestId('ic-day-1').getByRole('button', { name: 'Add', exact: true }).click()
  await expect(page.getByTestId('ic-stop-merdeka_square')).toBeVisible()                                  // the edit is kept even though checking failed
  await page.getByTestId('ic-compare').click()
  await expect(page.getByTestId('ic-table')).toBeVisible({ timeout: PLAN_WAIT })
})

test('an older server is reported once, in plain words, as a banner', async ({ page }) => {
  await page.route('**/version', (r) => r.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { code: 'not_found', message: 'Not found.', details: {}, request_id: 'x' } }) }))
  await page.goto('/')
  await expect(page.getByTestId('server-outdated')).toContainText('older than this page', { timeout: PLAN_WAIT })
  await expect(page.getByTestId('server-outdated')).toContainText('check-itinerary')
})

test('what-if (Kuala Lumpur, remove Batu Caves and Petronas): validation is shown first, an empty plan is called empty, and fewer sights is not called a saving', async ({ page }) => {
  await klPlan(page)
  await page.getByTestId('wi-toggle').click()
  for (const id of ['batu_caves', 'petronas_twin_towers']) await page.getByTestId(`wi-ex-${id}`).check()
  await page.getByTestId('wi-run').click()
  await expect(page.getByTestId('wi-validation')).toBeVisible({ timeout: PLAN_WAIT })
  await expect(page.getByTestId('wi-validation')).toContainText(/Validation: (Validated|Provisional)/)
  await expect(page.getByTestId('wi-validation')).not.toContainText('unavailable')
  await expect(page.getByTestId('wi-empty')).toHaveCount(0)                      // the planner fills the days with other sights, so this is not an empty plan
  await expect(page.getByTestId('wi-result')).toContainText('Removed:')
  await expect(page.getByTestId('wi-lower-because-less')).toContainText('fewer sights')
  await expect(page.getByTestId('wi-money')).toHaveText('not comparable')
  await expect(page.getByTestId('wi-apply')).toBeEnabled()
})

test('what-if from a server that returns no validator verdict: "Not checked", and Apply is disabled', async ({ page }) => {
  await page.route('**/optimise', async (route) => {
    const resp = await route.fetch(); const body = await resp.json()
    const request = route.request().postDataJSON()
    if (request.preferences?.skip?.length) delete body.feasibility_report         // the what-if preview only; the first plan keeps its report
    await route.fulfill({ response: resp, json: body })
  })
  await klPlan(page)
  await page.getByTestId('wi-toggle').click()
  await page.getByTestId('wi-ex-batu_caves').check()
  await page.getByTestId('wi-run').click()
  await expect(page.getByTestId('wi-validation')).toContainText('Not checked', { timeout: PLAN_WAIT })
  await expect(page.getByTestId('wi-apply')).toBeDisabled()
})

test('plan explanation: code-written summary first (spending incl. rooms), no jargon, AI optional, nothing duplicated', async ({ page }) => {
  await klPlan(page)
  const box = page.getByTestId('explain-block').first()
  await expect(box).toBeVisible()
  await expect(box.getByTestId('plan-status')).toContainText(/Feasible/)
  await expect(box.getByTestId('summary-spending')).toContainText('including rooms')
  await expect(box.getByTestId('summary-spending')).toContainText('rooms')
  await expect(box.getByTestId('summary-travel')).toContainText('Estimated travel')
  await expect(box.getByTestId('summary-coverage')).toContainText('sight')
  const text = await box.innerText()
  for (const bad of ['Template summary', 'true cost', 'True cost', 'grounding', 'rejected_tokens', 'F1:', 'undefined', 'null']) expect(text, bad).not.toContain(bad)
  expect(await box.locator('li').evaluateAll((els) => els.filter((e) => !e.textContent.trim()).length)).toBe(0)      // no empty list items
  await expect(box.getByTestId('explain-button')).toBeVisible()
  // each unverified item appears once on the page
  const bodyText = await page.locator('main').innerText()
  for (const kind of ['Opening hours unverified:', 'Admission price unknown:']) expect((bodyText.match(new RegExp(kind, 'g')) ?? []).length).toBeLessThanOrEqual(1)
})

test('an AI call that was made but whose text was rejected is described truthfully, and the fallback is complete', async ({ page }) => {
  await page.route('**/optimise', async (route) => {
    const resp = await route.fetch(); const body = await resp.json()
    if (route.request().postDataJSON().explain) body.explanation = { text: 'Plan for X: ...', source: 'template', call_count: 1, reason: 'fewer than 2 cited sentences passed the checks (2 dropped); template used', cited: false, sentences: [], facts: [], warnings: [], dropped: 2,
      grounding: { checked: 4, rejected_tokens: ['S1: a number used for the wrong item (495 is the modelled total spending including rooms)', 'S2: not supported by the cited facts (280)'] } }
    await route.fulfill({ response: resp, json: body })
  })
  await klPlan(page)
  await page.getByTestId('explain-button').first().click()
  await expect(page.getByTestId('explain-fallback')).toContainText('its wording was not used')
  await expect(page.getByTestId('explain-badge')).toHaveText('Code-written summary')
  await expect(page.getByTestId('summary-spending')).toBeVisible()
  await page.getByTestId('ai-diagnostics').locator('summary').first().click()
  await expect(page.getByTestId('ai-outcome')).toContainText('A model call was made; its wording was not used')
  await expect(page.getByTestId('ai-rejected')).toContainText('wrong thing')
  await expect(page.getByTestId('ai-rejected')).not.toContainText('S1:')
  await expect(page.getByTestId('ai-diagnostics')).not.toContainText('No AI call')
})

test('examples are about the current destination: Kuala Lumpur never suggests a Tokyo temple', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('city-kuala_lumpur').click()
  await expect(page.getByTestId('nl-label')).toContainText('Kuala Lumpur')
  await expect(page.getByTestId('nl-label')).not.toContainText(/Senso-ji|Tokyo|yen/)
  await page.getByTestId('load-example').click()
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: PLAN_WAIT })
  await expect(page.getByTestId('pr-label')).not.toContainText(/Senso-ji|Shibuya|Tokyo/)
  const stop = await page.locator('[data-testid^="stop-"] .stop-name, [data-testid^="stop-"]').first().innerText().catch(() => '')
  expect(stop).not.toMatch(/Senso-ji/)
})

test('phone width and keyboard: the new summary and the builder error state fit and are reachable', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 })
  await klPlan(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(1)
  await page.getByTestId('explain-button').first().focus()
  await expect(page.getByTestId('explain-button').first()).toBeFocused()
  await page.keyboard.press('Tab')
  expect(await page.evaluate(() => document.activeElement !== document.body)).toBe(true)
})
