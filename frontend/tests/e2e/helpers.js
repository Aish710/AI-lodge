import { expect } from '@playwright/test'

// 1x1 transparent PNG, used so tests do not depend on the public OpenStreetMap tile servers.
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64')

/** Collect console errors/warnings and uncaught exceptions. Assert with `expectClean(problems)`. */
export function watchConsole(page) {
  const problems = []
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) problems.push(`${m.type()}: ${m.text()}`) })
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`))
  return problems
}
export const expectClean = (problems) => expect(problems, problems.join('\n')).toEqual([])

export async function stubTiles(page) {
  await page.route('https://tile.openstreetmap.org/**', (r) => r.fulfill({ status: 200, contentType: 'image/png', body: PNG }))
}
