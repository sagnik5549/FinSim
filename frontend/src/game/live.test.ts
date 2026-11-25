import { describe, expect, it } from 'vitest'
import { mergeBars } from '../components/chart/TradingChart'
import { barPath, samplePath } from './live'

describe('live price path', () => {
  it('walks a rising minute through its low before its high and ends at the close', () => {
    const pts = barPath(100, [{ o: 100, h: 103, l: 99, c: 102 }])
    expect(pts[0]).toBe(100)
    expect(pts.indexOf(99)).toBeLessThan(pts.indexOf(103))
    expect(pts[pts.length - 1]).toBe(102)
  })
  it('interpolates and clamps progress', () => {
    const path = [100, 101, 99, 102, 104]
    expect(samplePath(path, 0)).toBe(100)
    expect(samplePath(path, 0.125)).toBeCloseTo(100.5)
    expect(samplePath(path, 2)).toBe(104)
    expect(samplePath(path, -1)).toBe(100)
    expect(samplePath(undefined, 0.5)).toBeNull()
  })
})

describe('minute bars into candles', () => {
  const t0 = Date.UTC(2026, 0, 5, 9, 0) / 1000
  const bar = (m: number, o: number, h: number, l: number, c: number) => ({ time: t0 + m * 60, o, h, l, c, v: 10 })
  it('folds minutes into the 5-minute bucket and opens a new one on the boundary', () => {
    const d = mergeBars([], [bar(0, 10, 11, 9, 10.5), bar(1, 10.5, 12, 10, 11), bar(5, 11, 11.5, 10.8, 11.2)], '5m')
    expect(d).toHaveLength(2)
    expect(d[0]).toMatchObject({ time: t0, o: 10, h: 12, l: 9, c: 11, v: 20 })
    expect(d[1]).toMatchObject({ time: t0 + 300, o: 11, c: 11.2 })
  })
  it('extends the forming hourly candle', () => {
    const d = mergeBars([{ time: t0, o: 10, h: 10.2, l: 9.9, c: 10.1, v: 5 }], [bar(37, 10.1, 10.6, 10.0, 10.5)], '1h')
    expect(d).toHaveLength(1)
    expect(d[0]).toMatchObject({ h: 10.6, c: 10.5, v: 15 })
  })
})
