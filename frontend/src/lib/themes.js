// Themes group and filter sights in the interface only: the solver never sees them. The mapping is frontend/src/lib/themes.json
// (one PRIMARY theme per sight, generated into docs/design/themes-inventory.md and pinned by backend/tests/test_themes.py).
import cfg from './themes.json'

export const THEMES = cfg.themes                       // [{ id, label, icon, short }]
export const THEME_IDS = THEMES.map((t) => t.id)
export const LIMITED_BELOW = cfg.limited_below
const BY_ID = Object.fromEntries(THEMES.map((t) => [t.id, t]))

/** The primary theme id of a place. An unmapped category is a data error and throws (the backend test makes sure it cannot ship). */
export function themeOf(place) {
  const over = cfg.overrides[place?.id]
  const id = over ? over.theme : cfg.category[place?.category]
  if (!id) throw new Error(`No theme for category '${place?.category}' (${place?.id})`)
  return id
}
export const themeInfo = (id) => BY_ID[id] ?? { id, label: id, icon: '•', short: '?' }
export const themeLabel = (placeOrId) => themeInfo(typeof placeOrId === 'string' ? placeOrId : themeOf(placeOrId)).label
export const themeIcon = (placeOrId) => themeInfo(typeof placeOrId === 'string' ? placeOrId : themeOf(placeOrId)).icon

/** { sightseeing: n, shopping: n, food: n } for a list of places. */
export function countByTheme(places) {
  const c = Object.fromEntries(THEME_IDS.map((t) => [t, 0]))
  for (const p of places ?? []) c[themeOf(p)] += 1
  return c
}
export const isLimited = (n) => n < LIMITED_BELOW

/** "2 Sightseeing, 1 Shopping" for the sights in `places` that satisfy `pick` (zero counts are left out). */
export function mixText(places, { lower = false } = {}) {
  const c = countByTheme(places)
  const parts = THEMES.filter((t) => c[t.id]).map((t) => `${c[t.id]} ${lower ? t.label.toLowerCase() : t.label}`)
  return parts.join(', ')
}

/** Free-text interests (from the AI reading, or typed) to theme ids, by keyword. Purely a highlight: it never changes what the planner does. */
export function interestsToThemes(interests = []) {
  const out = new Set()
  for (const raw of interests) {
    const text = String(raw).toLowerCase()
    for (const [theme, words] of Object.entries(cfg.interest_keywords)) {
      if (words.some((w) => text === w || new RegExp(`\\b${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(s|es)?\\b`).test(text))) out.add(theme)
    }
  }
  return out
}
