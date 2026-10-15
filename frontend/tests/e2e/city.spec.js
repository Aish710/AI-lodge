import { expect, test } from '@playwright/test'
import { expectClean, planFromExample, stubTiles, watchConsole } from './helpers.js'

test.beforeEach(async ({ page }) => { await stubTiles(page) })

const CITIES = ['tokyo', 'singapore', 'seoul', 'kuala_lumpur']
const WIDTHS = [320, 375, 768, 1280]
// Four hotel names per city: short, very long English, Korean, Chinese + a Malay long name (the list must hold every one without breaking its layout).
const NAMES = ['Inn', 'The Grand Imperial Riverside Heritage Boutique Hotel and Serviced Residences at the Old Town Waterfront Promenade (fictional)',
  '서울 종로구 한옥 가든 호텔 (fictional)', '上海外滩黄浦江畔豪华大酒店 (fictional)']
const MALAY = 'Hotel Seri Perdana Bukit Bintang Kuala Lumpur Sentral Persiaran Raja Chulan (fictional)'

async function patchHotels(page, names) {
  await page.route('**/data/places*', async (route) => {
    const resp = await route.fetch()
    const json = await resp.json()
    const base = json.hotels
    const four = [...base, { ...base[0], id: `${base[0].id}_x4` }].slice(0, 4)
    json.hotels = four.map((h, i) => ({ ...h, name: names[i] }))
    await route.fulfill({ response: resp, json })
  })
}

/** The compare response carries the hotel names the switch shows, so the long and native-script names are patched there too. */
async function patchCompareNames(page, names) {
  await page.route('**/compare-hotels', async (route) => {
    const resp = await route.fetch()
    const json = await resp.json()
    json.results = json.results.map((r, i) => ({ ...r, hotel_name: names[i] ?? r.hotel_name }))
    await route.fulfill({ response: resp, json })
  })
}

async function toTrip(page, city) {
  await page.goto('/')
  await page.getByTestId(`city-${city}`).click()
  await expect(page.getByTestId('city-chip')).toBeVisible()
  await expect(page.locator('article[data-testid^="card-"]').first()).toBeVisible()
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: 45_000 })
  await expect(page.getByTestId('hotel-switch')).toBeVisible()
}

for (const city of CITIES) {
  test(`${city}: the hotel switch holds long and native-script names at 320, 375, 768 and 1280 px without breaking the layout`, async ({ page }) => {
    const problems = watchConsole(page)
    const names = [NAMES[1], city === 'kuala_lumpur' ? MALAY : NAMES[2], NAMES[3], NAMES[0]]
    await patchHotels(page, names)
    await patchCompareNames(page, names)
    await toTrip(page, city)
    const options = page.getByTestId('hotel-switch').locator('.hotel-switch-option')
    await expect(options).toHaveCount(3)
    await expect(page.getByTestId('hotel-switch')).not.toContainText('fictional')
    await expect(page.getByTestId('hotel-switch')).toContainText('demo hotels with sample prices')
    await expect(page.getByTestId('hotel-switch').locator('input:checked')).toHaveCount(1)
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 800 })
      const box = await page.getByTestId('hotel-switch').boundingBox()
      for (let i = 0; i < 3; i++) {
        const b = await options.nth(i).boundingBox()
        expect(b.x + b.width, `option ${i} stays inside the switch at ${width}px`).toBeLessThanOrEqual(box.x + box.width + 1)
        const overflow = await options.nth(i).evaluate((el) => [...el.children].some((c) => c.getBoundingClientRect().right > el.getBoundingClientRect().right + 1))
        expect(overflow, `option ${i} content fits at ${width}px`).toBe(false)
      }
      const wider = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
      expect(wider, `no horizontal scrolling at ${width}px`).toBe(false)
    }
    expectClean(problems)
  })
}

test('switching the hotel re-plans in place: the old plan stays visible (dimmed), never blank, then follows the new hotel', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await planFromExample(page)
  const sw = page.getByTestId('hotel-switch')
  const otherId = await sw.locator('input:not(:checked):not(:disabled)').first().getAttribute('value')
  await page.route('**/optimise', async (r) => { await new Promise((x) => setTimeout(x, 1500)); await r.continue() })  // slow enough to observe the in-between state
  await page.locator(`label[for="hs-${otherId}"]`).click()
  await expect(page.getByTestId('plan-progress')).toBeVisible()
  await expect(page.getByTestId('trip-body')).toHaveClass(/dimmed/)
  await expect(page.getByTestId('timeline')).toBeVisible()           // the last good plan is never blanked
  await expect(page.getByTestId('trip-body')).not.toHaveClass(/dimmed/, { timeout: 20_000 })
  await expect(page.locator(`#hs-${otherId}`)).toBeChecked()
  await expect(page.getByTestId('plan-progress')).toHaveCount(0)
  expectClean(problems)
})

test('Seoul -> choices -> switch to Tokyo mid-flow: confirmation lists what is cleared and nothing carries over', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await page.getByTestId('city-seoul').click()
  await expect(page.getByTestId('city-chip')).toContainText('Seoul')
  const card = page.locator('article[data-testid^="card-"]').first()
  await expect(card).toBeVisible()
  await card.locator('label', { hasText: 'Must visit' }).click()
  await expect(page.getByTestId('wish-counts')).toContainText('1 must visit')
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: 45_000 })
  await expect(page.getByTestId('hotel-switch')).toContainText('Jongno')
  await expect(page.getByTestId('hotel-switch')).toContainText('₩')

  await page.getByTestId('edit-trip').click()
  await page.getByTestId('city-tokyo').click()
  const dialog = page.getByTestId('confirm-dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog).toContainText('Switch to Tokyo?')
  const cleared = page.getByTestId('switch-clears')
  await expect(cleared).toContainText('your wishlist (1 marked sight)')
  await expect(cleared).toContainText('your hotel selection')
  await expect(cleared).toContainText('the hotel comparison')
  // cancel keeps everything
  await page.getByTestId('dialog-cancel').click()
  await expect(page.getByTestId('city-chip').first()).toContainText('Seoul')
  // confirm clears everything
  await page.getByTestId('city-tokyo').click()
  await page.getByTestId('dialog-confirm').click()
  await expect(page.getByTestId('city-chip').first()).toContainText('Tokyo')
  await expect(page.getByTestId('city-chip').first()).toContainText('JPY')
  await expect(page.getByTestId('card-senso_ji')).toBeVisible()
  await expect(page.getByTestId('wish-counts')).toContainText('0 must visit')
  await expect(page.locator('article[data-testid^="card-"]')).toHaveCount(12)
  await page.getByTestId('plan-trip').click()
  await expect(page).toHaveURL(/\/trip$/, { timeout: 45_000 })
  await expect(page.getByTestId('hotel-switch')).toContainText('Kitsune')
  await expect(page.getByTestId('hotel-switch')).not.toContainText('Jongno')
  await page.getByTestId('compare-details').locator('summary').first().click()
  await expect(page.getByTestId('comparison-table')).toBeVisible()
  await expect(page.getByTestId('comparison-table')).not.toContainText('Jongno')
  await expect(page.getByTestId('settings-strip')).toContainText('Tokyo')
  expectClean(problems)
})

test('a map pin can be reached with the Tab key and opened with Enter', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await planFromExample(page)
  await expect(page.locator('.leaflet-container .pin').first()).toBeVisible()
  await page.getByRole('button', { name: 'Recalculate' }).focus()
  let landed = false
  for (let i = 0; i < 60 && !landed; i++) {
    await page.keyboard.press('Tab')
    landed = await page.evaluate(() => document.activeElement?.classList.contains('leaflet-marker-icon') ?? false)
  }
  expect(landed, 'a map pin received keyboard focus').toBe(true)
  const label = await page.evaluate(() => document.activeElement.getAttribute('aria-label') ?? document.activeElement.getAttribute('title'))
  expect(label).toBeTruthy()
  await page.keyboard.press('Enter')
  await expect(page.locator('.leaflet-popup')).toBeVisible()
  expectClean(problems)
})

test('every map pin has a hit area of at least 24 x 24 CSS pixels', async ({ page }) => {
  await page.goto('/')
  await planFromExample(page)
  await expect(page.locator('.leaflet-container .pin').first()).toBeVisible()
  const sizes = await page.$$eval('.leaflet-marker-icon.leaflet-interactive', (els) => els.map((e) => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)] }))
  expect(sizes.length).toBeGreaterThan(1)
  for (const [w, h] of sizes) { expect(w).toBeGreaterThanOrEqual(24); expect(h).toBeGreaterThanOrEqual(24) }
})

test('the example button loads a Seoul example while Seoul stays selected (no switch to Tokyo)', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await page.getByTestId('city-seoul').click()
  await expect(page.getByTestId('city-chip')).toContainText('Seoul')
  await expect(page.getByTestId('load-example')).toContainText('Seoul')
  await expect(page.getByTestId('load-example')).toContainText('45,000')
  await planFromExample(page)
  await expect(page.getByTestId('city-chip').first()).toContainText('Seoul')
  await expect(page.getByTestId('hotel-switch')).toContainText('Jongno')
  await expect(page.getByTestId('hotel-switch')).not.toContainText('Kitsune')
  await expect(page.getByTestId('confirm-dialog')).toBeHidden()   // the closed <dialog> element exists on the trip screen; no dialog is open
  expectClean(problems)
})

test('with no AI key the AI box says it is off, before any click, and the form still works', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('ai-off-note')).toContainText('AI is off in this deployment; the form works the same.')
  await expect(page.getByTestId('ai-box-mode')).toContainText('Sample mode')
  await expect(page.getByTestId('mode-indicator')).toHaveCount(1)
  await expect(page.getByTestId('plan-trip')).toBeEnabled()
})

test('map tiles send only the site origin as Referer (OpenStreetMap blocks tile requests with none), while the page policy stays no-referrer', async ({ page }) => {
  await page.goto('/')
  await planFromExample(page)
  await expect(page.locator('.leaflet-container .pin').first()).toBeVisible()
  const tile = page.locator('img.leaflet-tile').first()
  await expect(tile).toHaveAttribute('referrerpolicy', 'origin')
  expect(await page.evaluate(() => document.querySelector('meta[name=referrer]').content)).toBe('no-referrer')
})
