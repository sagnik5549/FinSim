import clsx from 'clsx'
import {
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type LogicalRange,
  type MouseEventParams,
  type SeriesType,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import { Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toUnix } from '../../game/format'
import { bollinger, ema, macd, rsi, sma, vwap, type Series } from '../../game/indicators'
import { liveStore, type MinuteBar } from '../../game/live'
import { color, onThemeChange } from '../../game/theme'
import { api } from '../../services/api'
import type { SymbolDetail, Timeframe } from '../../types/game'

export type ChartType = 'candles' | 'bars' | 'line' | 'area'
export type Study = 'sma20' | 'sma50' | 'ema20' | 'bb' | 'vwap' | 'volume' | 'rsi' | 'macd'
export type Tool = 'none' | 'buy' | 'sell' | 'alert'

export interface ChartLine {
  id: string
  price: number
  color: string
  title: string
  dashed?: boolean
  /** Lines that can be dragged to a new price (resting orders, alerts). */
  drag?: { kind: 'order' | 'alert'; field: 'price' | 'trigger' }
}

export interface K {
  time: number
  o: number
  h: number
  l: number
  c: number
  v: number
}

const TF_SECONDS: Record<Timeframe, number> = { '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '1d': 86400 }
const TF_LIMIT: Record<Timeframe, number> = { '1m': 900, '5m': 600, '15m': 400, '1h': 500, '1d': 250 }
const OVERLAY_COLORS: Record<string, string> = { sma20: '#e0a43a', sma50: '#8c7cf0', ema20: '#2db3c9', vwap: '#d86fb0' }

export function bucketOf(t: number, tf: Timeframe): number {
  const s = TF_SECONDS[tf]
  return t - (t % s)
}

/** Fold 1-minute bars into a candle list at the given timeframe (mutates and returns `data`). */
export function mergeBars(data: K[], bars: MinuteBar[], tf: Timeframe): K[] {
  for (const b of bars) {
    const t = bucketOf(b.time, tf)
    const last = data[data.length - 1]
    if (last && last.time === t) {
      last.h = Math.max(last.h, b.h)
      last.l = Math.min(last.l, b.l)
      last.c = b.c
      last.v += b.v
    } else if (!last || t > last.time) {
      data.push({ time: t, o: b.o, h: b.h, l: b.l, c: b.c, v: b.v })
    }
  }
  return data
}

function theme() {
  return {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: color('txt-mute'),
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize: 11,
    },
    grid: { vertLines: { color: color('line', 0.55) }, horzLines: { color: color('line', 0.55) } },
    rightPriceScale: { borderColor: color('line') },
    timeScale: { borderColor: color('line'), timeVisible: true, secondsVisible: false, rightOffset: 6 },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: color('txt-mute', 0.6), labelBackgroundColor: color('ink-600'), style: LineStyle.Dashed },
      horzLine: { color: color('txt-mute', 0.6), labelBackgroundColor: color('ink-600'), style: LineStyle.Dashed },
    },
  }
}

const fmtPrice = (p: number) => p.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function TradingChart({
  symbol, tf, type = 'candles', studies = ['volume'], lines = [], tool = 'none', onPick, onLineDrag, onDetail,
  className, watermark = true, legend = true,
}: {
  symbol: string
  tf: Timeframe
  type?: ChartType
  studies?: Study[]
  lines?: ChartLine[]
  tool?: Tool
  onPick?: (price: number, tool: Tool) => void
  onLineDrag?: (line: ChartLine, price: number) => void
  onDetail?: (d: SymbolDetail) => void
  className?: string
  watermark?: boolean
  legend?: boolean
}) {
  const mainBox = useRef<HTMLDivElement>(null)
  const rsiBox = useRef<HTMLDivElement>(null)
  const macdBox = useRef<HTMLDivElement>(null)
  const legendRef = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const main = useRef<ISeriesApi<SeriesType> | null>(null)
  const vol = useRef<ISeriesApi<'Histogram'> | null>(null)
  const overlays = useRef<Record<string, ISeriesApi<'Line'>>>({})
  const subs = useRef<{ rsi?: { c: IChartApi; s: ISeriesApi<'Line'> }; macd?: { c: IChartApi; m: ISeriesApi<'Line'>; sig: ISeriesApi<'Line'>; h: ISeriesApi<'Histogram'> } }>({})
  const priceLines = useRef<Map<string, IPriceLine>>(new Map())
  const data = useRef<K[]>([])
  const lastSeen = useRef(0)
  const pending = useRef<{ base: K; target: K; hi: number; lo: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [reload, setReload] = useState(0)
  const [hover, setHover] = useState(false)
  const props = useRef({ type, studies, tool, onPick, onLineDrag, onDetail, lines, tf, symbol })
  props.current = { type, studies, tool, onPick, onLineDrag, onDetail, lines, tf, symbol }
  const studyKey = studies.join(',')
  const showRsi = studies.includes('rsi')
  const showMacd = studies.includes('macd')

  // ---------------------------------------------------------------- drawing helpers
  const toPoint = (k: K) => {
    const t = k.time as UTCTimestamp
    return props.current.type === 'line' || props.current.type === 'area'
      ? { time: t, value: k.c }
      : { time: t, open: k.o, high: k.h, low: k.l, close: k.c }
  }
  const volPoint = (k: K) => ({ time: k.time as UTCTimestamp, value: k.v, color: k.c >= k.o ? color('up', 0.28) : color('down', 0.28) })

  const writeLegend = (k?: K, prev?: K) => {
    const el = legendRef.current
    if (!el) return
    if (!k) {
      el.textContent = ''
      return
    }
    const ch = prev ? k.c - prev.c : k.c - k.o
    const pc = prev ? ch / prev.c : ch / k.o
    const tone = ch >= 0 ? color('up') : color('down')
    el.innerHTML =
      `<span>O <b>${fmtPrice(k.o)}</b></span><span>H <b>${fmtPrice(k.h)}</b></span>` +
      `<span>L <b>${fmtPrice(k.l)}</b></span><span>C <b>${fmtPrice(k.c)}</b></span>` +
      `<span style="color:${tone}">${ch >= 0 ? '+' : ''}${fmtPrice(ch)} (${(pc * 100).toFixed(2)}%)</span>` +
      (k.v ? `<span>Vol <b>${k.v.toLocaleString('en-IN')}</b></span>` : '')
  }

  const drawStudies = () => {
    const c = chart.current
    if (!c) return
    const d = data.current
    const closes = d.map((k) => k.c)
    const st = props.current.studies
    const want: Record<string, Series> = {}
    if (st.includes('sma20')) want.sma20 = sma(closes, 20)
    if (st.includes('sma50')) want.sma50 = sma(closes, 50)
    if (st.includes('ema20')) want.ema20 = ema(closes, 20)
    if (st.includes('bb')) {
      const b = bollinger(closes)
      want.bb_upper = b.upper
      want.bb_lower = b.lower
    }
    if (st.includes('vwap') && props.current.tf !== '1d') want.vwap = vwap(d)
    for (const k of Object.keys(overlays.current)) {
      if (!want[k]) {
        c.removeSeries(overlays.current[k])
        delete overlays.current[k]
      }
    }
    for (const [k, arr] of Object.entries(want)) {
      let s = overlays.current[k]
      if (!s) {
        const isBand = k.startsWith('bb')
        s = c.addLineSeries({
          color: isBand ? color('info', 0.55) : OVERLAY_COLORS[k], lineWidth: isBand ? 1 : 2, priceLineVisible: false,
          lastValueVisible: false, crosshairMarkerVisible: false, lineStyle: isBand ? LineStyle.Dashed : LineStyle.Solid,
        })
        overlays.current[k] = s
      }
      s.setData(arr.map((v, i) => (v === null ? null : { time: d[i].time as UTCTimestamp, value: v })).filter(Boolean) as { time: Time; value: number }[])
    }
    vol.current?.setData(st.includes('volume') ? d.map(volPoint) : [])
    // Keep candles clear of the volume histogram at the bottom.
    main.current?.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: st.includes('volume') ? 0.2 : 0.06 } })
    const r = subs.current.rsi
    if (r) {
      const arr = rsi(closes)
      r.s.setData(arr.map((v, i) => (v === null ? { time: d[i].time as UTCTimestamp } : { time: d[i].time as UTCTimestamp, value: v })) as never)
    }
    const m = subs.current.macd
    if (m) {
      const x = macd(closes)
      const pt = (arr: Series) => arr.map((v, i) => (v === null ? { time: d[i].time as UTCTimestamp } : { time: d[i].time as UTCTimestamp, value: v })) as never
      m.m.setData(pt(x.macd))
      m.sig.setData(pt(x.signal))
      m.h.setData(x.hist.map((v, i) => (v === null ? { time: d[i].time as UTCTimestamp } : {
        time: d[i].time as UTCTimestamp, value: v, color: v >= 0 ? color('up', 0.5) : color('down', 0.5),
      })) as never)
    }
  }

  const drawAll = (fit: boolean) => {
    const s = main.current
    const c = chart.current
    if (!s || !c) return
    const d = data.current
    s.setData(d.map(toPoint) as never)
    drawStudies()
    const n = d.length
    writeLegend(d[n - 1], d[n - 2])
    if (fit && n) {
      const show = Math.min(n, props.current.tf === '1d' ? 120 : 150)
      c.timeScale().setVisibleLogicalRange({ from: n - show, to: n + 4 })
    }
  }

  // ---------------------------------------------------------------- chart lifecycle
  useEffect(() => {
    const el = mainBox.current
    if (!el) return
    const c = createChart(el, {
      ...theme(), autoSize: true,
      localization: { priceFormatter: fmtPrice },
      watermark: { visible: false, text: '', color: 'transparent' },
    })
    chart.current = c
    vol.current = c.addHistogramSeries({ priceScaleId: 'vol', priceFormat: { type: 'volume' }, lastValueVisible: false, priceLineVisible: false })
    c.priceScale('vol').applyOptions({ scaleMargins: { top: 0.84, bottom: 0 } })
    const onMove = (p: MouseEventParams) => {
      const d = data.current
      if (!p.time || !p.point) return writeLegend(d[d.length - 1], d[d.length - 2])
      const i = d.findIndex((k) => k.time === (p.time as number))
      if (i >= 0) writeLegend(d[i], d[i - 1])
    }
    c.subscribeCrosshairMove(onMove)
    const onClick = (p: MouseEventParams) => {
      const { tool: t, onPick: pick } = props.current
      if (t === 'none' || !pick || !p.point || !main.current) return
      const price = main.current.coordinateToPrice(p.point.y)
      if (price !== null) pick(Math.round(Number(price) * 20) / 20, t)
    }
    c.subscribeClick(onClick)
    const off = onThemeChange(() => {
      c.applyOptions(theme())
      for (const sc of [subs.current.rsi?.c, subs.current.macd?.c]) sc?.applyOptions(theme())
      applySeriesColors()
      drawAll(false)
    })
    return () => {
      off()
      c.remove()
      chart.current = null
      main.current = null
      vol.current = null
      overlays.current = {}
      priceLines.current.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const applySeriesColors = () => {
    const s = main.current
    if (!s) return
    const t = props.current.type
    if (t === 'candles' || t === 'bars') {
      s.applyOptions({ upColor: color('up'), downColor: color('down'), wickUpColor: color('up'), wickDownColor: color('down'), borderVisible: false } as never)
    } else if (t === 'line') {
      s.applyOptions({ color: color('info') } as never)
    } else {
      s.applyOptions({ lineColor: color('info'), topColor: color('info', 0.25), bottomColor: color('info', 0) } as never)
    }
  }

  // Main series follows the chart type
  useEffect(() => {
    const c = chart.current
    if (!c) return
    if (main.current) {
      c.removeSeries(main.current)
      priceLines.current.clear()
    }
    const common = { priceLineVisible: true, priceLineStyle: LineStyle.Dotted, lastValueVisible: true }
    main.current =
      type === 'candles' ? c.addCandlestickSeries(common)
        : type === 'bars' ? c.addBarSeries({ ...common, thinBars: false })
          : type === 'line' ? c.addLineSeries({ ...common, lineWidth: 2 })
            : c.addAreaSeries({ ...common, lineWidth: 2 })
    applySeriesColors()
    if (data.current.length) drawAll(false)
    drawLines()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type])

  // Watermark
  useEffect(() => {
    chart.current?.applyOptions({
      watermark: { visible: watermark, text: `${symbol} · ${tf.toUpperCase()}`, color: color('txt-mute', 0.12), fontSize: 44, horzAlign: 'center', vertAlign: 'center' },
    })
  }, [symbol, tf, watermark])

  // Oscillator panes (separate charts kept in sync with the main time scale)
  useEffect(() => {
    const c = chart.current
    if (!c) return
    const made: IChartApi[] = []
    const mk = (el: HTMLDivElement | null) => {
      if (!el) return null
      const sc = createChart(el, {
        ...theme(), autoSize: true, timeScale: { ...theme().timeScale, visible: false },
        handleScroll: false, handleScale: false, localization: { priceFormatter: (p: number) => p.toFixed(2) },
      })
      made.push(sc)
      return sc
    }
    if (showRsi) {
      const sc = mk(rsiBox.current)
      if (sc) {
        const s = sc.addLineSeries({ color: color('violet'), lineWidth: 1, priceLineVisible: false })
        s.createPriceLine({ price: 70, color: color('down', 0.5), lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' })
        s.createPriceLine({ price: 30, color: color('up', 0.5), lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' })
        subs.current.rsi = { c: sc, s }
      }
    }
    if (showMacd) {
      const sc = mk(macdBox.current)
      if (sc) {
        subs.current.macd = {
          c: sc,
          h: sc.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false }),
          m: sc.addLineSeries({ color: color('info'), lineWidth: 1, priceLineVisible: false, lastValueVisible: false }),
          sig: sc.addLineSeries({ color: OVERLAY_COLORS.sma20, lineWidth: 1, priceLineVisible: false, lastValueVisible: false }),
        }
      }
    }
    const sync = (r: LogicalRange | null) => {
      if (r) made.forEach((sc) => sc.timeScale().setVisibleLogicalRange(r))
    }
    c.timeScale().subscribeVisibleLogicalRangeChange(sync)
    if (data.current.length) {
      drawStudies()
      sync(c.timeScale().getVisibleLogicalRange())
    }
    return () => {
      c.timeScale().unsubscribeVisibleLogicalRangeChange(sync)
      made.forEach((sc) => sc.remove())
      subs.current = {}
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showRsi, showMacd])

  useEffect(() => {
    if (data.current.length) drawStudies()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studyKey])

  // ---------------------------------------------------------------- data
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    pending.current = null
    api.symbol(symbol, tf, TF_LIMIT[tf]).then((d) => {
      if (cancelled) return
      data.current = d.candles.map((k) => ({ time: toUnix(k.t), o: k.o, h: k.h, l: k.l, c: k.c, v: k.v }))
      lastSeen.current = toUnix(d.as_of) - 60
      setLoading(false)
      drawAll(true)
      props.current.onDetail?.(d)
    }).catch(() => {
      if (!cancelled) {
        setError(true)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, tf, reload])

  // Live: new minute bars extend the last candle; the animated price walks it to the close.
  useEffect(() => {
    const commit = () => {
      const p = pending.current
      if (!p) return
      const d = data.current
      const last = d[d.length - 1]
      if (last && last.time === p.target.time) Object.assign(last, p.target)
      pending.current = null
    }
    const offBars = liveStore.onBars((sym, bars) => {
      if (sym !== props.current.symbol || !main.current || loading) return
      const fresh = bars.filter((b) => b.time > lastSeen.current)
      if (!fresh.length) return
      if (fresh[0].time > lastSeen.current + 60) {
        setReload((x) => x + 1) // missed minutes (slept tab): refetch
        return
      }
      commit()
      const tfx = props.current.tf
      const d = data.current
      mergeBars(d, fresh.slice(0, -1), tfx)
      const lb = fresh[fresh.length - 1]
      const t = bucketOf(lb.time, tfx)
      let last = d[d.length - 1]
      if (!last || t > last.time) {
        last = { time: t, o: lb.o, h: lb.o, l: lb.o, c: lb.o, v: 0 }
        d.push(last)
      }
      const base = { ...last }
      const target = mergeBars([{ ...last }], [lb], tfx)[0]
      last.v = target.v
      pending.current = { base, target, hi: base.h, lo: base.l }
      lastSeen.current = fresh[fresh.length - 1].time
      main.current.update(toPoint(last) as never)
      drawStudies()
      if (d.length > 1 && d[d.length - 2].time !== last.time) writeLegend(last, d[d.length - 2])
    })
    const offPrice = liveStore.subscribe(symbol, () => {
      const p = pending.current
      const s = main.current
      const price = liveStore.get(symbol)
      if (!p || !s || price === undefined) return
      const d = data.current
      const last = d[d.length - 1]
      if (!last || last.time !== p.target.time) return
      p.hi = Math.max(p.hi, price)
      p.lo = Math.min(p.lo, price)
      last.h = Math.min(Math.max(p.base.h, p.hi), p.target.h)
      last.l = Math.max(Math.min(p.base.l, p.lo), p.target.l)
      last.c = price
      if (Math.abs(price - p.target.c) < 1e-9) commit()
      s.update(toPoint(last) as never)
      writeLegend(last, d[d.length - 2])
    })
    return () => {
      offBars()
      offPrice()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, loading])

  // ---------------------------------------------------------------- price lines (orders, alerts, position)
  const drawLines = () => {
    const s = main.current
    if (!s) return
    const want = new Map(props.current.lines.map((l) => [l.id, l]))
    for (const [id, pl] of priceLines.current) {
      if (!want.has(id)) {
        s.removePriceLine(pl)
        priceLines.current.delete(id)
      }
    }
    for (const l of want.values()) {
      const opts = { price: l.price, color: l.color, lineWidth: 1 as const, lineStyle: l.dashed ? LineStyle.Dashed : LineStyle.Solid, axisLabelVisible: true, title: l.title }
      const pl = priceLines.current.get(l.id)
      if (pl) pl.applyOptions(opts)
      else priceLines.current.set(l.id, s.createPriceLine(opts))
    }
  }
  const linesKey = lines.map((l) => `${l.id}:${l.price}:${l.title}:${l.color}`).join('|')
  useEffect(drawLines, [linesKey])

  // Drag a resting order or alert line to a new price.
  useEffect(() => {
    const el = mainBox.current
    if (!el) return
    let drag: { line: ChartLine; pl: IPriceLine; price: number } | null = null
    const near = (y: number) => {
      const s = main.current
      if (!s) return null
      let best: { line: ChartLine; d: number } | null = null
      for (const l of props.current.lines) {
        if (!l.drag) continue
        const ly = s.priceToCoordinate(l.price)
        if (ly === null) continue
        const d = Math.abs(ly - y)
        if (d <= 6 && (!best || d < best.d)) best = { line: l, d }
      }
      return best?.line ?? null
    }
    const yOf = (e: MouseEvent) => e.clientY - el.getBoundingClientRect().top
    const down = (e: MouseEvent) => {
      if (e.button !== 0) return
      const l = near(yOf(e))
      const pl = l && priceLines.current.get(l.id)
      if (!l || !pl) return
      e.preventDefault()
      e.stopPropagation()
      drag = { line: l, pl, price: l.price }
      chart.current?.applyOptions({ handleScroll: false, handleScale: false })
    }
    const move = (e: MouseEvent) => {
      if (drag) {
        const p = main.current?.coordinateToPrice(yOf(e))
        if (p !== null && p !== undefined) {
          drag.price = Math.round(Number(p) * 20) / 20
          drag.pl.applyOptions({ price: drag.price, title: `${drag.line.title} → ${fmtPrice(drag.price)}` })
        }
        return
      }
      el.style.cursor = near(yOf(e)) ? 'ns-resize' : props.current.tool !== 'none' ? 'crosshair' : ''
    }
    const up = () => {
      if (!drag) return
      const d = drag
      drag = null
      chart.current?.applyOptions({ handleScroll: true, handleScale: true })
      if (Math.abs(d.price - d.line.price) >= 0.01) props.current.onLineDrag?.(d.line, d.price)
      else d.pl.applyOptions({ price: d.line.price, title: d.line.title })
    }
    el.addEventListener('mousedown', down, true)
    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', up)
    return () => {
      el.removeEventListener('mousedown', down, true)
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mouseup', up)
    }
  }, [])

  const panes = (showRsi ? 1 : 0) + (showMacd ? 1 : 0)
  return (
    <div className={clsx('relative flex h-full w-full min-h-0 flex-col', className)}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <div className="relative min-h-0 flex-1">
        <div ref={mainBox} className="absolute inset-0" />
        {legend && (
          <div ref={legendRef}
            className={clsx('num pointer-events-none absolute left-2 top-1 z-[2] flex flex-wrap gap-x-2.5 text-2xs text-txt-mute [&_b]:font-medium [&_b]:text-txt-dim',
              !hover && 'opacity-90')} />
        )}
        {loading && <div className="absolute inset-0 grid place-items-center text-txt-mute"><Loader2 size={18} className="animate-spin" /></div>}
        {error && !loading && (
          <div className="absolute inset-0 grid place-items-center text-xs text-txt-mute">
            <div className="text-center">Chart data could not be loaded.<br />
              <button className="mt-2 text-info hover:underline" onClick={() => setReload((x) => x + 1)}>Try again</button>
            </div>
          </div>
        )}
      </div>
      {showRsi && (
        <div className={clsx('relative shrink-0 border-t border-line', panes > 1 ? 'h-[18%]' : 'h-[22%]')}>
          <span className="pointer-events-none absolute left-2 top-0.5 z-[2] text-2xs text-txt-mute">RSI 14</span>
          <div ref={rsiBox} className="absolute inset-0" />
        </div>
      )}
      {showMacd && (
        <div className={clsx('relative shrink-0 border-t border-line', panes > 1 ? 'h-[18%]' : 'h-[22%]')}>
          <span className="pointer-events-none absolute left-2 top-0.5 z-[2] text-2xs text-txt-mute">MACD 12 26 9</span>
          <div ref={macdBox} className="absolute inset-0" />
        </div>
      )}
    </div>
  )
}

