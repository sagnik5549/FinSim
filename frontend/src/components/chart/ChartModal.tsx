import clsx from 'clsx'
import { Bell, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useGame, useGameState } from '../../game/GameContext'
import { compactVol, int, num, pct } from '../../game/format'
import { api } from '../../services/api'
import type { SymbolDetail } from '../../types/game'
import { LiveChange, LiveNum, MarketDepth } from '../market/Quote'
import { ChartPanel } from './ChartPanel'

/** Large chart in a full-window overlay, with depth, the symbol's orders and alerts beside it. */
export function ChartModal({ symbol: initial }: { symbol: string }) {
  const s = useGameState()
  const { openChart, setModal, run } = useGame()
  const [symbol, setSymbol] = useState(initial)
  const [detail, setDetail] = useState<SymbolDetail | null>(null)
  const stock = s.stocks.find((x) => x.symbol === symbol)
  const idx = s.indices.find((x) => x.key === symbol)
  const value = stock?.price ?? idx?.value ?? 0
  const prev = stock?.prev_close ?? idx?.prev_close ?? value
  const orders = s.orders.filter((o) => o.symbol === symbol && (o.status === 'OPEN' || o.status === 'TRIGGERED'))
  const alerts = s.alerts.filter((a) => a.symbol === symbol && a.status === 'ACTIVE')
  const pos = s.holdings.find((h) => h.symbol === symbol)

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      if (e.key === 'Escape' && tag !== 'INPUT') openChart(null)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [openChart])

  // Depth refreshes with each tick while the window is open.
  useEffect(() => {
    if (!stock) return
    let cancelled = false
    api.symbol(symbol, '1m', 20).then((d) => !cancelled && setDetail(d)).catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [symbol, s.version, stock])

  return (
    <div className="fixed inset-0 z-30 flex flex-col bg-ink-950 animate-fadeIn" role="dialog" aria-label={`${symbol} chart`}>
      <div className="flex h-12 shrink-0 items-center gap-4 border-b border-line bg-ink-900 px-3">
        <select className="h-8 rounded border border-line bg-ink-850 px-2 text-sm font-semibold" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
          <optgroup label="Stocks">{s.stocks.map((x) => <option key={x.symbol} value={x.symbol}>{x.symbol} · {x.name}</option>)}</optgroup>
          <optgroup label="Indices">{s.indices.map((x) => <option key={x.key} value={x.key}>{x.name}</option>)}</optgroup>
        </select>
        <div className="flex items-baseline gap-2">
          <LiveNum symbol={symbol} value={value} decimals={symbol === 'USDINR' ? 4 : 2} className="text-lg font-semibold" />
          <LiveChange symbol={symbol} value={value} prevClose={prev} abs className="text-sm" />
        </div>
        {stock && (
          <div className="hidden gap-4 text-xs text-txt-mute md:flex">
            <span>O <span className="num text-txt-dim">{num(stock.open)}</span></span>
            <span>H <span className="num text-txt-dim">{num(stock.day_high)}</span></span>
            <span>L <span className="num text-txt-dim">{num(stock.day_low)}</span></span>
            <span>Prev <span className="num text-txt-dim">{num(stock.prev_close)}</span></span>
            <span>Vol <span className="num text-txt-dim">{compactVol(stock.volume)}</span></span>
          </div>
        )}
        <div className="ml-auto flex items-center gap-2">
          {stock && (
            <>
              <button className="h-8 rounded bg-info px-4 text-sm font-semibold text-white hover:bg-info/90" onClick={() => setModal({ kind: 'trade', side: 'BUY', symbol })}>Buy</button>
              <button className="h-8 rounded bg-down px-4 text-sm font-semibold text-white hover:bg-down/90 disabled:opacity-40" disabled={!pos}
                onClick={() => setModal({ kind: 'trade', side: 'SELL', symbol })}>Sell</button>
            </>
          )}
          <button className="icon-btn" aria-label="Close chart" title="Close (Esc)" onClick={() => openChart(null)}><X size={18} /></button>
        </div>
      </div>
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <ChartPanel symbol={symbol} prefsKey="popout" defaultTf="5m" defaultStudies={['volume', 'vwap']} large expandable={false} />
        </div>
        {stock && (
          <aside className="hidden w-[320px] shrink-0 flex-col overflow-y-auto border-l border-line bg-ink-900 lg:flex">
            <Section title="Market depth">
              {detail?.depth ? <MarketDepth depth={detail.depth} /> : <div className="h-40" />}
            </Section>
            {pos && (
              <Section title="Position">
                <div className="grid grid-cols-2 gap-y-1 text-xs">
                  <span className="text-txt-mute">Quantity</span><span className="num text-right">{int(pos.qty)}</span>
                  <span className="text-txt-mute">Average</span><span className="num text-right">{num(pos.avg_cost)}</span>
                  <span className="text-txt-mute">P&L</span><span className={clsx('num text-right', pos.pnl >= 0 ? 'text-up' : 'text-down')}>{pct(pos.pnl_pct)}</span>
                </div>
              </Section>
            )}
            <Section title={`Open orders (${orders.length})`}>
              {orders.length === 0 && <p className="text-xs text-txt-mute">None. Use “Buy at” or “Sell at” on the chart to mark levels.</p>}
              {orders.map((o) => (
                <div key={o.id} className="flex items-center gap-2 border-b border-line/60 py-1.5 text-xs last:border-0">
                  <span className={o.side === 'BUY' ? 'text-info' : 'text-down'}>{o.side}</span>
                  <span className="text-txt-dim">{o.tag || o.type}</span>
                  <span className="num">{int(o.qty)}</span>
                  <span className="num ml-auto">{o.price ? num(o.price) : ''}{o.trigger ? ` trg ${num(o.trigger)}` : ''}</span>
                  <button className="text-txt-mute hover:text-down" aria-label="Cancel order" onClick={() => run(() => api.cancelOrder(o.id))}><X size={13} /></button>
                </div>
              ))}
            </Section>
            <Section title={`Alerts (${alerts.length})`}>
              {alerts.length === 0 && <p className="text-xs text-txt-mute">Pick the bell tool and click the chart to add one.</p>}
              {alerts.map((a) => (
                <div key={a.id} className="flex items-center gap-2 py-1 text-xs">
                  <Bell size={12} className="text-warn" />
                  <span className="text-txt-dim">{a.op === 'ABOVE' ? 'Crosses above' : 'Falls below'}</span>
                  <span className="num ml-auto">{num(a.price)}</span>
                  <button className="text-txt-mute hover:text-down" aria-label="Remove alert" onClick={() => run(() => api.cancelAlert(a.id))}><X size={13} /></button>
                </div>
              ))}
            </Section>
          </aside>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-line p-3">
      <h3 className="mb-2 text-xs font-medium text-txt-dim">{title}</h3>
      {children}
    </section>
  )
}
