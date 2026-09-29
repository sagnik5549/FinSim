import clsx from 'clsx'
import { AlertTriangle, CalendarDays, Clock3, Gavel, Mail, Newspaper, Zap } from 'lucide-react'
import { useState } from 'react'
import { samplePath, useGame, useGameState, useLiveProgress } from '../../game/GameContext'
import { gameTime, hhmm, int, money, pct, price, shortDate, toneClass } from '../../game/format'
import { api } from '../../services/api'
import type { CalendarItem, NewsItem } from '../../types/game'
import { Avatar } from '../common/Avatar'
import { Badge, Bar, Button, Change, Empty, LivePrice, Panel, Ring } from '../common/ui'

/** Portfolio value that moves with the live intra-hour tick replay. */
export function useLiveNav(): number {
  const s = useGameState()
  const { replay, progress } = useLiveProgress()
  if (!replay || progress >= 1) return s.portfolio.value
  let v = s.portfolio.cash
  for (const h of s.holdings) v += h.qty * (samplePath(replay.paths[h.symbol], progress) ?? h.price)
  return v
}

export function PortfolioCard() {
  const s = useGameState()
  const p = s.portfolio
  const navLive = useLiveNav()
  const ret = navLive / p.starting_capital - 1
  const progress = (navLive - p.starting_capital) / Math.max(1, p.target_value - p.starting_capital)
  const ddLimit = s.career.max_drawdown_limit
  const ringColor = progress >= 1 ? '#E9B949' : progress >= 0 ? '#4C8DFF' : '#F2495C'
  return (
    <Panel title="Portfolio" right={<Badge tone={s.risk.level === 'LOW' ? 'up' : s.risk.level === 'MEDIUM' ? 'info' : s.risk.level === 'HIGH' ? 'warn' : 'down'}>Risk {s.risk.level}</Badge>}>
      <div className="flex items-center gap-4 p-3">
        <Ring value={Math.max(0, progress)} color={ringColor} size={92}>
          <span className="num text-lg font-bold leading-none">{Math.round(progress * 100)}%</span>
          <span className="mt-1 text-[9px] font-semibold uppercase tracking-wider text-txt-mute">to target</span>
        </Ring>
        <div className="min-w-0 flex-1">
          <div className="label">Current value</div>
          <div className="num text-[26px] font-bold leading-tight text-txt">{money(navLive)}</div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs">
            <span className={clsx('num font-semibold', toneClass(ret))}>{money(navLive - p.starting_capital, { signed: true })}</span>
            <span className={clsx('num font-semibold', toneClass(ret))}>{pct(ret)}</span>
          </div>
          <div className="mt-1 text-2xs text-txt-mute">
            Target <span className="num text-gold">{money(p.target_value)}</span> · start {money(p.starting_capital)}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 border-t border-line px-3 py-2.5">
        <div>
          <div className="flex justify-between"><span className="label">Today</span><span className={clsx('num text-xs font-semibold', toneClass(p.day_pnl))}>{money(p.day_pnl, { signed: true })}</span></div>
          <div className="flex justify-between"><span className="label">Realised</span><span className={clsx('num text-xs', toneClass(p.realized_pnl))}>{money(p.realized_pnl, { signed: true })}</span></div>
        </div>
        <div>
          <div className="flex justify-between"><span className="label">Cash</span><span className="num text-xs">{money(p.cash)}</span></div>
          <div className="flex justify-between"><span className="label">Invested</span><span className="num text-xs">{pct(p.invested / Math.max(1, p.value), 0, false)}</span></div>
        </div>
        <div className="col-span-2">
          <div className="flex items-center justify-between">
            <span className="label">Drawdown</span>
            <span className={clsx('num text-2xs', p.drawdown > ddLimit * 0.7 ? 'text-down' : 'text-txt-dim')}>
              {pct(p.drawdown, 2, false)} now · max {pct(p.max_drawdown, 2, false)} / limit {pct(ddLimit, 0, false)}
            </span>
          </div>
          <Bar value={p.drawdown} max={ddLimit * 1.5} tone={p.drawdown > ddLimit ? 'down' : p.drawdown > ddLimit * 0.7 ? 'warn' : 'up'} marker={ddLimit} className="mt-1" />
        </div>
      </div>
    </Panel>
  )
}

export function HoldingsTable({ compact = false }: { compact?: boolean }) {
  const s = useGameState()
  const { openSymbol, setModal } = useGame()
  if (s.holdings.length === 0)
    return <Empty>100% cash. Open <b className="mx-1 text-txt">Markets</b> or press <b className="mx-1 text-up">BUY STOCK</b> to deploy capital.</Empty>
  return (
    <table className="w-full text-xs">
      <thead className="table-head">
        <tr>
          <th>Stock</th>
          <th className="!text-right">Qty</th>
          {!compact && <th className="!text-right">Avg</th>}
          <th className="!text-right">Price</th>
          <th className="!text-right">Value</th>
          <th className="!text-right">Wt</th>
          <th className="!text-right">Day</th>
          <th className="!text-right">P&L</th>
          {!compact && <th />}
        </tr>
      </thead>
      <tbody>
        {s.holdings.map((h) => (
          <tr key={h.symbol} className="table-row cursor-pointer" onClick={() => openSymbol(h.symbol)}>
            <td>
              <div className="font-bold text-txt">{h.symbol}</div>
              {!compact && <div className="text-2xs text-txt-mute">{h.name}</div>}
            </td>
            <td className="num text-right">{int(h.qty)}</td>
            {!compact && <td className="num text-right text-txt-dim">{price(h.avg_cost)}</td>}
            <td className="text-right"><LivePrice symbol={h.symbol} value={h.price} /></td>
            <td className="num text-right">{money(h.value)}</td>
            <td className={clsx('num text-right', h.weight > s.risk.limits.max_single_stock ? 'font-bold text-down' : 'text-txt-dim')}>{pct(h.weight, 1, false)}</td>
            <td className="text-right"><Change value={h.day_change_pct} /></td>
            <td className={clsx('num text-right font-semibold', toneClass(h.pnl))}>
              {money(h.pnl, { signed: true })}
              <div className="text-2xs font-normal">{pct(h.pnl_pct)}</div>
            </td>
            {!compact && (
              <td className="text-right">
                <Button size="sm" variant="sell" onClick={() => setModal({ kind: 'trade', side: 'SELL', symbol: h.symbol })}
                  disabled={s.clock.market_status !== 'OPEN'}>Sell</Button>
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const CAT_TONE: Record<string, 'info' | 'violet' | 'gold' | 'neutral'> = { COMPANY: 'info', MACRO: 'violet', MARKET: 'gold', FIRM: 'neutral' }

export function NewsList({ items, onPick }: { items: NewsItem[]; onPick?: (n: NewsItem) => void }) {
  const s = useGameState()
  const held = new Set(s.holdings.map((h) => h.symbol))
  if (items.length === 0) return <Empty>No news yet.</Empty>
  return (
    <ul>
      {items.map((n) => {
        const mine = n.symbols.some((x) => held.has(x))
        return (
          <li key={n.id} onClick={() => onPick?.(n)}
            className={clsx('cursor-pointer border-b border-line/60 px-3 py-2 transition hover:bg-ink-800', mine && 'bg-gold/[0.04]')}>
            <div className="flex items-center gap-2">
              <span className={clsx('h-1.5 w-1.5 shrink-0 rounded-full', n.tone === 'POSITIVE' ? 'bg-up' : n.tone === 'NEGATIVE' ? 'bg-down' : 'bg-txt-mute')} />
              <Badge tone={CAT_TONE[n.category]}>{n.category}</Badge>
              {n.severity >= 3 && <Badge tone="down">Breaking</Badge>}
              {mine && <Badge tone="gold">Holding</Badge>}
              <span className="num ml-auto shrink-0 text-2xs text-txt-mute">{shortDate(n.time)} {hhmm(n.time)}</span>
            </div>
            <div className={clsx('mt-1 text-[12.5px] leading-snug', n.severity >= 3 ? 'font-semibold text-txt' : 'text-txt')}>{n.headline}</div>
          </li>
        )
      })}
    </ul>
  )
}

const SENDER_NAME: Record<string, string> = {}

export function MessagesList({ limit = 20 }: { limit?: number }) {
  const s = useGameState()
  const { run } = useGame()
  const [openId, setOpenId] = useState<string | null>(null)
  const team = Object.fromEntries(s.team.map((t) => [t.id, t]))
  if (s.messages.length === 0) return <Empty>Inbox empty.</Empty>
  return (
    <ul>
      {s.messages.slice(0, limit).map((m) => {
        const who = team[m.sender]
        const isOpen = openId === m.id
        return (
          <li key={m.id} className="border-b border-line/60">
            <button className="flex w-full items-start gap-2.5 px-3 py-2 text-left transition hover:bg-ink-800"
              onClick={() => {
                setOpenId(isOpen ? null : m.id)
                if (!m.read) run(() => api.markRead('messages', [m.id]), { quiet: true })
              }}>
              <Avatar id={m.sender} size={30} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={clsx('truncate text-xs', m.read ? 'text-txt-dim' : 'font-bold text-txt')}>{who?.name ?? SENDER_NAME[m.sender] ?? m.sender}</span>
                  {m.priority !== 'NORMAL' && <Badge tone={m.priority === 'CRITICAL' ? 'down' : 'warn'}>{m.priority}</Badge>}
                  <span className="num ml-auto shrink-0 text-2xs text-txt-mute">{hhmm(m.time)}</span>
                </div>
                <div className={clsx('truncate text-[12px]', m.read ? 'text-txt-mute' : 'text-txt')}>{m.subject}</div>
                {isOpen && (
                  <div className="mt-1.5 space-y-1 rounded border border-line bg-ink-900 p-2 text-xs leading-relaxed text-txt-dim">
                    {m.lines.map((l, i) => <p key={i}>{l}</p>)}
                  </div>
                )}
              </div>
              {!m.read && <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-info" />}
            </button>
          </li>
        )
      })}
    </ul>
  )
}

export function OpportunityCards() {
  const s = useGameState()
  const { run, setModal } = useGame()
  const open = s.opportunities.filter((o) => o.status === 'OPEN')
  if (open.length === 0) return null
  return (
    <div className="space-y-2">
      {open.map((o) => (
        <div key={o.id} className="relative overflow-hidden rounded-lg border border-gold/40 bg-gradient-to-br from-gold/10 to-transparent p-3">
          <div className="absolute inset-x-0 top-0 h-px overflow-hidden"><div className="h-px w-1/2 animate-sweep bg-gold" /></div>
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-gold" />
            <span className="text-2xs font-bold uppercase tracking-wider text-gold">Block deal</span>
            <span className="num ml-auto flex items-center gap-1 text-2xs font-bold text-warn"><Clock3 size={11} /> expires {hhmm(o.expires_at)} · {Math.round(o.minutes_left / 60)}h</span>
          </div>
          <div className="mt-1.5 text-[13px] font-semibold">{o.name} <span className="text-txt-mute">({o.symbol})</span></div>
          <div className="mt-0.5 text-2xs text-txt-dim">{int(o.qty)} shares from {o.seller} at <span className="num text-txt">{price(o.price)}</span> ·{' '}
            <span className={clsx('num font-semibold', o.effective_discount > 0 ? 'text-up' : 'text-down')}>{pct(o.effective_discount, 1, false)} {o.effective_discount > 0 ? 'below' : 'above'} market</span>
          </div>
          <div className="mt-2 flex gap-2">
            <Button size="sm" variant="gold" disabled={s.clock.market_status !== 'OPEN'} onClick={() => run(() => api.acceptDeal(o.id))}>Take block · {money(o.value)}</Button>
            <Button size="sm" onClick={() => setModal({ kind: 'research', symbol: o.symbol })}>Research first</Button>
            <Button size="sm" variant="subtle" onClick={() => run(() => api.declineDeal(o.id))}>Pass</Button>
          </div>
        </div>
      ))}
    </div>
  )
}

const KIND_ICON: Record<string, JSX.Element> = {
  EARNINGS: <Newspaper size={12} className="text-info" />,
  ECON_DATA: <CalendarDays size={12} className="text-violet" />,
  POLICY: <Gavel size={12} className="text-warn" />,
  CEO_MEETING: <Mail size={12} className="text-gold" />,
}

export function CalendarList({ items, limit = 6 }: { items: CalendarItem[]; limit?: number }) {
  const s = useGameState()
  if (items.length === 0) return <Empty>Nothing scheduled in the next three weeks.</Empty>
  const today = s.clock.game_date
  return (
    <ul>
      {items.slice(0, limit).map((c) => {
        const isToday = c.time.slice(0, 10) === today
        return (
          <li key={c.id} className="flex items-center gap-2.5 border-b border-line/60 px-3 py-1.5">
            {KIND_ICON[c.kind]}
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs text-txt">{c.title}</div>
              {c.consensus !== undefined && (
                <div className="text-2xs text-txt-mute">consensus <span className="num text-txt-dim">{Number(c.consensus).toFixed(1)}%</span> · our economist <span className="num text-violet">{Number(c.desk_forecast).toFixed(2)}%</span></div>
              )}
            </div>
            <span className={clsx('num shrink-0 text-2xs', isToday ? 'font-bold text-warn' : 'text-txt-mute')}>
              {isToday ? `TODAY ${hhmm(c.time)}` : `${shortDate(c.time)} ${hhmm(c.time)}`}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

export function RiskAlertsInline() {
  const s = useGameState()
  const items = [...s.risk.breaches.map((b) => ({ ...b, hard: true })), ...s.risk.near_limits.map((b) => ({ ...b, hard: false }))]
  if (items.length === 0) return null
  return (
    <div className="space-y-1 px-3 py-2">
      {items.slice(0, 3).map((b, i) => (
        <div key={i} className={clsx('flex items-center gap-2 rounded border px-2 py-1 text-2xs', b.hard ? 'border-down/40 bg-down-soft text-down' : 'border-warn/30 bg-warn-soft text-warn')}>
          <AlertTriangle size={12} />
          <span className="font-semibold">{b.rule.replace('_', ' ')} · {b.subject}</span>
          <span className="num ml-auto">{pct(b.value, 1, false)} / {pct(b.limit, 0, false)}{b.excepted ? ' · exception' : ''}</span>
        </div>
      ))}
    </div>
  )
}

export function TimeHint() {
  const s = useGameState()
  const next = s.calendar.find((c) => c.time.slice(0, 10) === s.clock.game_date)
  if (!next || s.clock.market_status !== 'OPEN') return null
  const hrs = Number(next.time.slice(11, 13)) - s.clock.game_hour
  if (hrs < 0) return null
  return (
    <div className="flex items-center gap-2 rounded-md border border-warn/30 bg-warn-soft px-2.5 py-1 text-2xs text-warn">
      <Clock3 size={12} />
      <span className="font-semibold">{next.title}</span>
      <span className="num">in {hrs}h ({hhmm(next.time)})</span>
    </div>
  )
}

export { gameTime }
