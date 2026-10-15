import { expect, test } from '@playwright/test'
import { expectClean, stubTiles, watchConsole } from './helpers.js'

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

async function toHotels(page, city) {
  await page.goto('/')
  await page.getByTestId(`city-${city}`).click()
  await expect(page.getByTestId('city-chip')).toBeVisible()
  await page.getByTestId('next-wishlist').click()
  await expect(page).toHaveURL(/\/wishlist$/)
  await expect(page.locator('article[data-testid^="card-"]').first()).toBeVisible()
  await page.getByRole('link', { name: /3 Hotels/ }).click()
  await expect(page.getByTestId('hotel-list')).toBeVisible()
}

for (const city of CITIES) {
  test(`${city}: hotels are stacked one per row at 320, 375, 768 and 1280 px, with long and native-script names`, async ({ page }) => {
    const problems = watchConsole(page)
    await patchHotels(page, [NAMES[0], NAMES[1], city === 'kuala_lumpur' ? MALAY : NAMES[2], NAMES[3]])
    await toHotels(page, city)
    const rows = page.getByTestId('hotel-row')
    await expect(rows).toHaveCount(4)
    await expect(page.getByTestId('hotel-note')).toHaveText('Hotels are made-up examples with sample prices.')
    await expect(page.getByTestId('hotel-list')).not.toContainText('fictional')
    await expect(page.getByTestId('hotel-list').locator('.hotel-tag')).toHaveCount(4)
    await expect(page.getByTestId('hotel-list').locator('.hotel-tag').first()).toHaveText('Demo hotel')
    await expect(page.getByTestId('selected-count')).toHaveText('3 of 4 selected, choose 2 or 3')
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 800 })
      const list = await page.getByTestId('hotel-list').boundingBox()
      let prevTop = -Infinity
      let left = null
      for (let i = 0; i < 4; i++) {
        const b = await rows.nth(i).boundingBox()
        expect(b.y, `row ${i} at ${width}px is below the previous one`).toBeGreaterThan(prevTop + 10)
        left ??= b.x
        expect(Math.abs(b.x - left), `row ${i} shares one column at ${width}px`).toBeLessThan(2)
        expect(b.width, `row ${i} spans the list at ${width}px`).toBeGreaterThan(list.width * 0.85)
        // nothing inside a row sticks out of it
        const overflow = await rows.nth(i).evaluate((el) => [...el.children].some((c) => c.getBoundingClientRect().right > el.getBoundingClientRect().right + 1))
        expect(overflow, `row ${i} content fits at ${width}px`).toBe(false)
        prevTop = b.y
      }
      const wider = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
      expect(wider, `no horizontal scrolling at ${width}px`).toBe(false)
    }
    expectClean(problems)
  })
}

test('the Compare button explains why it is disabled and the count follows the selection', async ({ page }) => {
  const problems = watchConsole(page)
  await toHotels(page, 'tokyo')
  const boxes = page.getByTestId('hotel-list').getByRole('checkbox')
  await expect(page.getByTestId('selected-count')).toHaveText('3 of 3 selected, choose 2 or 3')
  await expect(page.getByTestId('compare-reason')).toHaveCount(0)
  await boxes.nth(2).uncheck()
  await boxes.nth(1).uncheck()
  await expect(page.getByTestId('selected-count')).toHaveText('1 of 3 selected, choose 2 or 3')
  await expect(page.getByTestId('compare')).toBeDisabled()
  await expect(page.getByTestId('compare-reason')).toContainText('Choose at least 2 hotels')
  await boxes.nth(1).check()
  await expect(page.getByTestId('compare')).toBeEnabled()
  expectClean(problems)
})

test('Seoul -> choices -> switch to Tokyo mid-flow: confirmation lists what is cleared and nothing carries over', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await page.getByTestId('city-seoul').click()
  await expect(page.getByTestId('city-chip')).toContainText('Seoul')
  await page.getByTestId('next-wishlist').click()
  const card = page.locator('article[data-testid^="card-"]').first()
  await expect(card).toBeVisible()
  await card.locator('label', { hasText: 'Must visit' }).click()
  await expect(page.getByTestId('wish-counts')).toContainText('1 must visit')
  await page.getByTestId('next-hotels').click()
  await expect(page.getByTestId('comparison-table')).toBeVisible()
  await expect(page.getByTestId('hotel-list')).toContainText('Jongno')
  await expect(page.getByTestId('hotel-list')).toContainText('₩')

  await page.getByRole('link', { name: /1 Trip/ }).click()
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
  await expect(page.getByTestId('city-chip')).toContainText('Seoul')
  // confirm clears everything
  await page.getByTestId('city-tokyo').click()
  await page.getByTestId('dialog-confirm').click()
  await expect(page.getByTestId('city-chip')).toContainText('Tokyo')
  await expect(page.getByTestId('city-chip')).toContainText('JPY')
  await page.getByRole('link', { name: /2 Sights/ }).click()
  await expect(page.getByTestId('card-senso_ji')).toBeVisible()
  await expect(page.getByTestId('wish-counts')).toContainText('0 must visit')
  await expect(page.locator('article[data-testid^="card-"]')).toHaveCount(12)
  await page.getByRole('link', { name: /3 Hotels/ }).click()
  await expect(page.getByTestId('hotel-list')).toContainText('Kitsune')
  await expect(page.getByTestId('hotel-list')).not.toContainText('Jongno')
  await expect(page.getByTestId('comparison-table')).toBeVisible()
  await expect(page.getByTestId('comparison-table')).not.toContainText('Jongno')
  await expect(page.getByTestId('settings-strip')).toContainText('Tokyo')
  expectClean(problems)
})

test('a map pin can be reached with the Tab key and opened with Enter', async ({ page }) => {
  const problems = watchConsole(page)
  await page.goto('/')
  await page.getByTestId('load-example').click()
  await page.locator('button.btn-primary', { hasText: 'Use this hotel' }).click()
  await expect(page).toHaveURL(/\/itinerary$/)
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
  await page.getByTestId('load-example').click()
  await page.locator('button.btn-primary', { hasText: 'Use this hotel' }).click()
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
  await page.getByTestId('load-example').click()
  await expect(page).toHaveURL(/\/hotels$/)
  await expect(page.getByTestId('city-chip').first()).toContainText('Seoul')
  await expect(page.getByTestId('hotel-list')).toContainText('Jongno')
  await expect(page.getByTestId('hotel-list')).not.toContainText('Kitsune')
  await expect(page.getByTestId('confirm-dialog')).toHaveCount(0)
  expectClean(problems)
})
