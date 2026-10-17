// "Heard, but the planner can't act on this yet": preferences that appear in the user's OWN sentence and that the planner has no data for.
// A small keyword map, built in the browser, in English, Malay, Korean and Chinese. It only LISTS what was said. A subjective preference is never turned into a hard
// constraint, and nothing here changes the form: a SUGGESTION (an honest structured stand-in) changes something only when the user clicks Accept.
export const HEARD_FOOTER = 'This is shown, not applied. The sample data has no walking, accessibility or crowd information.'

export const HEARD_GROUPS = [
  { id: 'walking', label: 'Walking or mobility',
    en: ['walk*', 'on foot', 'mobility', 'stairs', 'steep', 'hills', 'tired legs'], ms: ['berjalan kaki', 'jalan kaki', 'banyak berjalan', 'mobiliti', 'tangga'],
    ko: ['걷', '도보', '계단', '이동이 불편', '언덕'], zh: ['走路', '步行', '少走', '爬楼梯', '行动不便', '爬山'] },
  { id: 'quiet', label: 'Quiet places or crowds',
    en: ['quiet', 'crowd*', 'busy', 'peaceful', 'tourist trap', 'calm'], ms: ['tenang', 'sesak', 'ramai', 'sunyi', 'senyap'],
    ko: ['조용', '붐비', '한적', '사람 많', '사람이 많'], zh: ['安静', '人多', '拥挤', '清静', '人少', '人山人海'] },
  { id: 'access', label: 'Accessibility',
    en: ['wheelchair', 'accessible', 'accessibility', 'step-free', 'disabled', 'disability'], ms: ['kerusi roda', 'oku', 'boleh diakses', 'akses'],
    ko: ['휠체어', '접근성', '장애인', '장애'], zh: ['轮椅', '无障碍', '残疾', '残障'] },
  { id: 'family', label: 'Children or older travellers',
    en: ['kids', 'kid', 'child', 'children', 'toddler', 'baby', 'elderly', 'grandparent*', 'senior citizen*', 'old parents'], ms: ['kanak-kanak', 'anak', 'bayi', 'warga emas', 'nenek', 'datuk', 'ibu bapa tua'],
    ko: ['아이', '아기', '어린이', '노인', '부모님', '할머니', '할아버지'], zh: ['孩子', '小孩', '儿童', '老人', '宝宝', '长辈', '带娃'] },
  { id: 'diet', label: 'Dietary needs',
    en: ['vegetarian', 'vegan', 'halal', 'kosher', 'gluten', 'allerg*', 'no pork'], ms: ['halal', 'vegetarian', 'alahan', 'tanpa babi', 'vegan'],
    ko: ['채식', '할랄', '알레르기', '비건'], zh: ['素食', '吃素', '清真', '过敏', '纯素'] },
]

const LATIN = /^[\x00-\x7f\s'-]+$/
const norm = (s) => String(s ?? '').normalize('NFKC').toLowerCase()

/** Which groups the sentence touches, with the words that matched (shown back to the user). A Latin term must be a whole word (so "oku" does not match "Okutama"); a trailing * makes it a prefix ("crowd*" finds "crowded"). Korean and Chinese terms match as substrings. */
export function detectHeard(text) {
  const t = norm(text)
  const out = []
  for (const g of HEARD_GROUPS) {
    const hits = []
    for (const lang of ['en', 'ms', 'ko', 'zh']) {
      for (const term of g[lang]) {
        const prefix = term.endsWith('*')
        const k = norm(prefix ? term.slice(0, -1) : term)
        const esc = k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
        const found = LATIN.test(k) ? new RegExp(`(^|[^a-z0-9])${esc}${prefix ? '' : '($|[^a-z0-9])'}`).test(t) : t.includes(k)
        const shown = prefix ? term.slice(0, -1) : term
        if (found && !hits.includes(shown)) hits.push(shown)
      }
    }
    if (hits.length) out.push({ id: g.id, label: g.label, terms: hits })
  }
  return out
}

/** An honest structured stand-in, offered only as a SUGGESTION. It is not what the user asked for, and the text says so. */
export const SUGGESTIONS = {
  walking: { field: 'pace', value: 'relaxed', text: 'Relaxed pace (at most 2 sights a day).', why: 'A stand-in: fewer sights a day usually means less walking in total. It is not a walking limit; the data has no walking distances.' },
  family: { field: 'pace', value: 'relaxed', text: 'Relaxed pace (at most 2 sights a day).', why: 'A stand-in for shorter days. It does not check that places suit children or older travellers; the data has no such information.' },
}

/** The suggestion for a group, or null if none applies or the form already has that value. */
export function suggestionFor(groupId, form) {
  const s = SUGGESTIONS[groupId]
  return s && form[s.field] !== s.value ? { groupId, ...s } : null
}
