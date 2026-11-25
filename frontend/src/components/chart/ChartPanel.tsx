import clsx from 'clsx'
import { BarChart2, Bell, CandlestickChart, ChevronDown, LineChart, Maximize2, MousePointer2, Spline, TrendingDown, TrendingUp } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useGame, useGameState } from '../../game/GameContext'
import { price as fmtPrice } from '../../game/format'
import { liveStore } from '../../game/live'
import { color } from '../../game/theme'
import { api } from '../../services/api'
import type { SymbolDetail, Timeframe } from '../../types/game'
import { TradingChart, type ChartLine, type ChartType, type Study, type Tool } from './TradingChart'

export const TIMEFRAMES: { value: Timeframe; label: string }[] = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1H' },
  { value: '1d', label: '1D' },
]

const TYPES: { value: ChartType; label: string; icon: ReactNode }[] = [
  { value: 'candles', label: 'Candles', icon: <CandlestickChart size={14} /> },
  { value: 'bars', label: 'OHLC bars', icon: <BarChart2 size={14} /> },
  { value: 'line', label: 'Line', icon: <LineChart size={14} /> },
  { value: 'area', label: 'Area', icon: <Spline size={14} /> },
]

const STUDIES: { value: Study; label: string }[] = [
  { value: 'volume', label: 'Volume' },
  { value: 'sma20', label: 'SMA 20' },
  { value: 'sma50', label: 'SMA 50' },
  { value: 'ema20', label: 'EMA 20' },
  { value: 'bb', label: 'Bollinger Bands (20, 2)' },
  { value: 'vwap', label: 'VWAP (intraday)' },
  { value: 'rsi', label: 'RSI 14' },
  { value: 'macd', label: 'MACD (12, 26, 9)' },
]

interface Prefs {
  tf: Timeframe
  type: ChartType
  studies: Study[]
}

function loadPrefs(key: string, fallback: Prefs): Prefs {
  try {
    const raw = localStorage.getItem(`ibm.chart.${key}`)
    return raw ? { ...fallback, ...JSON.parse(raw) } : fallback
  } catch {
    return fallback
  }
}

function savePrefs(key: string, p: Prefs) {
  try {
    localStorage.setItem(`ibm.chart.${key}`, JSON.stringify(p))
  } catch {
    /* ignore */
  }
}

export function useOutside(ref: React.RefObject<HTMLElement>, onOut: () => void) {
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && onOut()
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [ref, onOut])
}

function Dropdown({ label, children, title }: { label: ReactNode; children: (close: () => void) => ReactNode; title?: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useOutside(ref, () => setOpen(false))
  return (
    <div className="relative" ref={ref}>
      <button title={title} onClick={() => setOpen(!open)}
        className={clsx('flex h-7 items-center gap-1 rounded px-2 text-xs text-txt-dim hover:bg-ink-750 hover:text-txt', open && 'bg-ink-750 text-txt')}>
        {label}<ChevronDown size={12} className="opacity-60" />
      </button>
      {open && <div className="menu absolute left-0 top-8">{children(() => setOpen(false))}</div>}
    </div>
  )
}

/** Lines drawn on a stock's chart: resting orders, alerts and the position's average cost. */
export function useChartLines(symbol: string): ChartLine[] {
  const s = useGameState()
  return useMemo(() => {
    const out: ChartLine[] = []
    for (const o of s.orders) {
      if (o.symbol !== symbol || (o.status !== 'OPEN' && o.status !== 'TRIGGERED')) continue
      const tone = o.side === 'BUY' ? color('info') : color('down')
      const label = o.tag === 'TARGET' ? 'TGT' : o.tag === 'STOPLOSS' ? 'SL' : o.type === 'LIMIT' ? 'LMT' : o.type
      if (o.price !== null && (o.type === 'LIMIT' || o.type === 'SL'))
        out.push({ id: `${o.id}:p`, price: o.price, color: tone, title: `${o.side} ${label} ${o.qty}`, drag: { kind: 'order', field: 'price' } })
      if (o.trigger !== null && (o.type === 'SL' || o.type === 'SL-M'))
        out.push({ id: `${o.id}:t`, price: o.trigger, color: tone, dashed: true, title: `${o.side} ${label} trg ${o.qty}`, drag: { kind: 'order', field: 'trigger' } })
    }
    for (const a of s.alerts) {
      if (a.symbol === symbol && a.status === 'ACTIVE')
        out.push({ id: a.id, price: a.price, color: color('warn'), dashed: true, title: `Alert ${a.op === 'ABOVE' ? '▲' : '▼'}`, drag: { kind: 'alert', field: 'price' } })
    }
    const h = s.holdings.find((x) => x.symbol === symbol)
    if (h) out.push({ id: 'avg', price: h.avg_cost, color: color('txt-mute'), dashed: true, title: `Avg ${h.qty.toLocaleString('en-IN')}` })
    return out
  }, [s.orders, s.alerts, s.holdings, symbol])
}

export function ChartPanel({
  symbol, prefsKey = 'main', defaultTf = '5m', defaultStudies = ['volume'], large = false, right, onDetail, expandable = true,
}: {
  symbol: string
  prefsKey?: string
  defaultTf?: Timeframe
  defaultStudies?: Study[]
  large?: boolean
  right?: ReactNode
  onDetail?: (d: SymbolDetail) => void
  expandable?: boolean
}) {
  const s = useGameState()
  const { run, setModal, openChart, toast } = useGame()
  const [prefs, setPrefs] = useState<Prefs>(() => loadPrefs(prefsKey, { tf: defaultTf, type: 'candles', studies: defaultStudies }))
  const [tool, setTool] = useState<Tool>('none')
  const isStock = s.stocks.some((x) => x.symbol === symbol)
  const lines = useChartLines(symbol)
  const update = (p: Partial<Prefs>) =>
    setPrefs((cur) => {
      const next = { ...cur, ...p }
      savePrefs(prefsKey, next)
      return next
    })
  const toggleStudy = (st: Study) =>
    update({ studies: prefs.studies.includes(st) ? prefs.studies.filter((x) => x !== st) : [...prefs.studies, st] })

  useEffect(() => {
    if (tool === 'none') return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setTool('none')
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [tool])

  const onPick = (p: number, t: Tool) => {
    setTool('none')
    const ltp = liveStore.get(symbol) ?? s.stocks.find((x) => x.symbol === symbol)?.price ?? p
    if (t === 'alert') {
      run(() => api.addAlert(symbol, p), { quiet: false }).then((r) => r && toast({ kind: 'success', title: 'Alert set', body: `${symbol} ${p > ltp ? 'above' : 'below'} ${fmtPrice(p)}` }))
      return
    }
    const side = t === 'buy' ? 'BUY' : 'SELL'
    // Buying below the market / selling above it rests as a limit; the other way round is a stop.
    const limit = side === 'BUY' ? p <= ltp : p >= ltp
    setModal({ kind: 'trade', side, symbol, type: limit ? 'LIMIT' : 'SL-M', price: limit ? p : undefined, trigger: limit ? undefined : p })
  }

  const onLineDrag = async (l: ChartLine, p: number) => {
    if (!l.drag) return
    if (l.drag.kind === 'alert') {
      await run(() => api.cancelAlert(l.id), { quiet: true })
      await run(() => api.addAlert(symbol, p))
      return
    }
    const id = l.id.split(':')[0]
    await run(() => api.modifyOrder(id, l.drag!.field === 'price' ? { price: p } : { trigger: p }))
  }

  const tf = prefs.tf
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-9 shrink-0 items-center gap-0.5 border-b border-line px-1.5">
        <div className="flex items-center">
          {TIMEFRAMES.map((x) => (
            <button key={x.value} onClick={() => update({ tf: x.value })}
              className={clsx('h-7 rounded px-2 text-xs font-medium', tf === x.value ? 'bg-ink-700 text-txt' : 'text-txt-mute hover:text-txt')}>
              {x.label}
            </button>
          ))}
        </div>
        <span className="mx-1 h-4 w-px bg-line" />
        <Dropdown title="Chart type" label={TYPES.find((x) => x.value === prefs.type)?.icon}>
          {(close) => TYPES.map((x) => (
            <button key={x.value} className={clsx('menu-item', prefs.type === x.value && 'text-txt')} onClick={() => { update({ type: x.value }); close() }}>
              {x.icon}{x.label}
            </button>
          ))}
        </Dropdown>
        <Dropdown title="Indicators" label={<span>Indicators{prefs.studies.length ? <span className="ml-1 text-txt-mute">{prefs.studies.length}</span> : null}</span>}>
          {() => STUDIES.map((x) => (
            <label key={x.value} className="menu-item cursor-pointer">
              <input type="checkbox" className="accent-[rgb(var(--info))]" checked={prefs.studies.includes(x.value)} onChange={() => toggleStudy(x.value)} />
              {x.label}
            </label>
          ))}
        </Dropdown>
        {isStock && (
          <>
            <span className="mx-1 h-4 w-px bg-line" />
            <ToolButton active={tool === 'none'} onClick={() => setTool('none')} title="Pointer"><MousePointer2 size={14} /></ToolButton>
            <ToolButton active={tool === 'buy'} onClick={() => setTool(tool === 'buy' ? 'none' : 'buy')} title="Mark a buy level: click the chart to set a buy limit (below the price) or a buy stop (above)">
              <TrendingUp size={14} className="text-info" /><span className="hidden text-xs xl:inline">Buy at</span>
            </ToolButton>
            <ToolButton active={tool === 'sell'} onClick={() => setTool(tool === 'sell' ? 'none' : 'sell')} title="Mark a sell level: click the chart to set a target (above the price) or a stop-loss (below)">
              <TrendingDown size={14} className="text-down" /><span className="hidden text-xs xl:inline">Sell at</span>
            </ToolButton>
            <ToolButton active={tool === 'alert'} onClick={() => setTool(tool === 'alert' ? 'none' : 'alert')} title="Click the chart to set a price alert">
              <Bell size={14} className="text-warn" /><span className="hidden text-xs xl:inline">Alert</span>
            </ToolButton>
          </>
        )}
        <div className="ml-auto flex items-center gap-1">
          {right}
          {expandable && (
            <button className="icon-btn !h-7 !w-7" title="Open large chart" onClick={() => openChart(symbol)}><Maximize2 size={14} /></button>
          )}
        </div>
      </div>
      {tool !== 'none' && (
        <div className="shrink-0 border-b border-line bg-ink-800 px-3 py-1 text-2xs text-txt-dim">
          {tool === 'alert' ? 'Click the chart at the price you want to be alerted at.'
            : tool === 'buy' ? 'Click where you want to buy. Below the price places a buy limit; above it places a buy stop.'
              : 'Click where you want to sell. Above the price places a sell limit (target); below it places a stop-loss.'}
          <span className="ml-2 text-txt-mute">Esc to cancel · drag an order or alert line to move it</span>
        </div>
      )}
      <div className="min-h-0 flex-1">
        <TradingChart symbol={symbol} tf={tf} type={prefs.type} studies={prefs.studies} lines={lines} tool={tool}
          onPick={onPick} onLineDrag={onLineDrag} onDetail={onDetail} watermark={large} />
      </div>
    </div>
  )
}

function ToolButton({ active, onClick, title, children }: { active: boolean; onClick: () => void; title: string; children: ReactNode }) {
  return (
    <button title={title} onClick={onClick}
      className={clsx('flex h-7 items-center gap-1 rounded px-1.5 text-txt-dim hover:bg-ink-750 hover:text-txt', active && 'bg-ink-700 text-txt')}>
      {children}
    </button>
  )
}
