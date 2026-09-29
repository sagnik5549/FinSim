import clsx from 'clsx'
import { Award, CheckCircle2, Circle, Lock, ScrollText, Star, Trophy } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Avatar } from '../components/common/Avatar'
import { Badge, Bar, Empty, Panel, Ring } from '../components/common/ui'
import { useGameState } from '../game/GameContext'
import { gameTime, money, pct } from '../game/format'
import { api } from '../services/api'

interface CareerPayload {
  level: number; title: string; xp: number; xp_next: number; xp_level_start: number; reputation: number; warning_level: number
  target_progress: number; time_progress: number; quarter_index: number
  promotion_requirements: { label: string; value: number; met: boolean }[]
  history: { quarter: number; level: number; title: string; outcome: string; return_pct: number; max_drawdown: number; reputation_change: number; date: string }[]
  achievements: string[]
  decisions: { t: string; kind: string; text: string }[]
  ladder: { level: number; title: string; unlocks: string[]; target_return: number; max_drawdown: number }[]
}

export default function CareerPage() {
  const s = useGameState()
  const [c, setC] = useState<CareerPayload | null>(null)
  useEffect(() => { api.get<CareerPayload>('/career').then(setC).catch(() => setC(null)) }, [s.version])
  if (!c) return <Empty>Loading career…</Empty>
  const xpSpan = Math.max(1, c.xp_next - c.xp_level_start)
  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-2.5 overflow-y-auto p-2.5">
      <div className="panel relative col-span-12 overflow-hidden lg:col-span-8">
        <div className="absolute inset-0 bg-gradient-to-br from-gold/10 via-transparent to-info/10" />
        <div className="relative flex items-center gap-6 p-5">
          <div className="relative">
            <div className="grid h-28 w-28 place-items-center rounded-2xl border-2 border-gold/70 bg-ink-900 shadow-glowGold">
              <div className="text-center"><div className="label !text-gold">Level</div><div className="font-display text-5xl font-bold text-gold">{c.level}</div></div>
            </div>
          </div>
          <div className="min-w-0 flex-1">
            <div className="label tracking-[0.25em]">Apex Capital · Quarter {c.quarter_index}</div>
            <div className="font-display text-3xl font-bold">{c.title.toUpperCase()}</div>
            <div className="mt-3 flex items-center gap-3">
              <Bar value={c.xp - c.xp_level_start} max={xpSpan} tone="gold" className="h-2.5 max-w-sm" />
              <span className="num text-xs text-txt-dim">{c.xp.toLocaleString('en-IN')} / {c.xp_next.toLocaleString('en-IN')} XP</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge tone={c.warning_level === 0 ? 'up' : c.warning_level === 1 ? 'warn' : 'down'}>{['Clean record', 'Warning', 'Final warning'][Math.min(2, c.warning_level)]}</Badge>
              <Badge tone="info">Risk profile {s.career.risk_profile}</Badge>
              <Badge tone="violet">Target {money(s.career.target_value)}</Badge>
            </div>
          </div>
          <div className="flex gap-4">
            <Ring value={c.reputation / 100} color={c.reputation >= 60 ? '#26D07C' : c.reputation >= 40 ? '#F5A524' : '#F2495C'} size={96}>
              <span className="num text-xl font-bold">{Math.round(c.reputation)}</span><span className="text-[9px] uppercase tracking-wider text-txt-mute">reputation</span>
            </Ring>
            <Ring value={Math.max(0, c.target_progress)} color="#E9B949" size={96}>
              <span className="num text-xl font-bold">{Math.round(c.target_progress * 100)}%</span><span className="text-[9px] uppercase tracking-wider text-txt-mute">target</span>
            </Ring>
          </div>
        </div>
      </div>

      <Panel title="Promotion requirements" icon={<Star size={13} />} className="col-span-12 lg:col-span-4">
        <ul className="space-y-2 p-3">
          {c.promotion_requirements.map((r) => (
            <li key={r.label} className="flex items-center gap-2 text-xs">
              {r.met ? <CheckCircle2 size={15} className="text-up" /> : <Circle size={15} className="text-txt-mute" />}
              <span className={r.met ? 'text-txt' : 'text-txt-dim'}>{r.label}</span>
              <span className="num ml-auto text-txt-mute">{r.label.includes('Reputation') ? Math.round(r.value) : r.label.includes('%') ? pct(r.value, 1) : r.value}</span>
            </li>
          ))}
        </ul>
        <div className="border-t border-line px-3 py-2 text-2xs text-txt-mute">Time elapsed in quarter: {Math.round(c.time_progress * 100)}%. Reviews weigh return, risk conduct, reputation, alpha and decision quality — not profit alone.</div>
      </Panel>

      <Panel title="Career ladder" icon={<Trophy size={13} />} className="col-span-12 lg:col-span-8">
        <div className="grid grid-cols-7 gap-2 p-3">
          {c.ladder.map((l) => {
            const done = l.level < c.level
            const cur = l.level === c.level
            return (
              <div key={l.level} className={clsx('relative rounded-lg border p-2.5 text-center',
                cur ? 'border-gold/70 bg-gold-soft shadow-glowGold' : done ? 'border-up/40 bg-up-soft' : 'border-line bg-ink-900 opacity-70')}>
                <div className={clsx('mx-auto grid h-8 w-8 place-items-center rounded-full font-display text-sm font-bold', cur ? 'bg-gold text-ink-950' : done ? 'bg-up text-ink-950' : 'bg-ink-700 text-txt-mute')}>
                  {l.level > c.level ? <Lock size={13} /> : l.level}
                </div>
                <div className="mt-1.5 text-[11px] font-bold leading-tight">{l.title}</div>
                <ul className="mt-1.5 space-y-0.5 text-[10px] leading-tight text-txt-mute">{l.unlocks.slice(0, 3).map((u) => <li key={u}>{u}</li>)}</ul>
              </div>
            )
          })}
        </div>
      </Panel>

      <Panel title="Achievements" icon={<Award size={13} />} className="col-span-12 lg:col-span-4" bodyClass="overflow-y-auto">
        {c.achievements.length === 0 ? <Empty>Hit your first target to earn an achievement.</Empty> : (
          <ul className="space-y-1.5 p-3">{c.achievements.map((a) => <li key={a} className="flex items-center gap-2 text-xs"><Award size={13} className="text-gold" />{a}</li>)}</ul>
        )}
      </Panel>

      <Panel title="Career history" className="col-span-12 lg:col-span-6" bodyClass="overflow-y-auto">
        {c.history.length === 0 ? (
          <div className="flex items-center gap-3 p-4 text-xs text-txt-dim"><Avatar id="ceo" size={44} /><p>"Your first review comes at the end of the quarter. Make it count."</p></div>
        ) : (
          <table className="w-full text-xs">
            <thead className="table-head"><tr><th>Quarter</th><th>Role</th><th>Outcome</th><th className="!text-right">Return</th><th className="!text-right">Max DD</th><th className="!text-right">Rep Δ</th></tr></thead>
            <tbody>{c.history.map((h) => (
              <tr key={h.quarter} className="table-row">
                <td className="num">Q{h.quarter}</td><td>{h.title}</td>
                <td><Badge tone={h.outcome === 'PROMOTED' ? 'gold' : h.outcome === 'TARGET ACHIEVED' ? 'up' : h.outcome === 'WARNING' ? 'warn' : 'down'}>{h.outcome}</Badge></td>
                <td className="num text-right">{pct(h.return_pct)}</td><td className="num text-right">{pct(h.max_drawdown, 1, false)}</td><td className="num text-right">{h.reputation_change.toFixed(1)}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </Panel>

      <Panel title="Major decisions" icon={<ScrollText size={13} />} className="col-span-12 lg:col-span-6" bodyClass="max-h-72 overflow-y-auto">
        {c.decisions.length === 0 ? <Empty>Large trades, risk calls and leave will be logged here.</Empty> : (
          <ul>{c.decisions.map((d, i) => (
            <li key={i} className="flex items-center gap-2 border-b border-line/60 px-3 py-1.5 text-xs">
              <Badge tone={d.kind === 'RISK' ? 'warn' : d.kind === 'WARNING' ? 'down' : d.kind === 'DEAL' ? 'gold' : 'info'}>{d.kind}</Badge>
              <span className="truncate">{d.text}</span>
              <span className="num ml-auto shrink-0 text-2xs text-txt-mute">{gameTime(d.t)}</span>
            </li>
          ))}</ul>
        )}
      </Panel>
    </div>
  )
}
