import clsx from 'clsx'
import { Bell, Pause, Play, Save, Settings } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { LIVE_SPEEDS, useGame, useGameState } from '../../game/GameContext'
import { gameTime } from '../../game/format'
import { api } from '../../services/api'
import { Bar } from '../common/ui'

const STATUS_STYLE: Record<string, string> = {
  OPEN: 'text-up border-up/40 bg-up-soft',
  CLOSED: 'text-down border-down/40 bg-down-soft',
  WEEKEND: 'text-violet border-violet/40 bg-violet-soft',
  PRE_MARKET: 'text-warn border-warn/40 bg-warn-soft',
}

export function TopBar() {
  const s = useGameState()
  const { live, setLive, speed, setSpeed, setModal, run } = useGame()
  const { clock, career } = s
  const xpSpan = Math.max(1, career.xp_next - career.xp_level_start)
  const xpIn = career.xp - career.xp_level_start
  const unread = s.notifications.filter((n) => !n.read).length
  const [open, setOpen] = useState(false)
  const menu = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const h = (e: MouseEvent) => menu.current && !menu.current.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  const repTone = career.reputation >= 70 ? 'text-up' : career.reputation >= 45 ? 'text-info' : career.reputation >= 30 ? 'text-warn' : 'text-down'

  return (
    <header className="relative z-20 flex h-14 shrink-0 items-center gap-4 border-b border-line bg-ink-900/90 px-4 backdrop-blur">
      <div className="flex shrink-0 items-center gap-2.5 pr-2">
        <div className="grid h-8 w-8 place-items-center rounded-md bg-gradient-to-br from-info to-violet shadow-glowInfo">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="white" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 17l5-6 4 3 7-9" />
          </svg>
        </div>
        <div className="leading-none">
          <div className="font-display text-[15px] font-bold tracking-wide">IB MODE</div>
          <div className="mt-0.5 text-2xs uppercase tracking-[0.18em] text-txt-mute">{career.firm}</div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3 border-l border-line pl-4">
        <div className="grid h-9 w-9 place-items-center rounded-full border-2 border-gold/70 bg-gold-soft font-display text-sm font-bold text-gold shadow-glowGold" title="Career level">
          {career.level}
        </div>
        <div className="min-w-[190px]">
          <div className="whitespace-nowrap text-[11px] font-bold uppercase tracking-wider text-txt">{career.title}</div>
          <div className="mt-1 flex items-center gap-2">
            <Bar value={xpIn} max={xpSpan} tone="gold" className="w-20" />
            <span className="num whitespace-nowrap text-2xs text-txt-mute">{career.xp.toLocaleString('en-IN')} / {career.xp_next.toLocaleString('en-IN')} XP</span>
          </div>
        </div>
        <div className="ml-1" title="Reputation (0-100)">
          <div className="label">Reputation</div>
          <div className={clsx('num text-[15px] font-bold', repTone)}>{career.reputation.toFixed(0)}</div>
        </div>
        {career.warning_level > 0 && (
          <span className={clsx('rounded border px-2 py-0.5 text-2xs font-bold uppercase tracking-wider',
            career.warning_level >= 2 ? 'border-down/50 bg-down-soft text-down' : 'border-warn/50 bg-warn-soft text-warn')}>
            {career.warning_level >= 2 ? 'Final warning' : 'Warning'}
          </span>
        )}
      </div>

      <div className="mx-auto flex items-center gap-5">
        <div className="text-right">
          <div className="label">{clock.day_of_week}</div>
          <div className="num text-[22px] font-bold leading-none text-txt">{clock.time}</div>
        </div>
        <div className="border-l border-line pl-4">
          <div className="text-[11px] font-semibold text-txt-dim">{clock.label}</div>
          <div className="mt-0.5 flex items-center gap-2 text-2xs text-txt-mute">
            <span className="num font-semibold text-txt">DAY {Math.min(clock.quarter_day, clock.quarter_days)} / {clock.quarter_days}</span>
            <span>·</span>
            <span>Q{clock.quarter}, YEAR {clock.career_year}</span>
          </div>
        </div>
        <span className={clsx('flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-2xs font-bold tracking-wider', STATUS_STYLE[clock.market_status])}>
          <span className={clsx('h-1.5 w-1.5 rounded-full bg-current', clock.market_status === 'OPEN' && 'animate-pulseDot')} />
          MARKET {clock.market_status.replace('_', '-')}
        </span>
        {clock.market_status === 'OPEN' && (
          <span className="num text-2xs text-txt-mute">{clock.hours_to_close}h to close</span>
        )}
      </div>

      <div className="flex items-center gap-1.5 rounded-md border border-line bg-ink-850 p-1" title="Live mode: the clock advances automatically, one game hour at a time">
        <button
          onClick={() => setLive(!live)}
          disabled={career.status !== 'ACTIVE'}
          className={clsx('flex h-7 items-center gap-1.5 rounded px-2.5 text-2xs font-bold tracking-wider transition disabled:opacity-40',
            live ? 'bg-up text-ink-950 shadow-glowUp' : 'bg-ink-700 text-txt-dim hover:text-txt')}
        >
          {live ? <Pause size={12} /> : <Play size={12} />}
          {live ? 'LIVE' : 'PAUSED'}
        </button>
        {LIVE_SPEEDS.map((sp, i) => (
          <button key={sp.label} onClick={() => setSpeed(i)}
            className={clsx('h-7 rounded px-2 text-2xs font-bold', speed === i ? 'bg-ink-600 text-txt' : 'text-txt-mute hover:text-txt-dim')}>
            {sp.label}
          </button>
        ))}
      </div>

      <div className="relative flex items-center gap-1" ref={menu}>
        <button aria-label="Notifications" onClick={() => {
          setOpen(!open)
          if (!open && unread) run(() => api.markRead('notifications'), { quiet: true })
        }} className="relative rounded-md p-2 text-txt-dim hover:bg-ink-750 hover:text-txt">
          <Bell size={17} />
          {unread > 0 && (
            <span className="num absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-down px-1 text-[9px] font-bold text-white">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </button>
        <button aria-label="Save / load" onClick={() => setModal({ kind: 'saves' })} className="rounded-md p-2 text-txt-dim hover:bg-ink-750 hover:text-txt"><Save size={17} /></button>
        <button aria-label="Settings" onClick={() => setModal({ kind: 'settings' })} className="rounded-md p-2 text-txt-dim hover:bg-ink-750 hover:text-txt"><Settings size={17} /></button>
        {open && (
          <div className="panel absolute right-0 top-11 w-96 animate-fadeIn overflow-hidden">
            <div className="border-b border-line px-3 py-2 label">Notifications</div>
            <div className="max-h-[420px] overflow-y-auto">
              {s.notifications.length === 0 && <div className="p-4 text-xs text-txt-mute">Nothing yet.</div>}
              {s.notifications.map((n) => (
                <div key={n.id} className="border-b border-line/60 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className={clsx('text-2xs font-bold uppercase tracking-wider', NOTIF_TONE[n.kind] ?? 'text-info')}>{n.title}</span>
                    <span className="num text-2xs text-txt-mute">{gameTime(n.time)}</span>
                  </div>
                  <div className="mt-0.5 text-xs text-txt-dim">{n.body}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

const NOTIF_TONE: Record<string, string> = {
  RISK_WARNING: 'text-down',
  MARKET_ALERT: 'text-warn',
  TARGET_UPDATE: 'text-gold',
  BREAKING: 'text-info',
  CEO_MESSAGE: 'text-violet',
  TRADE: 'text-up',
  OPPORTUNITY: 'text-gold',
}
