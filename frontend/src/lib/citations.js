// Citation chips: hovering or focusing a chip (F5) highlights the number it cites in the tables of the page. A match is a table cell, tile or verdict whose digits
// contain the number written in the cited fact. The highlight is an outline (a shape), never colour alone, and it is removed on leave or blur.
const SELECTOR = 'main td, main th, main .tile-value, main .verdict, main .verdict-detail, main [data-testid^="day-facts"], main [data-testid^="cost-"]'
export const HL = 'fact-hl'

/** Numbers of three or more digits in a fact line ("31,090 JPY" -> "31090"); shorter ones match too many cells to mean anything. */
export function citedNumbers(factText) {
  return [...new Set([...String(factText).matchAll(/\d[\d,]*/g)].map((m) => m[0].replace(/,/g, '')).filter((d) => d.length >= 3))]
}

export function highlightFact(factText, root = document) {
  clearHighlights(root)
  const nums = citedNumbers(factText)
  const hits = []
  if (!nums.length) return hits
  for (const el of root.querySelectorAll(SELECTOR)) {
    if (el.closest('[data-testid=explain-block]')) continue
    const digits = (el.textContent ?? '').replace(/[^\d]/g, '')
    if (digits && nums.some((n) => digits.includes(n)) && (el.textContent ?? '').length < 400) { el.classList.add(HL); hits.push(el); if (hits.length >= 6) break }
  }
  return hits
}

export function clearHighlights(root = document) {
  root.querySelectorAll(`.${HL}`).forEach((el) => el.classList.remove(HL))
}
