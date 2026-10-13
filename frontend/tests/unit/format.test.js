import { describe, expect, it } from 'vitest'
import { formatJpy, formatMoney, formatSgd, humanMinutes, jpyToSgd, minutesToHm, formatHours1, weekdayOfDay, UNKNOWN } from '../../src/lib/format.js'

describe('formatters', () => {
  it('formats JPY with grouping and shows unknown for missing values, never 0 or blank', () => {
    expect(formatJpy(12345)).toBe('¥12,345')
    expect(formatJpy(0)).toBe('¥0')
    for (const v of [null, undefined, NaN]) expect(formatJpy(v)).toBe(UNKNOWN)
    expect(UNKNOWN).toBe('unknown')
  })
  it('converts to SGD only with the supplied (labelled, sample) rate', () => {
    expect(jpyToSgd(11000, 110)).toBe(100)
    expect(formatSgd(11000, 110)).toBe('S$100.00')
    expect(formatSgd(1234, 110)).toBe('S$11.22')
    expect(formatSgd(null, 110)).toBe(UNKNOWN)
    expect(formatSgd(1000, 0)).toBe(UNKNOWN)
    expect(formatMoney(11000, { jpy_per_sgd: 110 })).toBe('¥11,000 (≈ S$100.00)')
    expect(formatMoney(11000, null)).toBe('¥11,000')
    expect(formatMoney(null, { jpy_per_sgd: 110 })).toBe(UNKNOWN)
  })
  it('turns minutes into h:mm', () => {
    expect([0, 5, 59, 60, 65, 125, 600].map(minutesToHm)).toEqual(['0:00', '0:05', '0:59', '1:00', '1:05', '2:05', '10:00'])
    expect(minutesToHm(-65)).toBe('-1:05')
    expect(minutesToHm(null)).toBe(UNKNOWN)
  })
  it('writes durations for sentences', () => {
    expect([humanMinutes(35), humanMinutes(60), humanMinutes(125), humanMinutes(null)]).toEqual(['35 min', '1 h 00 min', '2 h 05 min', UNKNOWN])
  })
  it('describes opening hours without ever calling unknown "open"', () => {
    expect(formatHours1([['09:00', '17:00']])).toBe('09:00-17:00')
    expect(formatHours1([['09:00', '12:00'], ['13:00', '17:00']])).toBe('09:00-12:00, 13:00-17:00')
    expect(formatHours1(null)).toBe('closed')
    expect(formatHours1('unknown')).toBe('unknown hours')
  })
  it('maps trip days to weekdays', () => {
    expect([1, 2, 3, 4].map((d) => weekdayOfDay(5, d))).toEqual(['sat', 'sun', 'mon', 'tue'])
  })
})
