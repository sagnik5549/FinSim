import { describe, expect, it } from 'vitest'
import { money, pct, price, toUnix, tone } from './format'

describe('Indian number formatting', () => {
  it('formats crore and lakh', () => {
    expect(money(100e7)).toBe('₹100.00 Cr')
    expect(money(24.5e5)).toBe('₹24.50 L')
    expect(money(4900)).toBe('₹4,900')
    expect(money(-2.5e7, { signed: true })).toBe('−₹2.50 Cr')
    expect(money(8.75e7, { signed: true })).toBe('+₹8.75 Cr')
  })
  it('formats prices with Indian digit grouping', () => {
    expect(price(124512.5)).toBe('₹1,24,512.50')
  })
  it('formats percentages with sign', () => {
    expect(pct(0.0085)).toBe('+0.85%')
    expect(pct(-0.034)).toBe('−3.40%')
    expect(pct(0.1, 0, false)).toBe('10%')
  })
  it('classifies tone', () => {
    expect(tone(1)).toBe('up')
    expect(tone(-1)).toBe('down')
    expect(tone(0)).toBe('flat')
  })
  it('treats naive game timestamps as UTC', () => {
    expect(toUnix('2026-01-05T09:00:00')).toBe(Date.UTC(2026, 0, 5, 9) / 1000)
    expect(toUnix('2026-01-05')).toBe(Date.UTC(2026, 0, 5) / 1000)
  })
})
