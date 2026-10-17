// "What I could and couldn't apply": keywords per group and language, the footer wording, suggestions that need an Accept click, and the rule that only form fields reach the planner.
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import NlParsePanel from '../../src/components/NlParsePanel.vue'
import { detectHeard, HEARD_FOOTER, HEARD_GROUPS, suggestionFor } from '../../src/lib/heard.js'
import { appliedRows } from '../../src/lib/understood.js'
import { DEFAULT_FORM } from '../../src/lib/prefs.js'
import { currentPrefs, resetAll, store } from '../../src/store.js'
import places from '../fixtures/places.json'

// one real-looking sentence per group and language
const SENTENCES = {
  walking: { en: 'Three days, I do not want to walk much.', ms: 'Tiga hari, saya tidak mahu banyak berjalan.', ko: '3일 여행, 많이 걷고 싶지 않아요.', zh: '三天行程，我不想走路太多。' },
  quiet: { en: 'Three days, quiet places please, no crowds.', ms: 'Tiga hari, tempat yang tenang, tidak sesak.', ko: '3일 여행, 조용한 곳이 좋아요.', zh: '三天行程，想去安静的地方。' },
  access: { en: 'Three days, we need wheelchair access.', ms: 'Tiga hari, kami perlukan kerusi roda.', ko: '3일 여행, 휠체어가 필요해요.', zh: '三天行程，需要轮椅无障碍。' },
  family: { en: 'Three days with two kids and my grandparents.', ms: 'Tiga hari bersama kanak-kanak dan nenek.', ko: '3일 여행, 아이와 부모님이 함께 가요.', zh: '三天行程，带孩子和老人。' },
  diet: { en: 'Three days, I am vegetarian and need halal food.', ms: 'Tiga hari, saya vegetarian dan perlukan makanan halal.', ko: '3일 여행, 채식을 해요.', zh: '三天行程，我吃素。' },
}
const parseOk = (over = {}) => ({ status: 'ok', draft: { days: 3, budget: null, strict_budget: false, pace: 'balanced', interests: [], must_visit: ['senso_ji'], skip: [], day_start: '09:00', day_end: '19:00',
  value_of_time_per_hour: 1000, max_walking_minutes_per_day: 90, start_weekday: 2, allow_unknown_hours: false, nights: null, locked: [] }, raw_input_echo: 'x', extracted_json: { days: 3 },
  resolved_names: [], unresolved_names: [], ambiguities: [], defaults_applied: ['pace: balanced (not stated)'], clarifications: [], unclear: [], assumptions: {}, call_count: 1, mode: 'llm', prompt_version: '2', ...over })

beforeEach(() => { resetAll(); store.cityId = 'tokyo'; store.city = { currency_code: 'JPY', display_currency_code: 'SGD' }; store.places = places.attractions })
afterEach(() => { resetAll(); store.parseResult = null })

describe('the keyword map', () => {
  for (const [group, byLang] of Object.entries(SENTENCES)) {
    for (const [lang, sentence] of Object.entries(byLang)) {
      it(`${group} is heard in ${lang}`, () => {
        expect(detectHeard(sentence).map((g) => g.id)).toContain(group)
      })
    }
  }
  it('every group has terms in all four languages', () => {
    for (const g of HEARD_GROUPS) for (const lang of ['en', 'ms', 'ko', 'zh']) expect(g[lang].length, `${g.id} ${lang}`).toBeGreaterThan(0)
  })
  it('does not fire on ordinary requests, place names that contain a short keyword, or the AI-box examples', () => {
    for (const t of ['3 days in Tokyo, relaxed pace, I must see Senso-ji and Tokyo Skytree. Budget 40,000 yen.', 'A day trip to Okutama and Bukit Bintang', '3 days in Seoul, balanced pace, must see Gyeongbokgung.', 'Gardens by the Bay and Jewel Changi', '东京三天，浅草寺，预算三万日元', 'Busan is not on the list'])
      expect(detectHeard(t), t).toEqual([])
  })
  it('shows back the words it matched, whole words only unless marked as a prefix', () => {
    expect(detectHeard('The crowded streets and my kid')).toEqual([expect.objectContaining({ id: 'quiet', terms: ['crowd'] }), expect.objectContaining({ id: 'family', terms: ['kid'] })])
    expect(detectHeard('okutama')).toEqual([])
    expect(detectHeard('oku friendly')).toEqual([expect.objectContaining({ id: 'access' })])
  })
  it('uses the agreed footer wording', () => {
    expect(HEARD_FOOTER).toBe('This is shown, not applied. The sample data has no walking, accessibility or crowd information.')
  })
})

describe('suggestions are stand-ins, offered only when they would change something', () => {
  it('walking and family suggest a relaxed pace, quiet, access and diet suggest nothing', () => {
    expect(suggestionFor('walking', DEFAULT_FORM())).toMatchObject({ field: 'pace', value: 'relaxed' })
    expect(suggestionFor('family', DEFAULT_FORM())).toMatchObject({ field: 'pace', value: 'relaxed' })
    for (const g of ['quiet', 'access', 'diet']) expect(suggestionFor(g, DEFAULT_FORM())).toBeNull()
    expect(suggestionFor('walking', { ...DEFAULT_FORM(), pace: 'relaxed' })).toBeNull()
    expect(suggestionFor('walking', DEFAULT_FORM()).why).toContain('not a walking limit')
  })
})

describe('the panel: shown, not applied; nothing changes without a click; only form fields reach the planner', () => {
  it('lists the AI notes, the keywords from the user\'s own sentence, interests and the footer, and none of it is an "applied" row', () => {
    store.parseResult = parseOk({ raw_input_echo: SENTENCES.walking.en + ' ' + SENTENCES.diet.en, unclear: ['how busy the places are'], draft: { ...parseOk().draft, interests: ['food'] } })
    const w = mount(NlParsePanel)
    const heard = w.get('[data-testid=nl-heard]').text()
    expect(heard).toContain("Heard, but the planner can't act on this yet")
    expect(heard).toContain('The AI was unsure about: how busy the places are')
    expect(heard).toContain('Walking or mobility') ; expect(heard).toContain('Dietary needs')
    expect(heard).toContain('Interests: food. They only highlight sights')
    expect(w.get('[data-testid=heard-footer]').text()).toBe(HEARD_FOOTER)
    const applied = w.get('[data-testid=nl-rows]').text()
    expect(applied).not.toMatch(/walk|vegetarian|food|busy/i)
    expect(applied).toContain('Days')
  })
  it('the "Applied to the form" list holds only fields the planner uses, each with an AI read marker and a Change link', () => {
    const rows = appliedRows(parseOk({ draft: { ...parseOk().draft, budget: 40000, interests: ['food'], pace: 'relaxed' }, defaults_applied: [] }), { places: places.attractions, currency: 'JPY' })
    expect(rows.map((r) => r.field)).toEqual(['days', 'budget', 'pace', 'must'])
    store.parseResult = parseOk({ draft: { ...parseOk().draft, budget: 40000 } })
    const w = mount(NlParsePanel)
    expect(w.findAll('[data-testid=nl-rows] [data-testid=ai-mark]').length).toBeGreaterThanOrEqual(3)
    expect(w.findAll('[data-testid^=change-]').length).toBeGreaterThanOrEqual(3)
  })
  it('a preference is never turned into a constraint silently: the form and the planner request are unchanged until Accept is clicked', async () => {
    store.parseResult = parseOk({ raw_input_echo: SENTENCES.walking.en })
    store.form = { ...DEFAULT_FORM(), days: 3, pace: 'balanced' }
    const before = JSON.stringify(currentPrefs().prefs)
    const w = mount(NlParsePanel)
    expect(w.get('[data-testid=suggestion]').text()).toContain('Relaxed pace')
    expect(store.form.pace).toBe('balanced')
    expect(JSON.stringify(currentPrefs().prefs)).toBe(before)                   // heard text and suggestions do not reach the request
    await w.get('[data-testid=suggestion-accept]').trigger('click')
    expect(store.form.pace).toBe('relaxed')
    expect(currentPrefs().prefs.pace).toBe('relaxed')
    expect(w.get('[data-testid=suggestion-accepted]').text()).toContain('set to relaxed')
    // only that one field differs from before: nothing else slipped into the request
    const after = currentPrefs().prefs
    expect({ ...after, pace: 'balanced' }).toEqual(JSON.parse(before))
  })
  it('keywords never add a field to the request (no walking, accessibility, crowd, family or diet key)', () => {
    const keysBefore = Object.keys(currentPrefs().prefs).sort()
    store.parseResult = parseOk({ raw_input_echo: Object.values(SENTENCES).map((s) => s.en).join(' ') })
    mount(NlParsePanel)
    expect(Object.keys(currentPrefs().prefs).sort()).toEqual(keysBefore)                  // the request has exactly the keys it always had
    expect(keysBefore.filter((k) => /access|crowd|quiet|family|child|diet|halal|vegetarian/i.test(k))).toEqual([])
  })
  it('nothing is shown when nothing was heard', () => {
    store.parseResult = parseOk({ raw_input_echo: '3 days in Tokyo, relaxed pace.' })
    expect(mount(NlParsePanel).find('[data-testid=nl-heard]').exists()).toBe(false)
  })
})
