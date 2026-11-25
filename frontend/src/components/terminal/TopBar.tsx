import clsx from 'clsx'
import { Bell, CalendarClock, ChevronDown, FastForward, Gauge, Palmtree, Save, Settings, SkipForward, Sunrise } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useGame, useGameState } from '../../game/GameContext'
import { gameTime } from '../../game/format'
import { api } from '../../services/api'
import type { Page } from '../../types/game'
import { useOutside } from '../chart/ChartPanel'

export const NAV: { page: Page; label: string }[] = [
  { page: 'dashboard', label: 'Dashboard' },
  { page: 'markets', label: 'Markets' },
  { page: 'stock', label: 'Chart' },
  { page: 'orders', label: 'Orders' },
  { page: 'portfolio', label: 'Portfolio' },
  { page: 'research', label: 'Research' },
  { page: 'news', label: 'News' },
  { page: 'team', label: 'Team' },
  { page: 'career', label: 'Career' },
  { page: 'performance', label: 'Performance' },
]

/** Countdown that ticks locally between server updates. */
export function useCountdown(seconds: number, key: unknown): number {
  const [left, setLeft] = useState(seconds)
  useEffect(() => {
    const end = Date.now() + seconds * 1000
    setLeft(seconds)
    const id = setInterval(() => setLeft(Math.max(0, (end - Date.now()) / 1000)), 1000)
    return () => clearInterval(id)
  }, [seconds, key])
  return left
}

function TimeMenu() {
  const s = useGameState()
  const { run, busy, setModal } = useGame()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useOutside(ref, useCallback(() => setOpen(false), []))
  const c = s.clock
  const blocked = busy || s.popups.some((p) => p.blocking && p.type === 'REVIEW') || s.career.status !== 'ACTIVE'
  const isOpen = c.market_status === 'OPEN'
  const act = (fn: () => Promise<never> | ReturnType<typeof api.advanceHour>) => {
    setOpen(false)
    run(fn as () => ReturnType<typeof api.advanceHour>)
  }
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(!open)} title="Skip time"
        className={clsx('flex h-8 items-center gap-1 rounded px-2 text-xs text-txt-dim hover:bg-ink-750 hover:text-txt', open && 'bg-ink-750 text-txt')}>
        <FastForward size={14} /> <ChevronDown size={12} className="opacity-60" />
      </button>
      {open && (
        <div className="menu absolute right-0 top-9 w-64">
          <div className="px-3 pb-1 pt-1.5 text-2xs text-txt-mute">The market runs on its own. Skipping simulates every minute in between.</div>
          <button className="menu-item" disabled={blocked || !isOpen} onClick={() => act(() => api.advanceHour())}><SkipForward size={14} />Skip to the next hour</button>
          <button className="menu-item" disabled={blocked || !isOpen} onClick={() => act(api.advanceToClose)}><Gauge size={14} />Skip to the close (17:00)</button>
          <button className="menu-item" disabled={blocked} onClick={() => act(api.nextBusinessDay)}><Sunrise size={14} />Next trading day</button>
          <button className="menu-item" disabled={blocked} onClick={() => act(api.nextWeek)}><CalendarClock size={14} />Next week</button>
          <div className="my-1 border-t border-line" />
          <button className="menu-item" disabled={blocked} onClick={() => { setOpen(false); setModal({ kind: 'leave' }) }}>
            <Palmtree size={14} />Take leave <span className="ml-auto text-2xs text-txt-mute">{s.leave.remaining} days</span>
          </button>
        </div>
      )}
    </div>
  )
}

export function MarketClock() {
  const s = useGameState()
  const { setSpeed, busy } = useGame()
  const c = s.clock
  const live = s.live
  const wait = useCountdown(live.next_tick_in, s.version)
  const status = c.market_status
  const label = status === 'OPEN' ? 'Open' : status === 'CLOSED' ? 'Closed' : status === 'WEEKEND' ? 'Weekend' : 'Pre-open'
  return (
    <div className="flex items-center gap-3">
      <div className="text-right leading-tight">
        <div className="num text-[15px] font-semibold text-txt">{c.time}</div>
        <div className="text-2xs text-txt-mute">{c.label.slice(0, 3)} {c.label.slice(4, 10)}</div>
      </div>
      <div className="leading-tight">
        <div className={clsx('flex items-center gap-1.5 text-xs font-medium', status === 'OPEN' ? 'text-up' : 'text-txt-dim')}>
          <span className={clsx('h-1.5 w-1.5 rounded-full', status === 'OPEN' ? 'animate-pulseDot bg-up' : 'bg-txt-mute')} />
          {label}
        </div>
        <div className="num text-2xs text-txt-mute">
          {status === 'OPEN'
            ? `closes in ${Math.floor(c.minutes_to_close / 60)}h ${String(c.minutes_to_close % 60).padStart(2, '0')}m`
            : s.career.status === 'ACTIVE' ? `opens in ${Math.ceil(wait)}s` : 'paused'}
        </div>
      </div>
      <div className="flex rounded border border-line p-0.5" title={`Speed. At 1x a full 8-hour session takes ${Math.round(live.session_seconds / 60)} minutes.`}>
        {live.speeds.map((x) => (
          <button key={x} disabled={busy} onClick={() => x !== live.speed && setSpeed(x)}
            className={clsx('h-6 min-w-[30px] rounded px-1.5 text-xs font-medium', live.speed === x ? 'bg-ink-700 text-txt' : 'text-txt-mute hover:text-txt')}>
            {x}x
          </button>
        ))}
      </div>
    </div>
  )
}

export function TopBar() {
  const s = useGameState()
  const { page, setPage, setModal, run } = useGame()
  const unread = s.notifications.filter((n) => !n.read).length
  const [open, setOpen] = useState(false)
  const menu = useRef<HTMLDivElement>(null)
  useOutside(menu, useCallback(() => setOpen(false), []))
  const openOrders = s.orders.filter((o) => o.status === 'OPEN' || o.status === 'TRIGGERED').length
  const unreadMsgs = s.messages.filter((m) => !m.read).length

  return (
    <header className="relative z-20 flex h-12 shrink-0 items-center gap-2 border-b border-line bg-ink-900 pl-3 pr-2">
      <div className="flex shrink-0 items-center gap-2 pr-3" title={`${s.career.firm} · ${s.career.title}`}>
        <div className="grid h-7 w-7 place-items-center rounded bg-info text-white">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round"><path d="M4 17l5-6 4 3 7-9" /></svg>
        </div>
        <span className="hidden text-sm font-semibold text-txt 2xl:inline">IB Mode</span>
      </div>
      <nav className="flex h-full min-w-0 flex-1 items-stretch overflow-x-auto [scrollbar-width:none]">
        {NAV.map((n) => {
          const badge = n.page === 'orders' ? openOrders : n.page === 'team' ? unreadMsgs : 0
          return (
            <button key={n.page} onClick={() => setPage(n.page)} className={clsx('tab shrink-0', page === n.page && 'tab-on')}>
              {n.label}
              {badge > 0 && <span className="num ml-1.5 rounded bg-ink-700 px-1 text-[10px] text-txt-dim">{badge}</span>}
            </button>
          )
        })}
      </nav>
      <div className="flex shrink-0 items-center gap-1.5">
        <MarketClock />
        <TimeMenu />
        <span className="mx-1 h-6 w-px bg-line" />
        <div className="relative" ref={menu}>
          <button aria-label="Notifications" className="icon-btn relative" onClick={() => {
            setOpen(!open)
            if (!open && unread) run(() => api.markRead('notifications'), { quiet: true })
          }}>
            <Bell size={16} />
            {unread > 0 && <span className="num absolute right-1 top-1 grid h-3.5 min-w-3.5 place-items-center rounded-full bg-down px-0.5 text-[9px] font-semibold text-white">{unread > 9 ? '9+' : unread}</span>}
          </button>
          {open && (
            <div className="menu absolute right-0 top-10 w-96 !py-0">
              <div className="border-b border-line px-3 py-2 text-xs font-medium text-txt-dim">Notifications</div>
              <div className="max-h-[420px] overflow-y-auto">
                {s.notifications.length === 0 && <div className="p-4 text-xs text-txt-mute">Nothing yet.</div>}
                {s.notifications.map((n) => (
                  <div key={n.id} className="border-b border-line/60 px-3 py-2 last:border-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className={clsx('text-xs font-medium', NOTIF_TONE[n.kind] ?? 'text-txt')}>{n.title}</span>
                      <span className="num shrink-0 text-2xs text-txt-mute">{gameTime(n.time)}</span>
                    </div>
                    <div className="mt-0.5 text-xs text-txt-dim">{n.body}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <button aria-label="Save / load" className="icon-btn" onClick={() => setModal({ kind: 'saves' })}><Save size={16} /></button>
        <button aria-label="Settings" className="icon-btn" onClick={() => setModal({ kind: 'settings' })}><Settings size={16} /></button>
      </div>
    </header>
  )
}

const NOTIF_TONE: Record<string, string> = {
  RISK_WARNING: 'text-down',
  MARKET_ALERT: 'text-warn',
  PRICE_ALERT: 'text-warn',
  TARGET_UPDATE: 'text-gold',
  BREAKING: 'text-info',
  CEO_MESSAGE: 'text-violet',
  TRADE: 'text-up',
  OPPORTUNITY: 'text-gold',
  RESEARCH: 'text-info',
}
