import clsx from 'clsx'
import { AlertTriangle, ArrowRight, Globe2, Palmtree, ShieldAlert, Sunrise, TrendingDown, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useGame, useGameState } from '../../game/GameContext'
import { int, money, pct, shortDate, toneClass } from '../../game/format'
import { api } from '../../services/api'
import type { Popup } from '../../types/game'
import { Avatar } from '../common/Avatar'
import { Badge, Bar, Button, Modal } from '../common/ui'
import { Speaker } from './SystemModals'

const ORDER: Record<string, number> = { REVIEW: 0, RISK_WARNING: 1, DIALOGUE: 2, LEAVE_REPORT: 3, WEEKEND_REPORT: 4, DAILY_REPORT: 5 }

export function PopupHost() {
  const s = useGameState()
  const { modal } = useGame()
  if (modal && s.popups.every((p) => !p.blocking)) return null
  const p = [...s.popups].sort((a, b) => ORDER[a.type] - ORDER[b.type])[0]
  if (!p) return null
  switch (p.type) {
    case 'REVIEW': return <QuarterlyReview popup={p} key={p.id} />
    case 'RISK_WARNING': return <RiskWarningModal popup={p} key={p.id} />
    case 'DIALOGUE': return <DialogueModal popup={p} key={p.id} />
    case 'LEAVE_REPORT': return <LeaveReport popup={p} key={p.id} />
    case 'WEEKEND_REPORT': return <WeekendReport popup={p} key={p.id} />
    case 'DAILY_REPORT': return <DailyReport popup={p} key={p.id} />
    default: return null
  }
}

function useAck(p: Popup) {
  const { run } = useGame()
  return () => run(() => api.ackPopup(p.id))
}

function Line({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-line/60 py-1.5 text-xs">
      <span className="text-txt-mute">{k}</span>
      <span className={clsx('num font-semibold', tone)}>{v}</span>
    </div>
  )
}

function DailyReport({ popup }: { popup: Popup }) {
  const d = popup.payload
  const ack = useAck(popup)
  return (
    <Modal onClose={ack} width="max-w-[460px]">
      <div className="border-b border-line bg-gradient-to-r from-info/10 px-5 py-3">
        <div className="label">End of day · {shortDate(d.date)}</div>
        <div className="font-display text-lg font-bold">Market summary</div>
      </div>
      <div className="px-5 py-3">
        <div className="mb-2 grid grid-cols-4 gap-2 text-center">
          {Object.entries(d.indices as Record<string, number>).map(([k, v]) => (
            <div key={k} className="rounded bg-ink-900 py-1.5"><div className="label">{k}</div><div className={clsx('num text-xs font-bold', k === 'BVIX' ? 'text-warn' : toneClass(v))}>{pct(v)}</div></div>
          ))}
        </div>
        <Line k="Portfolio" v={`${money(d.portfolio_change, { signed: true })} (${pct(d.portfolio_change_pct)})`} tone={toneClass(d.portfolio_change)} />
        <Line k="Portfolio value" v={money(d.portfolio_value)} />
        {d.best_holding && <Line k="Best holding" v={`${d.best_holding.name} ${pct(d.best_holding.change)}`} tone={toneClass(d.best_holding.change)} />}
        {d.worst_holding && d.worst_holding.symbol !== d.best_holding?.symbol && <Line k="Worst holding" v={`${d.worst_holding.name} ${pct(d.worst_holding.change)}`} tone={toneClass(d.worst_holding.change)} />}
        <Line k="New events" v={d.new_events} />
        <Line k="Risk" v={`${d.risk_level} (${Math.round(d.risk_score)})`} tone={d.risk_level === 'HIGH' || d.risk_level === 'CRITICAL' ? 'text-down' : undefined} />
        <div className="py-2">
          <div className="flex justify-between text-xs"><span className="text-txt-mute">Target progress</span><span className="num font-bold text-gold">{Math.round(d.target_progress * 100)}%</span></div>
          <Bar value={Math.max(0, d.target_progress)} tone="gold" className="mt-1" />
        </div>
        {d.headlines?.length > 0 && (
          <ul className="mt-1 space-y-0.5 text-2xs text-txt-dim">{d.headlines.map((h: string, i: number) => <li key={i}>• {h}</li>)}</ul>
        )}
        <Button variant="primary" className="mt-3 w-full" onClick={ack}>CONTINUE <ArrowRight size={14} /></Button>
      </div>
    </Modal>
  )
}

function WeekendReport({ popup }: { popup: Popup }) {
  const d = popup.payload
  const ack = useAck(popup)
  const sectors = Object.entries(d.sectors as Record<string, number>).sort((a, b) => b[1] - a[1])
  return (
    <Modal onClose={ack} width="max-w-[520px]">
      <div className="flex items-center gap-3 border-b border-line bg-gradient-to-r from-violet/15 px-5 py-3">
        <Sunrise className="text-violet" size={22} />
        <div>
          <div className="label">{shortDate(d.from)} → {shortDate(d.to)}</div>
          <div className="font-display text-lg font-bold">Weekend report</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 px-5 py-3">
        <div>
          <div className="label mb-1 flex items-center gap-1"><Globe2 size={11} /> Global markets</div>
          <Line k="US Tech 100" v={pct(d.global.UST100)} tone={toneClass(d.global.UST100)} />
          <Line k="US 500" v={pct(d.global.US500)} tone={toneClass(d.global.US500)} />
          <Line k="Gold" v={pct(d.global.GOLD)} tone={toneClass(d.global.GOLD)} />
          <Line k="USD/INR" v={pct(d.global.USDINR)} tone={toneClass(-d.global.USDINR)} />
          <Line k="Crude" v={`$${d.oil.toFixed(1)}`} />
        </div>
        <div>
          <div className="label mb-1">Sector gaps at the open</div>
          {sectors.slice(0, 3).concat(sectors.slice(-2)).map(([k, v]) => <Line key={k} k={k} v={pct(v)} tone={toneClass(v)} />)}
        </div>
      </div>
      {d.headlines.length > 0 && (
        <div className="mx-5 rounded-md border border-line bg-ink-900 p-2.5">
          <div className="label mb-1">Major news</div>
          <ul className="space-y-0.5 text-xs">{d.headlines.map((h: string, i: number) => <li key={i}>"{h}"</li>)}</ul>
        </div>
      )}
      <div className="px-5 py-3">
        <div className="label mb-1">Your portfolio</div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded bg-ink-900 py-2"><div className="label">Friday close</div><div className="num text-sm font-bold">{money(d.friday_close)}</div></div>
          <div className="rounded bg-ink-900 py-2"><div className="label">Monday open</div><div className="num text-sm font-bold">{money(d.monday_open)}</div></div>
          <div className="rounded bg-ink-900 py-2"><div className="label">Change</div><div className={clsx('num text-sm font-bold', toneClass(d.change))}>{money(d.change, { signed: true })}</div></div>
        </div>
        <div className="mt-2 text-xs text-txt-mute">Risk: <span className={d.risk_level === 'HIGH' || d.risk_level === 'CRITICAL' ? 'font-bold text-down' : 'text-txt'}>{d.risk_level}</span></div>
        <Button variant="primary" className="mt-3 w-full" onClick={ack}>START THE WEEK <ArrowRight size={14} /></Button>
      </div>
    </Modal>
  )
}

function LeaveReport({ popup }: { popup: Popup }) {
  const d = popup.payload
  const ack = useAck(popup)
  const change = d.portfolio_after - d.portfolio_before
  return (
    <Modal onClose={ack} width="max-w-[500px]">
      <div className="flex items-center gap-4 border-b border-line bg-gradient-to-r from-violet/15 px-5 py-4">
        <Palmtree className="text-violet" size={26} />
        <div>
          <div className="font-display text-xl font-bold tracking-wide">WELCOME BACK</div>
          <div className="text-xs text-txt-dim">{shortDate(d.from)} → {shortDate(d.to)}</div>
        </div>
      </div>
      <div className="px-5 py-3">
        <Line k="Days away" v={d.days_away} />
        <Line k="Market move (BHARAT 50)" v={pct(d.market_move)} tone={toneClass(d.market_move)} />
        <Line k="Portfolio" v={<>{money(d.portfolio_before)} → {money(d.portfolio_after)}</>} tone={toneClass(change)} />
        <Line k="Change" v={money(change, { signed: true })} tone={toneClass(change)} />
        <Line k="New events" v={d.new_events} />
        <Line k="Team actions" v={d.team_actions.length && !d.team_actions[0].startsWith('No dedicated') ? d.team_actions.length : 0} />
        <Line k="Risk" v={d.risk_level} tone={d.risk_level === 'HIGH' || d.risk_level === 'CRITICAL' ? 'text-down' : undefined} />
        <Line k="Leave remaining" v={`${d.leave_remaining} days`} />
        {d.headlines.length > 0 && <ul className="mt-2 space-y-0.5 text-2xs text-txt-dim">{d.headlines.map((h: string, i: number) => <li key={i}>• {h}</li>)}</ul>}
        {d.team_actions.length > 0 && <ul className="mt-2 space-y-0.5 rounded border border-line bg-ink-900 p-2 text-2xs text-txt-dim">{d.team_actions.map((h: string, i: number) => <li key={i}>• {h}</li>)}</ul>}
        <Button variant="primary" className="mt-3 w-full" onClick={ack}>BACK TO THE DESK <ArrowRight size={14} /></Button>
      </div>
    </Modal>
  )
}

const OPTION_TEXT: Record<string, { label: string; sub: string; variant: 'primary' | 'warn' | 'subtle' }> = {
  REDUCE_EXPOSURE: { label: 'REDUCE EXPOSURE', sub: 'Sell down to policy now', variant: 'primary' },
  REQUEST_EXCEPTION: { label: 'REQUEST EXCEPTION', sub: 'Risk Manager decides · 7 days', variant: 'warn' },
  IGNORE: { label: 'IGNORE', sub: 'Goes on your record', variant: 'subtle' },
}

function RiskWarningModal({ popup }: { popup: Popup }) {
  const d = popup.payload
  const s = useGameState()
  const { run, busy } = useGame()
  const rm = s.team.find((t) => t.id === 'risk_manager')
  const closed = s.clock.market_status !== 'OPEN' && !(s.clock.working_day && s.clock.game_hour === 17)
  return (
    <Modal closable={false} width="max-w-[520px]" className="border-down/50 shadow-glowDown">
      <div className="flex items-center gap-3 border-b border-down/30 bg-gradient-to-r from-down/20 px-5 py-3">
        <ShieldAlert className="text-down" size={24} />
        <div>
          <div className="font-display text-lg font-bold tracking-[0.18em] text-down">RISK WARNING</div>
          <div className="text-2xs text-txt-dim">{d.during_leave ? 'Raised while you were on leave' : 'Firm risk policy breached'}</div>
        </div>
      </div>
      <div className="space-y-4 px-5 py-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border border-down/40 bg-down-soft p-3 text-center">
            <div className="label">{d.label}</div>
            <div className="num mt-1 text-3xl font-bold text-down">{pct(d.value, 1, false)}</div>
          </div>
          <div className="rounded-md border border-line bg-ink-900 p-3 text-center">
            <div className="label">Firm policy</div>
            <div className="num mt-1 text-3xl font-bold text-txt">{pct(d.limit, 0, false)}</div>
          </div>
        </div>
        {rm && <Speaker id="risk_manager" name={rm.name} role="Chief Risk Officer" line={d.comment} />}
        {d.reduce_orders.length > 0 && (
          <div className="text-2xs text-txt-mute">Reduce plan: {d.reduce_orders.map((o: { symbol: string; qty: number }) => `sell ${int(o.qty)} ${o.symbol}`).join(', ')}</div>
        )}
        <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${d.options.length}, minmax(0,1fr))` }}>
          {d.options.map((o: string) => (
            <button key={o} disabled={busy || (o === 'REDUCE_EXPOSURE' && closed)}
              title={o === 'REDUCE_EXPOSURE' && closed ? 'Market closed: reduce at the next open or ignore for now' : undefined}
              onClick={() => run(() => api.resolveRisk(d.warning_id, o))}
              className={clsx('rounded-md border px-2 py-2.5 text-center transition disabled:opacity-40',
                o === 'REDUCE_EXPOSURE' ? 'border-info/60 bg-info/90 text-white hover:bg-info' :
                  o === 'REQUEST_EXCEPTION' ? 'border-warn/40 bg-warn-soft text-warn hover:bg-warn/25' :
                    'border-line bg-ink-800 text-txt-dim hover:text-txt')}>
              <div className="text-[11px] font-bold tracking-wider">{OPTION_TEXT[o].label}</div>
              <div className="mt-0.5 text-[10px] opacity-80">{OPTION_TEXT[o].sub}</div>
            </button>
          ))}
        </div>
      </div>
    </Modal>
  )
}

function DialogueModal({ popup }: { popup: Popup }) {
  const d = popup.payload as { title: string; tone: string; lines: { speaker: string; text: string }[] }
  const s = useGameState()
  const ack = useAck(popup)
  const [shown, setShown] = useState(1)
  const team = Object.fromEntries(s.team.map((t) => [t.id, t]))
  useEffect(() => {
    if (shown >= d.lines.length) return
    const t = setTimeout(() => setShown((x) => x + 1), 900)
    return () => clearTimeout(t)
  }, [shown, d.lines.length])
  const lead = d.lines[0]?.speaker ?? 'ceo'
  const toneCls = d.tone === 'danger' ? 'from-down/20 border-down/40' : d.tone === 'warning' ? 'from-warn/15 border-warn/30' : d.tone === 'positive' ? 'from-up/15 border-up/30' : 'from-info/10 border-line'
  return (
    <Modal onClose={ack} width="max-w-[600px]">
      <div className={clsx('flex items-end gap-4 border-b bg-gradient-to-r px-5 pt-4', toneCls)}>
        <Avatar id={lead} size={96} className="-mb-1 drop-shadow-xl" />
        <div className="pb-3">
          <div className="label">{team[lead]?.role}</div>
          <div className="font-display text-xl font-bold">{d.title}</div>
          <div className="text-xs text-txt-dim">{team[lead]?.name}</div>
        </div>
      </div>
      <div className="space-y-3 px-5 py-4">
        {d.lines.slice(0, shown).map((l, i) => (
          <div key={i} className="animate-fadeIn">
            <Speaker id={l.speaker} name={team[l.speaker]?.name ?? l.speaker} role={team[l.speaker]?.role ?? ''} line={l.text}
              tone={d.tone === 'danger' && l.speaker === 'ceo' ? 'border-down/40' : undefined} />
          </div>
        ))}
        <div className="flex justify-end">
          {shown < d.lines.length
            ? <Button onClick={() => setShown(d.lines.length)}>Skip</Button>
            : <Button variant="primary" onClick={ack}>Understood <ArrowRight size={14} /></Button>}
        </div>
      </div>
    </Modal>
  )
}

const OUTCOME_STYLE: Record<string, { color: string; ring: string; icon: JSX.Element }> = {
  PROMOTED: { color: 'text-gold', ring: 'border-gold shadow-glowGold', icon: <TrendingUp size={18} /> },
  'TARGET ACHIEVED': { color: 'text-up', ring: 'border-up shadow-glowUp', icon: <TrendingUp size={18} /> },
  WARNING: { color: 'text-warn', ring: 'border-warn', icon: <AlertTriangle size={18} /> },
  FAILED: { color: 'text-down', ring: 'border-down shadow-glowDown', icon: <TrendingDown size={18} /> },
  TERMINATED: { color: 'text-down', ring: 'border-down shadow-glowDown', icon: <TrendingDown size={18} /> },
}

function QuarterlyReview({ popup }: { popup: Popup }) {
  const r = popup.payload
  const s = useGameState()
  const { run, restart, busy } = useGame()
  const [stage, setStage] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setStage(1), 900)
    const t2 = setTimeout(() => setStage(2), 2100)
    return () => { clearTimeout(t); clearTimeout(t2) }
  }, [])
  const st = OUTCOME_STYLE[r.outcome] ?? OUTCOME_STYLE.WARNING
  const team = Object.fromEntries(s.team.map((t) => [t.id, t]))
  const terminated = r.outcome === 'TERMINATED'
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-ink-950/95 backdrop-blur-sm">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="text-center animate-rise">
          <div className="label tracking-[0.3em]">{s.career.firm} · Board room</div>
          <h1 className="mt-1 font-display text-3xl font-bold tracking-[0.12em]">QUARTERLY REVIEW</h1>
          <div className="mt-1 text-xs text-txt-mute">Quarter {r.quarter} · {r.title}</div>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-4">
          {[['ceo', r.ceo.join(' ')], ['cfo', r.cfo], ['risk_manager', r.risk_manager]].map(([id, text], i) => (
            <div key={id} className="panel flex flex-col items-center p-4 text-center animate-rise" style={{ animationDelay: `${0.15 * i}s` }}>
              <Avatar id={id} size={92} />
              <div className="mt-2 text-sm font-bold">{team[id]?.name}</div>
              <div className="text-2xs uppercase tracking-wider text-txt-mute">{team[id]?.role}</div>
              <p className="mt-2 text-xs leading-relaxed text-txt-dim">"{text}"</p>
            </div>
          ))}
        </div>

        <div className="mt-6 grid grid-cols-12 gap-4">
          <div className="panel col-span-7 p-4">
            <div className="grid grid-cols-3 gap-3">
              <Metric k="Starting capital" v={money(r.start_value)} />
              <Metric k="Ending capital" v={money(r.end_value)} tone={toneClass(r.end_value - r.start_value)} />
              <Metric k="Return" v={pct(r.return_pct)} tone={toneClass(r.return_pct)} />
              <Metric k="Target" v={`${pct(r.target_pct, 0)} · ${money(r.target_value)}`} />
              <Metric k="Benchmark" v={pct(r.benchmark_pct)} tone={toneClass(r.benchmark_pct)} />
              <Metric k="Max drawdown" v={`${pct(r.max_drawdown, 2, false)} / ${pct(r.drawdown_limit, 0, false)}`} tone={r.max_drawdown > r.drawdown_limit ? 'text-down' : 'text-up'} />
              <Metric k="Risk breaches" v={`${r.risk_violations} (${r.ignored_violations} ignored)`} tone={r.ignored_violations > 1 ? 'text-down' : undefined} />
              <Metric k="Reputation" v={`${Math.round(r.reputation_before)} → ${Math.round(r.reputation_after)}`} tone={toneClass(r.reputation_change)} />
              <Metric k="XP earned" v={`+${r.xp_gain}`} tone="text-gold" />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-md border border-up/30 bg-up-soft p-2.5">
                <div className="label !text-up">Best decision</div>
                <div className="mt-0.5">{r.best_decision ? <>{r.best_decision.name} <span className="num font-semibold text-up">{money(r.best_decision.pnl, { signed: true })}</span></> : 'No positions taken'}</div>
              </div>
              <div className="rounded-md border border-down/30 bg-down-soft p-2.5">
                <div className="label !text-down">Worst decision</div>
                <div className="mt-0.5">{r.worst_decision ? <>{r.worst_decision.name} <span className={clsx('num font-semibold', toneClass(r.worst_decision.pnl))}>{money(r.worst_decision.pnl, { signed: true })}</span></> : '—'}</div>
              </div>
            </div>
          </div>
          <div className="panel col-span-5 p-4">
            <div className="label mb-2">Board scorecard</div>
            {Object.entries(r.scores as Record<string, number>).map(([k, v]) => (
              <div key={k} className="mb-2">
                <div className="flex justify-between text-xs"><span className="capitalize text-txt-dim">{k.replace('_', ' ')}</span><span className="num font-semibold">{v}</span></div>
                <Bar value={v} max={100} tone={v >= 65 ? 'up' : v >= 45 ? 'warn' : 'down'} className="mt-1" />
              </div>
            ))}
            {r.decision_quality?.count > 0 && <div className="text-2xs text-txt-mute">Theses: {r.decision_quality.correct}/{r.decision_quality.count} proved right.</div>}
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center">
          {stage >= 1 && (
            <div className={clsx('flex items-center gap-3 rounded-lg border-4 px-8 py-3 font-display text-3xl font-bold tracking-[0.2em] animate-stamp', st.color, st.ring)}>
              {st.icon}{r.outcome}
            </div>
          )}
          {stage >= 2 && (
            <div className="mt-5 flex flex-col items-center gap-3 animate-fadeIn">
              {r.ladder_note && <div className="text-sm font-semibold text-down">{r.ladder_note}</div>}
              {r.next_level && <div className="text-sm text-gold">New role: <b>{r.next_level}</b> · unlocks {r.unlocks.join(', ')}</div>}
              {terminated
                ? <Button variant="gold" size="lg" onClick={restart}>START NEW CAREER</Button>
                : <Button variant="primary" size="lg" disabled={busy} onClick={() => run(() => api.ackPopup(popup.id))}>BEGIN NEXT QUARTER <ArrowRight size={16} /></Button>}
              <Badge tone={r.warning_level >= 2 ? 'down' : r.warning_level === 1 ? 'warn' : 'neutral'}>
                Warning status: {['Clean record', 'Warning', 'Final warning', 'Terminated'][Math.min(3, r.warning_level)]}
              </Badge>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Metric({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div className="rounded-md bg-ink-900 px-3 py-2">
      <div className="label">{k}</div>
      <div className={clsx('num mt-0.5 text-sm font-bold', tone)}>{v}</div>
    </div>
  )
}
