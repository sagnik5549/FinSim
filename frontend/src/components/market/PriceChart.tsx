import clsx from 'clsx'
import {
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef, useState } from 'react'
import { samplePath, useGame, useLiveProgress } from '../../game/GameContext'
import { toUnix } from '../../game/format'
import { api } from '../../services/api'
import type { Candle, SymbolDetail } from '../../types/game'

export type Overlay = 'sma20' | 'sma50' | 'ema20' | 'bb'

const OVERLAY_COLORS: Record<string, string> = {
  sma20: '#E9B949',
  sma50: '#9B7BFF',
  ema20: '#38C6E8',
  bb_upper: '#4C8DFF',
  bb_lower: '#4C8DFF',
}

export const CHART_THEME = {
  layout: {
    background: { type: ColorType.Solid, color: 'transparent' },
    textColor: '#93A0B8',
    fontFamily: 'JetBrains Mono, ui-monospace, monospace',
    fontSize: 11,
  },
  grid: {
    vertLines: { color: 'rgba(26,36,56,0.55)' },
    horzLines: { color: 'rgba(26,36,56,0.55)' },
  },
  rightPriceScale: { borderColor: '#1A2438' },
  timeScale: { borderColor: '#1A2438', timeVisible: true, secondsVisible: false, rightOffset: 3 },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: { color: '#4C8DFF66', labelBackgroundColor: '#1F2B44', style: LineStyle.Dashed },
    horzLine: { color: '#4C8DFF66', labelBackgroundColor: '#1F2B44', style: LineStyle.Dashed },
  },
}

function bar(c: Candle) {
  return { time: toUnix(c.t) as UTCTimestamp, open: c.o, high: c.h, low: c.l, close: c.c }
}

function volBar(c: Candle) {
  return { time: toUnix(c.t) as UTCTimestamp, value: c.v, color: c.c >= c.o ? 'rgba(38,208,124,0.35)' : 'rgba(242,73,92,0.35)' }
}

export function PriceChart({
  symbol, tf = '1h', overlays = [], showVolume = true, className, limit = 240, onDetail,
}: {
  symbol: string; tf?: '1h' | '1d'; overlays?: Overlay[]; showVolume?: boolean; className?: string; limit?: number
  onDetail?: (d: SymbolDetail) => void
}) {
  const { state } = useGame()
  const { replay } = useLiveProgress()
  const box = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const candles = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volume = useRef<ISeriesApi<'Histogram'> | null>(null)
  const lines = useRef<Record<string, ISeriesApi<'Line'>>>({})
  const [detail, setDetail] = useState<SymbolDetail | null>(null)
  const [error, setError] = useState(false)
  const animRef = useRef(0)
  const version = state?.version ?? 0
  const onDetailRef = useRef(onDetail)
  onDetailRef.current = onDetail

  // Create chart once
  useEffect(() => {
    if (!box.current) return
    const c = createChart(box.current, { ...CHART_THEME, autoSize: true })
    candles.current = c.addCandlestickSeries({
      upColor: '#26D07C', downColor: '#F2495C', borderVisible: false, wickUpColor: '#26D07C', wickDownColor: '#F2495C',
      priceLineColor: '#4C8DFF', priceLineStyle: LineStyle.Dotted,
    })
    volume.current = c.addHistogramSeries({ priceScaleId: 'vol', priceFormat: { type: 'volume' }, lastValueVisible: false, priceLineVisible: false })
    c.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } })
    chart.current = c
    return () => {
      cancelAnimationFrame(animRef.current)
      c.remove()
      chart.current = null
      lines.current = {}
    }
  }, [])

  // Overlay series follow the toggles
  useEffect(() => {
    const c = chart.current
    if (!c) return
    const want = new Set<string>(overlays.flatMap((o) => (o === 'bb' ? ['bb_upper', 'bb_lower'] : [o])))
    for (const k of Object.keys(lines.current)) {
      if (!want.has(k)) {
        c.removeSeries(lines.current[k])
        delete lines.current[k]
      }
    }
    for (const k of want) {
      if (!lines.current[k]) {
        lines.current[k] = c.addLineSeries({
          color: OVERLAY_COLORS[k], lineWidth: k.startsWith('bb') ? 1 : 2, priceLineVisible: false,
          lastValueVisible: false, crosshairMarkerVisible: false,
          lineStyle: k.startsWith('bb') ? LineStyle.Dashed : LineStyle.Solid,
        })
      }
    }
    if (detail) applyOverlays(detail)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overlays.join(',')])

  function applyOverlays(d: SymbolDetail) {
    for (const [k, s] of Object.entries(lines.current)) {
      const arr = (d.indicators as unknown as Record<string, (number | null)[]>)[k] ?? []
      s.setData(d.candles.map((cd, i) => ({ time: toUnix(cd.t) as Time, value: arr[i] })).filter((p) => p.value !== null && p.value !== undefined) as { time: Time; value: number }[])
    }
  }

  // Load data whenever the game advances; animate the newest hourly candle along its tick path.
  useEffect(() => {
    let cancelled = false
    cancelAnimationFrame(animRef.current)
    api.symbol(symbol, tf, limit).then((d) => {
      if (cancelled || !candles.current) return
      setError(false)
      setDetail(d)
      onDetailRef.current?.(d)
      const isIndex = !!d.index
      const last = d.candles[d.candles.length - 1]
      const path = replay?.paths[symbol]
      const animate = tf === '1h' && !!replay && !!last && last.t === replay.t && !!path && performance.now() - replay.start < replay.duration
      const base = animate ? d.candles.slice(0, -1) : d.candles
      candles.current.setData(base.map(bar))
      volume.current?.setData(showVolume && !isIndex ? base.map(volBar) : [])
      applyOverlays(d)
      if (animate && replay && path) {
        const time = toUnix(last.t) as UTCTimestamp
        const tick = () => {
          const p = Math.min(1, (performance.now() - replay.start) / replay.duration)
          const n = Math.max(1, Math.floor(p * (path.length - 1)))
          const seen = path.slice(0, n + 1)
          const cur = samplePath(path, p) ?? last.c
          candles.current?.update({ time, open: path[0], high: Math.max(...seen, cur), low: Math.min(...seen, cur), close: cur })
          if (showVolume && !isIndex) volume.current?.update({ time, value: last.v * p, color: cur >= path[0] ? 'rgba(38,208,124,0.35)' : 'rgba(242,73,92,0.35)' })
          if (p < 1) animRef.current = requestAnimationFrame(tick)
          else {
            candles.current?.update(bar(last))
            if (showVolume && !isIndex) volume.current?.update(volBar(last))
          }
        }
        animRef.current = requestAnimationFrame(tick)
      }
    }).catch(() => !cancelled && setError(true))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, tf, version, limit, showVolume])

  // Fit on symbol/timeframe change
  useEffect(() => {
    const t = setTimeout(() => chart.current?.timeScale().fitContent(), 250)
    return () => clearTimeout(t)
  }, [symbol, tf])

  return (
    <div className={clsx('relative h-full w-full', className)}>
      <div ref={box} className="absolute inset-0" />
      {error && <div className="absolute inset-0 flex items-center justify-center text-xs text-txt-mute">Chart unavailable</div>}
    </div>
  )
}

/** Small oscillator pane (RSI or MACD) driven by precomputed backend indicators. */
export function OscillatorChart({ detail, kind }: { detail: SymbolDetail | null; kind: 'rsi' | 'macd' }) {
  const box = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const series = useRef<ISeriesApi<'Line'>[]>([])
  const hist = useRef<ISeriesApi<'Histogram'> | null>(null)

  useEffect(() => {
    if (!box.current) return
    const c = createChart(box.current, {
      ...CHART_THEME, autoSize: true, timeScale: { ...CHART_THEME.timeScale, visible: false },
      handleScroll: false, handleScale: false,
    })
    if (kind === 'rsi') {
      const s = c.addLineSeries({ color: '#9B7BFF', lineWidth: 2, priceLineVisible: false })
      s.createPriceLine({ price: 70, color: '#F2495C88', lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' })
      s.createPriceLine({ price: 30, color: '#26D07C88', lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' })
      series.current = [s]
    } else {
      hist.current = c.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false })
      series.current = [
        c.addLineSeries({ color: '#38C6E8', lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
        c.addLineSeries({ color: '#E9B949', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }),
      ]
    }
    chart.current = c
    return () => {
      c.remove()
      chart.current = null
    }
  }, [kind])

  useEffect(() => {
    if (!detail || !chart.current) return
    const t = detail.candles.map((c) => toUnix(c.t) as Time)
    const mk = (arr: (number | null)[]) => arr.map((v, i) => ({ time: t[i], value: v })).filter((p) => p.value !== null) as { time: Time; value: number }[]
    if (kind === 'rsi') series.current[0].setData(mk(detail.indicators.rsi14))
    else {
      series.current[0].setData(mk(detail.indicators.macd))
      series.current[1].setData(mk(detail.indicators.macd_signal))
      hist.current?.setData(mk(detail.indicators.macd_hist).map((p) => ({ ...p, color: p.value >= 0 ? 'rgba(38,208,124,0.5)' : 'rgba(242,73,92,0.5)' })))
    }
    chart.current.timeScale().fitContent()
  }, [detail, kind])

  return <div ref={box} className="h-full w-full" />
}
