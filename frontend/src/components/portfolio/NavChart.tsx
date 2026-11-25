import { ColorType, createChart, LineStyle, type IChartApi, type ISeriesApi, type Time } from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import { toUnix } from '../../game/format'
import { color, onThemeChange } from '../../game/theme'
import type { NavPoint } from '../../types/game'

function theme() {
  return {
    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: color('txt-mute'), fontFamily: 'Inter, system-ui, sans-serif', fontSize: 11 },
    grid: { vertLines: { color: color('line', 0.55) }, horzLines: { color: color('line', 0.55) } },
    rightPriceScale: { borderColor: color('line') },
    timeScale: { borderColor: color('line'), timeVisible: true, secondsVisible: false },
  }
}

/** Portfolio value vs. the BHARAT 50 benchmark rebased to the same starting capital. */
export function NavChart({ series, target, start }: { series: NavPoint[]; target?: number; start: number }) {
  const box = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const nav = useRef<ISeriesApi<'Area'> | null>(null)
  const bench = useRef<ISeriesApi<'Line'> | null>(null)
  const tline = useRef<ReturnType<ISeriesApi<'Area'>['createPriceLine']> | null>(null)

  useEffect(() => {
    if (!box.current) return
    const c = createChart(box.current, { ...theme(), autoSize: true, localization: { priceFormatter: (p: number) => `₹${(p / 1e7).toFixed(2)}Cr` } })
    const paint = () => {
      c.applyOptions(theme())
      nav.current?.applyOptions({ lineColor: color('info'), topColor: color('info', 0.22), bottomColor: color('info', 0) })
      bench.current?.applyOptions({ color: color('txt-mute') })
    }
    nav.current = c.addAreaSeries({ lineWidth: 2, priceLineVisible: false })
    bench.current = c.addLineSeries({ lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false })
    chart.current = c
    paint()
    const off = onThemeChange(paint)
    return () => {
      off()
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
      tline.current = nav.current.createPriceLine({ price: target, color: color('gold'), lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true, title: 'Target' })
    }
    chart.current?.timeScale().fitContent()
  }, [series, target, start])

  return <div ref={box} className="h-full w-full" />
}
