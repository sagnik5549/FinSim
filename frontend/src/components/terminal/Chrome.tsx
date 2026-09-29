import clsx from 'clsx'
import {
  BarChart3, Briefcase, CalendarClock, CandlestickChart, ChevronsRight, Clock, FastForward, FileSearch, Gauge,
  LayoutDashboard, Newspaper, Palmtree, ShoppingCart, SkipForward, Sunrise, Trophy, Users, Wallet,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { useGame, useGameState, useLiveValue } from '../../game/GameContext'
import { num, pct, toneClass } from '../../game/format'
import { api } from '../../services/api'
import type { IndexRow, Page } from '../../types/game'
import { Bar, Sparkline } from '../common/ui'

const NAV: { page: Page; label: string; icon: ReactNode }[] = [
  { page: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
  { page: 'markets', label: 'Markets', icon: <CandlestickChart size={16} /> },
  { page: 'portfolio', label: 'Portfolio', icon: <Wallet size={16} /> },
  { page: 'research', label: 'Research', icon: <FileSearch size={16} /> },
  { page: 'trading', label: 'Trading', icon: <ShoppingCart size={16} /> },
  { page: 'news', label: 'News', icon: <Newspaper size={16} /> },
  { page: 'team', label: 'Team', icon: <Users size={16} /> },
  { page: 'career', label: 'Career', icon: <Trophy size={16} /> },
  { page: 'performance', label: 'Performance', icon: <BarChart3 size={16} /> },
]

export function Sidebar() {
  const { page, setPage, setModal } = useGame()
  const s = useGameState()
  const unreadMsgs = s.messages.filter((m) => !m.read).length
  const openDeals = s.opportunities.filter((o) => o.status === 'OPEN').length
  const riskTone = { LOW: 'up', MEDIUM: 'info', HIGH: 'warn', CRITICAL: 'down' }[s.risk.level] as 'up' | 'info' | 'warn' | 'down'
  return (
    <nav className="flex w-[196px] shrink-0 flex-col border-r border-line bg-ink-900/70">
      <ul className="flex-1 space-y-0.5 p-2">
        {NAV.map((n) => {
          const badge = n.page === 'team' ? unreadMsgs : n.page === 'trading' ? openDeals : 0
          return (
            <li key={n.page}>
              <button
                onClick={() => setPage(n.page)}
                className={clsx(
                  'group relative flex h-9 w-full items-center gap-3 rounded-md px-3 text-[13px] font-medium transition',
                  page === n.page ? 'bg-info-soft text-txt' : 'text-txt-dim hover:bg-ink-800 hover:text-txt',
                )}
              >
                {page === n.page && <span className="absolute left-0 top-1.5 h-6 w-[3px] rounded-r bg-info shadow-glowInfo" />}
                <span className={page === n.page ? 'text-info' : 'text-txt-mute group-hover:text-txt-dim'}>{n.icon}</span>
                {n.label}
                {badge > 0 && <span className="num ml-auto rounded-full bg-gold/90 px-1.5 text-[10px] font-bold text-ink-950">{badge}</span>}
              </button>
            </li>
          )
        })}
      </ul>
      <div className="space-y-2 border-t border-line p-3">
        <div className="rounded-md border border-line bg-ink-850 p-2.5">
          <div className="flex items-center justify-between">
            <span className="label">Risk</span>
            <span className={clsx('text-2xs font-bold', `text-${riskTone}`)}>{s.risk.level}</span>
          </div>
          <Bar value={s.risk.score} max={100} tone={riskTone} className="mt-1.5" />
          <div className="num mt-1 text-2xs text-txt-mute">score {s.risk.score.toFixed(0)} · DD {pct(s.portfolio.drawdown, 1, false)}</div>
        </div>
        <button onClick={() => setModal({ kind: 'leave' })}
          className="w-full rounded-md border border-line bg-ink-850 p-2.5 text-left transition hover:border-violet/50">
          <div className="flex items-center justify-between">
            <span className="label">Paid leave</span>
            <Palmtree size={13} className="text-violet" />
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="num text-lg font-bold text-txt">{s.leave.remaining}</span>
            <span className="text-2xs text-txt-mute">of {s.leave.allowance} days left</span>
          </div>
          <Bar value={s.leave.used} max={s.leave.allowance} tone="violet" className="mt-1" />
        </button>
      </div>
    </nav>
  )
}

function IndexCell({ idx }: { idx: IndexRow }) {
  const { openSymbol } = useGame()
  const v = useLiveValue(idx.key, idx.value)
  const chg = idx.prev_close ? v / idx.prev_close - 1 : 0
  const decimals = idx.key === 'USDINR' ? 4 : 2
  return (
    <button onClick={() => openSymbol(idx.key, 'dashboard')}
      className="flex min-w-[168px] flex-1 items-center justify-between gap-2 border-r border-line px-3 py-1.5 text-left transition hover:bg-ink-800">
      <div className="min-w-0">
        <div className="truncate text-2xs font-bold tracking-wider text-txt-dim">{idx.name}</div>
        <div className="num text-[13px] font-semibold text-txt">{num(v, decimals)}</div>
        <div className={clsx('num text-2xs font-semibold', toneClass(chg))}>{pct(chg)}</div>
      </div>
      <Sparkline data={idx.spark} width={64} height={28} color={idx.key === 'BVIX' ? '#F5A524' : undefined} />
    </button>
  )
}

export function TickerStrip() {
  const s = useGameState()
  return (
    <div className="flex shrink-0 overflow-x-auto border-b border-line bg-ink-900/60">
      {s.indices.map((i) => <IndexCell key={i.key} idx={i} />)}
    </div>
  )
}

export function StatusMarquee() {
  const s = useGameState()
  const { openSymbol } = useGame()
  const items = [...s.stocks, ...s.stocks]
  return (
    <div className="relative flex h-7 shrink-0 items-center overflow-hidden border-t border-line bg-ink-900 text-2xs">
      <div className="z-10 flex h-full items-center gap-1.5 border-r border-line bg-ink-900 px-3 font-bold tracking-wider text-txt-mute">
        <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-up" /> DSX · SIMULATED
      </div>
      <div className="flex animate-marquee whitespace-nowrap hover:[animation-play-state:paused]">
        {items.map((st, i) => (
          <button key={i} onClick={() => openSymbol(st.symbol, 'stock')} className="mx-3 inline-flex items-center gap-1.5 hover:text-txt">
            <span className="font-bold text-txt-dim">{st.symbol}</span>
            <span className="num text-txt">{num(st.price)}</span>
            <span className={clsx('num', toneClass(st.change_pct))}>{pct(st.change_pct)}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function nextBizLabel(iso: string): string {
  const d = new Date(iso.slice(0, 10) + 'T00:00:00Z')
  do d.setUTCDate(d.getUTCDate() + 1)
  while (d.getUTCDay() === 0 || d.getUTCDay() === 6)
  return d.toLocaleDateString('en-GB', { weekday: 'short', timeZone: 'UTC' }) + ' 09:00'
}

function ActionButton({ icon, label, cost, onClick, disabled, variant = 'default', title }: {
  icon: ReactNode; label: string; cost?: string; onClick: () => void; disabled?: boolean
  variant?: 'default' | 'buy' | 'sell' | 'time' | 'primary' | 'leave'; title?: string
}) {
  const styles = {
    default: 'border-line bg-ink-800 hover:border-ink-500 hover:bg-ink-750',
    buy: 'border-up/40 bg-up-soft text-up hover:bg-up/20',
    sell: 'border-down/40 bg-down-soft text-down hover:bg-down/20',
    time: 'border-line bg-ink-800 hover:border-info/50 hover:bg-info-soft',
    primary: 'border-info/60 bg-info/90 text-white shadow-glowInfo hover:bg-info',
    leave: 'border-violet/40 bg-violet-soft text-violet hover:bg-violet/20',
  }[variant]
  return (
    <button onClick={onClick} disabled={disabled} title={title}
      className={clsx('flex h-[50px] min-w-[92px] flex-col items-center justify-center gap-0.5 rounded-md border px-2.5 transition disabled:cursor-not-allowed disabled:opacity-35', styles)}>
      <span className="flex items-center gap-1.5 text-[11px] font-bold tracking-wide">{icon}{label}</span>
      {cost && <span className={clsx('num text-[10px]', variant === 'primary' ? 'text-white/80' : 'text-txt-mute')}>{cost}</span>}
    </button>
  )
}

export function ActionBar() {
  const s = useGameState()
  const { run, busy, setModal, setPage, symbol } = useGame()
  const c = s.clock
  const blocked = s.popups.some((p) => p.blocking) || s.career.status !== 'ACTIVE'
  const open = c.market_status === 'OPEN'
  const lock = busy || blocked
  const h = c.game_hour
  const to = (n: number) => `→ ${String(Math.min(17, h + n)).padStart(2, '0')}:00`
  const isFriday = c.day_of_week === 'FRIDAY'
  const stockSymbol = s.stocks.some((x) => x.symbol === symbol) ? symbol : undefined
  return (
    <div className="flex shrink-0 items-center gap-2 overflow-x-auto border-t border-line bg-ink-900/80 px-3 py-2">
      <ActionButton icon={<ShoppingCart size={13} />} label="BUY STOCK" cost="instant" variant="buy" disabled={lock || !open}
        title={!open ? 'Market closed' : undefined} onClick={() => setModal({ kind: 'trade', side: 'BUY', symbol: stockSymbol })} />
      <ActionButton icon={<Briefcase size={13} />} label="SELL STOCK" cost="instant" variant="sell" disabled={lock || !open || s.holdings.length === 0}
        onClick={() => setModal({ kind: 'trade', side: 'SELL', symbol: s.holdings.find((x) => x.symbol === symbol)?.symbol ?? s.holdings[0]?.symbol })} />
      <ActionButton icon={<FileSearch size={13} />} label="RESEARCH" cost="1h · 3h" disabled={lock || !open}
        onClick={() => setModal({ kind: 'research', symbol: stockSymbol })} />
      <ActionButton icon={<Wallet size={13} />} label="PORTFOLIO" cost="view" onClick={() => setPage('portfolio')} />
      <div className="mx-1 h-9 w-px bg-line" />
      <ActionButton icon={<Clock size={13} />} label={open ? 'WORK 1 HOUR' : 'START DAY'} cost={open ? to(1) : `→ ${nextBizLabel(c.game_date)}`}
        variant="primary" disabled={lock} onClick={() => run(open ? api.advanceHour : api.nextBusinessDay)} />
      <ActionButton icon={<ChevronsRight size={13} />} label="SKIP 2H" cost={to(2)} variant="time" disabled={lock || !open || c.hours_to_close < 1}
        onClick={() => run(() => api.advanceHours(2))} />
      <ActionButton icon={<ChevronsRight size={13} />} label="SKIP 4H" cost={to(4)} variant="time" disabled={lock || !open || c.hours_to_close < 1}
        onClick={() => run(() => api.advanceHours(4))} />
      <ActionButton icon={<Gauge size={13} />} label="TO CLOSE" cost="→ 17:00" variant="time" disabled={lock || !open}
        onClick={() => run(api.advanceToClose)} />
      <ActionButton icon={<Sunrise size={13} />} label="NEXT BUSINESS DAY" cost={`→ ${nextBizLabel(c.game_date)}`} variant="time" disabled={lock}
        onClick={() => run(api.nextBusinessDay)} />
      {isFriday && (
        <ActionButton icon={<SkipForward size={13} />} label="SKIP WEEKEND" cost="→ Mon 09:00" variant="time" disabled={lock}
          onClick={() => run(api.skipWeekend)} />
      )}
      <ActionButton icon={<FastForward size={13} />} label="NEXT WEEK" cost="→ Mon 09:00" variant="time" disabled={lock}
        onClick={() => run(api.nextWeek)} />
      <div className="mx-1 h-9 w-px bg-line" />
      <ActionButton icon={<Palmtree size={13} />} label="TAKE LEAVE" cost={`${s.leave.remaining}d left`} variant="leave" disabled={lock}
        onClick={() => setModal({ kind: 'leave' })} />
      <div className="ml-auto flex items-center gap-2 pl-3 text-2xs text-txt-mute">
        <CalendarClock size={13} />
        <span className="num">{s.stats.hours_worked}h worked · {s.stats.hours_skipped}h skipped</span>
      </div>
    </div>
  )
}
