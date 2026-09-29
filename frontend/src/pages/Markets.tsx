import clsx from 'clsx'
import { ArrowDown, ArrowUp, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Badge, Button, Change, LivePrice, Panel, Sparkline } from '../components/common/ui'
import { useGame, useGameState } from '../game/GameContext'
import { compactVol, num } from '../game/format'
import type { StockRow } from '../types/game'

type Key = 'name' | 'sector' | 'price' | 'change_pct' | 'volume' | 'volatility' | 'momentum' | 'pe' | 'sentiment' | 'risk' | 'market_cap_cr'

const COLS: { key: Key; label: string; right?: boolean }[] = [
  { key: 'name', label: 'Company' },
  { key: 'sector', label: 'Sector' },
  { key: 'price', label: 'Price', right: true },
  { key: 'change_pct', label: 'Change', right: true },
  { key: 'volume', label: 'Volume', right: true },
  { key: 'volatility', label: 'Volatility', right: true },
  { key: 'momentum', label: 'Momentum', right: true },
  { key: 'pe', label: 'Valuation (P/E)', right: true },
  { key: 'sentiment', label: 'Sentiment', right: true },
  { key: 'risk', label: 'Risk', right: true },
  { key: 'market_cap_cr', label: 'Mkt cap', right: true },
]

export function sentimentTone(label: string): 'up' | 'down' | 'neutral' | 'info' | 'warn' {
  return label === 'BULLISH' ? 'up' : label === 'POSITIVE' ? 'info' : label === 'BEARISH' ? 'down' : label === 'NEGATIVE' ? 'warn' : 'neutral'
}

export default function Markets() {
  const s = useGameState()
  const { openSymbol, setModal } = useGame()
  const [q, setQ] = useState('')
  const [sector, setSector] = useState<string | null>(null)
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: 'market_cap_cr', dir: -1 })
  const [heldOnly, setHeldOnly] = useState(false)
  const sectors = useMemo(() => [...new Set(s.stocks.map((x) => x.sector))].sort(), [s.stocks])
  const rows = useMemo(() => {
    const term = q.trim().toLowerCase()
    return s.stocks
      .filter((x) => (!sector || x.sector === sector) && (!heldOnly || x.held) &&
        (!term || x.name.toLowerCase().includes(term) || x.symbol.toLowerCase().includes(term)))
      .sort((a, b) => {
        const av = a[sort.key] as number | string | null
        const bv = b[sort.key] as number | string | null
        if (typeof av === 'string' && typeof bv === 'string') return av.localeCompare(bv) * sort.dir
        return (((av as number) ?? 0) - ((bv as number) ?? 0)) * sort.dir
      })
  }, [s.stocks, q, sector, sort, heldOnly])
  const breadth = s.stocks.filter((x) => x.change_pct > 0).length

  return (
    <div className="flex h-full min-h-0 flex-col gap-2.5 p-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-72">
          <Search size={14} className="absolute left-3 top-2.5 text-txt-mute" />
          <input className="input pl-8" placeholder="Search company or symbol" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <button className={clsx('chip', !sector && 'chip-on')} onClick={() => setSector(null)}>All sectors</button>
        {sectors.map((x) => <button key={x} className={clsx('chip', sector === x && 'chip-on')} onClick={() => setSector(sector === x ? null : x)}>{x}</button>)}
        <button className={clsx('chip', heldOnly && 'chip-on')} onClick={() => setHeldOnly(!heldOnly)}>Holdings only</button>
        <div className="ml-auto text-2xs text-txt-mute">
          Breadth <span className="num font-bold text-up">{breadth}</span> up / <span className="num font-bold text-down">{s.stocks.length - breadth}</span> down
        </div>
      </div>
      <Panel title="Stock screener · Dalal Street Exchange (simulated)" className="min-h-0 flex-1" bodyClass="overflow-auto"
        right={<span className="text-2xs text-txt-mute">{rows.length} of {s.stocks.length}</span>}>
        <table className="w-full text-xs">
          <thead className="table-head">
            <tr>
              {COLS.map((c) => (
                <th key={c.key} className={clsx('cursor-pointer select-none hover:text-txt', c.right && '!text-right')}
                  onClick={() => setSort((p) => ({ key: c.key, dir: p.key === c.key ? (p.dir === 1 ? -1 : 1) : -1 }))}>
                  <span className="inline-flex items-center gap-1">{c.label}{sort.key === c.key && (sort.dir === 1 ? <ArrowUp size={10} /> : <ArrowDown size={10} />)}</span>
                </th>
              ))}
              <th className="!text-right">Trend</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => <Row key={x.symbol} x={x} onOpen={() => openSymbol(x.symbol, 'stock')}
              onBuy={() => setModal({ kind: 'trade', side: 'BUY', symbol: x.symbol })} canTrade={s.clock.market_status === 'OPEN'} />)}
          </tbody>
        </table>
      </Panel>
    </div>
  )
}

function Row({ x, onOpen, onBuy, canTrade }: { x: StockRow; onOpen: () => void; onBuy: () => void; canTrade: boolean }) {
  return (
    <tr className="table-row cursor-pointer" onClick={onOpen}>
      <td>
        <div className="flex items-center gap-2">
          <span className="w-12 font-bold text-txt">{x.symbol}</span>
          <span className="truncate text-txt-dim">{x.name}</span>
          {x.held && <Badge tone="gold">Held</Badge>}
        </div>
      </td>
      <td className="text-txt-dim">{x.sector}</td>
      <td className="text-right"><LivePrice symbol={x.symbol} value={x.price} /></td>
      <td className="text-right"><Change value={x.change_pct} /></td>
      <td className="num text-right text-txt-dim" title={x.volume ? 'Today' : 'Previous session'}>{x.volume ? compactVol(x.volume) : <span className="italic text-txt-mute">{compactVol(x.prev_volume)}</span>}</td>
      <td className="num text-right">{(x.volatility * 100).toFixed(2)}%</td>
      <td className={clsx('num text-right', x.momentum > 0.2 ? 'text-up' : x.momentum < -0.2 ? 'text-down' : 'text-txt-dim')}>{x.momentum > 0 ? '+' : ''}{num(x.momentum, 2)}</td>
      <td className={clsx('num text-right', x.valuation > 0.7 ? 'text-warn' : x.valuation < 0.35 ? 'text-up' : 'text-txt')}>{x.pe ? `${x.pe.toFixed(1)}×` : '—'}</td>
      <td className="text-right"><Badge tone={sentimentTone(x.sentiment_label)}>{x.sentiment_label}</Badge></td>
      <td className="text-right">
        <div className="ml-auto flex w-16 items-center gap-1.5">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-700">
            <div className={clsx('h-full', x.risk > 65 ? 'bg-down' : x.risk > 45 ? 'bg-warn' : 'bg-up')} style={{ width: `${Math.min(100, x.risk)}%` }} />
          </div>
          <span className="num w-5 text-2xs text-txt-dim">{Math.round(x.risk)}</span>
        </div>
      </td>
      <td className="num text-right text-txt-dim">₹{num(x.market_cap_cr / 1000, 1)}K Cr</td>
      <td className="text-right"><Sparkline data={x.spark} width={70} height={22} className="ml-auto" /></td>
      <td className="text-right" onClick={(e) => e.stopPropagation()}>
        <Button size="sm" variant="buy" disabled={!canTrade} onClick={onBuy}>Buy</Button>
      </td>
    </tr>
  )
}
