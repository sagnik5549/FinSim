import clsx from 'clsx'
import { Bell, CandlestickChart, Search, Wifi, WifiOff, X } from 'lucide-react'
import { memo, useMemo, useState } from 'react'
import { useGame, useGameState } from '../../game/GameContext'
import { money, pct } from '../../game/format'
import { useLiveNav } from '../../game/live'
import type { IndexRow, StockRow } from '../../types/game'
import { LiveChange, LiveNum } from '../market/Quote'

const INDEX_KEYS = ['BH50', 'DL30', 'BKX', 'BVIX']

function IndexCell({ idx }: { idx: IndexRow }) {
  const { openSymbol, symbol } = useGame()
  return (
    <button onClick={() => openSymbol(idx.key, 'stock')}
      className={clsx('min-w-0 rounded px-2 py-1.5 text-left hover:bg-ink-800', symbol === idx.key && 'bg-ink-800')}>
      <div className="truncate text-2xs text-txt-mute">{idx.name}</div>
      <div className="flex items-baseline justify-between gap-1">
        <LiveNum symbol={idx.key} value={idx.value} className="text-[13px] font-medium text-txt" flash={false} />
        <LiveChange symbol={idx.key} value={idx.value} prevClose={idx.prev_close} className="text-2xs" />
      </div>
    </button>
  )
}

const WatchRow = memo(function WatchRow({ x, active, held, alert, canSell }: {
  x: StockRow; active: boolean; held: boolean; alert: boolean; canSell: boolean
}) {
  const { openSymbol, setModal, openChart } = useGame()
  return (
    <li className={clsx('group relative flex h-11 cursor-pointer items-center gap-2 border-b border-line/60 px-3 hover:bg-ink-800', active && 'bg-ink-800')}
      onClick={() => openSymbol(x.symbol, 'stock')}>
      {active && <span className="absolute inset-y-0 left-0 w-0.5 bg-info" />}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-[13px] font-medium text-txt">{x.symbol}</span>
          {held && <span className="h-1.5 w-1.5 rounded-full bg-gold" title="In your portfolio" />}
          {alert && <Bell size={10} className="text-warn" />}
        </div>
        <div className="truncate text-2xs text-txt-mute">{x.name}</div>
      </div>
      <div className="text-right group-hover:invisible">
        <LiveNum symbol={x.symbol} value={x.price} className="block text-[13px] text-txt" />
        <LiveChange symbol={x.symbol} value={x.price} prevClose={x.prev_close} className="text-2xs" />
      </div>
      <div className="invisible absolute right-2 flex gap-1 group-hover:visible" onClick={(e) => e.stopPropagation()}>
        <button className="h-6 w-7 rounded bg-info text-xs font-semibold text-white hover:bg-info/90" title="Buy"
          onClick={() => setModal({ kind: 'trade', side: 'BUY', symbol: x.symbol })}>B</button>
        <button className="h-6 w-7 rounded bg-down text-xs font-semibold text-white hover:bg-down/90 disabled:opacity-30" title="Sell" disabled={!canSell}
          onClick={() => setModal({ kind: 'trade', side: 'SELL', symbol: x.symbol })}>S</button>
        <button className="grid h-6 w-7 place-items-center rounded border border-line bg-ink-850 text-txt-dim hover:text-txt" title="Large chart"
          onClick={() => openChart(x.symbol)}><CandlestickChart size={13} /></button>
      </div>
    </li>
  )
})

export function Watchlist({ onClose }: { onClose?: () => void }) {
  const s = useGameState()
  const { symbol } = useGame()
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<'default' | 'change' | 'symbol'>('default')
  const held = useMemo(() => new Set(s.holdings.map((h) => h.symbol)), [s.holdings])
  const alerts = useMemo(() => new Set(s.alerts.filter((a) => a.status === 'ACTIVE').map((a) => a.symbol)), [s.alerts])
  const rows = useMemo(() => {
    const t = q.trim().toLowerCase()
    const list = s.stocks.filter((x) => !t || x.symbol.toLowerCase().includes(t) || x.name.toLowerCase().includes(t) || x.sector.toLowerCase().includes(t))
    if (sort === 'change') list.sort((a, b) => b.change_pct - a.change_pct)
    if (sort === 'symbol') list.sort((a, b) => a.symbol.localeCompare(b.symbol))
    return list
  }, [s.stocks, q, sort])
  const idx = s.indices.filter((i) => INDEX_KEYS.includes(i.key))
  return (
    <aside className="flex h-full w-[300px] shrink-0 flex-col border-r border-line bg-ink-900">
      <div className="grid grid-cols-2 gap-0.5 border-b border-line p-1">
        {idx.map((i) => <IndexCell key={i.key} idx={i} />)}
      </div>
      <div className="flex items-center gap-1 border-b border-line px-2 py-1.5">
        <div className="relative flex-1">
          <Search size={13} className="absolute left-2.5 top-2.5 text-txt-mute" />
          <input className="input h-8 pl-7 text-xs" placeholder="Search symbol or sector" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <select className="h-8 rounded border border-line bg-ink-900 px-1.5 text-2xs text-txt-dim" value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} aria-label="Sort">
          <option value="default">Default</option>
          <option value="change">% change</option>
          <option value="symbol">A–Z</option>
        </select>
        {onClose && <button className="icon-btn !h-8 !w-7" onClick={onClose} aria-label="Hide watchlist"><X size={14} /></button>}
      </div>
      <div className="flex items-center justify-between px-3 py-1 text-2xs text-txt-mute">
        <span>Watchlist · {rows.length} stocks</span>
        <span>{s.stocks.filter((x) => x.change_pct > 0).length} up · {s.stocks.filter((x) => x.change_pct < 0).length} down</span>
      </div>
      <ul className="min-h-0 flex-1 overflow-y-auto">
        {rows.map((x) => (
          <WatchRow key={x.symbol} x={x} active={symbol === x.symbol} held={held.has(x.symbol)} alert={alerts.has(x.symbol)} canSell={held.has(x.symbol)} />
        ))}
        {rows.length === 0 && <li className="p-4 text-center text-xs text-txt-mute">No match.</li>}
      </ul>
    </aside>
  )
}

export function StatusBar() {
  const s = useGameState()
  const { connected } = useGame()
  const nav = useLiveNav(s)
  const p = s.portfolio
  const day = nav - (p.value - p.day_pnl)
  const ret = nav / p.starting_capital - 1
  const riskTone = { LOW: 'text-up', MEDIUM: 'text-txt-dim', HIGH: 'text-warn', CRITICAL: 'text-down' }[s.risk.level]
  return (
    <footer className="flex h-7 shrink-0 items-center gap-4 overflow-x-auto whitespace-nowrap border-t border-line bg-ink-900 px-3 text-2xs text-txt-mute [scrollbar-width:none]">
      <span className={clsx('flex items-center gap-1', connected ? 'text-txt-mute' : 'text-down')}>
        {connected ? <Wifi size={12} /> : <WifiOff size={12} />}{connected ? 'Live' : 'Reconnecting…'}
      </span>
      <span>Day {Math.min(s.clock.quarter_day, s.clock.quarter_days)} of {s.clock.quarter_days} · Q{s.clock.quarter} · Year {s.clock.career_year}</span>
      <span>Speed {s.live.speed}x</span>
      <span className="ml-auto">Portfolio <span className="num text-txt">{money(nav)}</span> <span className={clsx('num', ret >= 0 ? 'text-up' : 'text-down')}>{pct(ret)}</span></span>
      <span>Today <span className={clsx('num', day >= 0 ? 'text-up' : 'text-down')}>{money(day, { signed: true })}</span></span>
      <span>Cash <span className="num text-txt">{money(p.cash)}</span></span>
      <span>Drawdown <span className={clsx('num', p.drawdown > s.career.max_drawdown_limit * 0.7 ? 'text-down' : 'text-txt')}>{pct(p.drawdown, 2, false)}</span></span>
      <span>Risk <span className={riskTone}>{s.risk.level.toLowerCase()}</span></span>
      <span>Target <span className="num text-txt">{money(p.target_value)}</span></span>
    </footer>
  )
}
