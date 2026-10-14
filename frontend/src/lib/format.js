// Display formatters. Rule: a missing value is shown as "unknown", never as 0 or blank.
export const UNKNOWN = 'unknown'
const missing = (v) => v === null || v === undefined || (typeof v === 'number' && !Number.isFinite(v))

export function formatJpy(n) {
  return missing(n) ? UNKNOWN : `¥${Math.round(n).toLocaleString('en-US')}`
}

// Currency symbols. RULE: a symbol is printed only if it is unique among the currencies of ALL supported cities; a shared symbol
// (the yen sign is both JPY and CNY) prints the ISO code instead ("JPY 1,500", "CNY 1,500"). A currency with no known symbol prints
// "1,500 XYZ". The supported set is registered from /data/cities (see the store); the default is the cities that ship today.
const SYMBOLS = { JPY: '¥', CNY: '¥', KRW: '₩', SGD: 'S$', MYR: 'RM', USD: '$' }
let supported = new Set(['JPY', 'KRW', 'SGD', 'MYR'])

/** Replace the registered currencies (the codes of every supported city). Returns a function that restores the previous set. */
export function setSupportedCurrencies(codes) {
  const before = supported
  supported = new Set(codes.filter(Boolean))
  return () => { supported = before }
}

/** The symbol to print, `null` when it would be shared (print the code), `undefined` when the currency has no known symbol. */
export function symbolFor(code) {
  const sym = SYMBOLS[code]
  if (!sym) return undefined
  const sharedWith = [...supported, code].some((c) => c !== code && SYMBOLS[c] === sym)
  return sharedWith ? null : sym
}

function withCurrency(text, code) {
  const sym = symbolFor(code)
  if (sym === undefined) return `${text} ${code}`
  return sym === null ? `${code} ${text}` : `${sym}${text}`
}

export function formatLocalMoney(n, currency = 'JPY') {
  if (missing(n)) return UNKNOWN
  return withCurrency(Math.round(n).toLocaleString('en-US'), currency)
}

export function formatDisplayMoney(local, city) {
  if (missing(local)) return UNKNOWN
  const rate = city?.sample_fx_to_display_currency ?? city?.display_fx?.rate
  const cur = city?.display_currency_code
  if (!rate || !cur) return UNKNOWN
  const value = (local * rate).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return withCurrency(value, cur)
}

export function jpyToSgd(jpy, jpyPerSgd) {
  return missing(jpy) || !jpyPerSgd ? null : jpy / jpyPerSgd
}

/** "S$11.25". The rate is a labelled SAMPLE rate; callers show the label next to it (see fxLabel). */
export function formatSgd(jpy, jpyPerSgd) {
  const v = jpyToSgd(jpy, jpyPerSgd)
  return v === null ? UNKNOWN : `S$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatMoney(jpy, fx) {
  if (missing(jpy)) return UNKNOWN
  if (fx?.currency_code) {
    const local = formatLocalMoney(jpy, fx.currency_code)
    const rate = fx.rate ?? fx.sample_fx_to_display_currency
    const display = rate && fx.display_currency_code ? formatDisplayMoney(jpy, { sample_fx_to_display_currency: rate, display_currency_code: fx.display_currency_code }) : null
    return display ? `${local} (≈ ${display})` : local
  }
  return fx?.jpy_per_sgd ? `${formatJpy(jpy)} (≈ ${formatSgd(jpy, fx.jpy_per_sgd)})` : formatJpy(jpy)
}

/** minutes -> "h:mm" (65 -> "1:05"). */
export function minutesToHm(min) {
  if (missing(min)) return UNKNOWN
  const m = Math.round(min)
  const sign = m < 0 ? '-' : ''
  const a = Math.abs(m)
  return `${sign}${Math.floor(a / 60)}:${String(a % 60).padStart(2, '0')}`
}

/** minutes -> "1 h 05 min" / "35 min" for sentences. */
export function humanMinutes(min) {
  if (missing(min)) return UNKNOWN
  const a = Math.round(min)
  const h = Math.floor(a / 60)
  const m = a % 60
  return h ? `${h} h ${String(m).padStart(2, '0')} min` : `${m} min`
}

export function formatHours(minutes) {
  return missing(minutes) ? UNKNOWN : `${(minutes / 60).toFixed(2)} h`
}

export const WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
export const WEEKDAY_NAMES = { mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday', fri: 'Friday', sat: 'Saturday', sun: 'Sunday' }

/** weekday key of trip day (1-based) given the start weekday index 0=Mon. */
export function weekdayOfDay(startWeekday, day) {
  return WEEKDAYS[(startWeekday + day - 1) % 7]
}

/** opening hours for one weekday -> readable text. null = closed, 'unknown' = not known (never "open"). */
export function formatHours1(h) {
  if (h === 'unknown') return 'unknown hours'
  if (h === null || h === undefined) return 'closed'
  return h.map(([o, c]) => `${o}-${c}`).join(', ')
}

export function titleCase(s) {
  return String(s ?? '').replace(/[_-]+/g, ' ').replace(/^./, (c) => c.toUpperCase())
}
