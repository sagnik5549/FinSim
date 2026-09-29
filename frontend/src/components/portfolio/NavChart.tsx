import { createChart, LineStyle, type IChartApi, type ISeriesApi, type Time } from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import { toUnix } from '../../game/format'
import type { NavPoint } from '../../types/game'
import { CHART_THEME } from '../market/PriceChart'

/** Portfolio value vs. the BHARAT 50 benchmark rebased to the same starting capital. */
export function NavChart({ series, target, start }: { series: NavPoint[]; target?: number; start: number }) {
  const box = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const nav = useRef<ISeriesApi<'Area'> | null>(null)
  const bench = useRef<ISeriesApi<'Line'> | null>(null)
  const tline = useRef<ReturnType<ISeriesApi<'Area'>['createPriceLine']> | null>(null)

  useEffect(() => {
    if (!box.current) return
    const c = createChart(box.current, {
      ...CHART_THEME, autoSize: true,
      localization: { priceFormatter: (p: number) => `₹${(p / 1e7).toFixed(2)}Cr` },
    })
    nav.current = c.addAreaSeries({
      lineColor: '#4C8DFF', topColor: 'rgba(76,141,255,0.28)', bottomColor: 'rgba(76,141,255,0.0)', lineWidth: 2,
      priceLineVisible: false,
    })
    bench.current = c.addLineSeries({ color: '#93A0B8', lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false })
    chart.current = c
    return () => {
      c.remove()
      chart.current = null
    }
  }, [])

  useEffect(() => {
    if (!nav.current || !bench.current || series.length === 0) return
    const dedup = new Map<number, NavPoint>()
    for (const p of series) dedup.set(toUnix(p.t), p)
    const pts = [...dedup.entries()].sort((a, b) => a[0] - b[0])
    const b0 = pts[0][1].bench
    nav.current.setData(pts.map(([t, p]) => ({ time: t as Time, value: p.nav })))
    bench.current.setData(pts.map(([t, p]) => ({ time: t as Time, value: (p.bench / b0) * start })))
    if (tline.current) nav.current.removePriceLine(tline.current)
    if (target) {
      tline.current = nav.current.createPriceLine({ price: target, color: '#E9B949', lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true, title: 'TARGET' })
    }
    chart.current?.timeScale().fitContent()
  }, [series, target, start])

  return <div ref={box} className="h-full w-full" />
}
