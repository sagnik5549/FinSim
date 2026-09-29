import clsx from 'clsx'
import { Inbox, Lock, UserPlus, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Avatar, accentOf } from '../components/common/Avatar'
import { Badge, Bar, Button, Panel } from '../components/common/ui'
import { MessagesList } from '../components/terminal/widgets'
import { useGame, useGameState } from '../game/GameContext'
import { api } from '../services/api'

interface Member {
  id: string; name: string; role: string; avatar: string; skills: Record<string, number>; trust: number; loyalty: number
  stress: number; performance: number; personality: string; salary_lakh: number; core: boolean
}
interface Candidate { id: string; name: string; role: string; avatar: string; skills: Record<string, number>; experience: number; loyalty: number; salary_lakh: number }
interface TeamPayload { members: Member[]; hiring_unlocked: boolean; candidates: Candidate[]; delegation: string | null; research_quality: number }

const EFFECT: Record<string, string> = {
  ceo: 'Sets targets and judges your quarter. Trust drops when you fall behind pace.',
  cfo: 'Signs off the numbers at quarterly review.',
  risk_manager: 'Approves risk exceptions (odds rise with his trust & your reputation). Flags near-limit exposure early.',
  research_director: 'Leads deep dives: fair-value accuracy and red-flag detection.',
  senior_analyst: 'Runs quick looks; weekly screen of undervalued names.',
  trader: 'Execution skill cuts market impact on large orders.',
  economist: 'Better macro forecasts in the calendar; weekly regime read.',
  compliance: 'Documentation rules for large trades; strikes hit reputation.',
  hr: 'Manages leave and headcount.',
}

export default function TeamPage() {
  const s = useGameState()
  const { run } = useGame()
  const [data, setData] = useState<TeamPayload | null>(null)
  useEffect(() => { api.get<TeamPayload>('/team').then(setData).catch(() => setData(null)) }, [s.version])
  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-2.5 p-2.5">
      <div className="col-span-12 min-h-0 overflow-y-auto lg:col-span-8">
        <div className="mb-2.5 flex items-center gap-3 px-1">
          <Users size={15} className="text-info" />
          <span className="font-display text-base font-bold">Apex Capital · Investment Management Division</span>
          {data && <Badge tone="info">Research quality {data.research_quality}</Badge>}
          <Badge tone={data?.delegation ? 'up' : 'warn'}>{data?.delegation ? `Delegation: ${data.delegation.replace('_', ' ')}` : 'No delegation at Level 1'}</Badge>
        </div>
        <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2 2xl:grid-cols-3">
          {data?.members.map((m) => (
            <div key={m.id} className="panel relative overflow-hidden p-3">
              <div className="absolute inset-x-0 top-0 h-0.5" style={{ background: accentOf(m.avatar === 'analyst' || m.avatar === 'risk' ? m.avatar : m.id) }} />
              <div className="flex items-start gap-3">
                <Avatar id={m.core ? m.id : m.avatar} size={64} />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold">{m.name}</div>
                  <div className="text-2xs uppercase tracking-wider text-txt-mute">{m.role}</div>
                  <div className="mt-1 text-2xs italic text-txt-dim">{m.personality}</div>
                </div>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
                {Object.entries(m.skills).map(([k, v]) => (
                  <div key={k}>
                    <div className="flex justify-between text-2xs"><span className="capitalize text-txt-mute">{k.replace('_', ' ')}</span><span className="num">{v}</span></div>
                    <Bar value={v} max={100} tone="info" className="mt-0.5" />
                  </div>
                ))}
              </div>
              <div className="mt-2.5 grid grid-cols-3 gap-2 border-t border-line pt-2">
                <Meter k="Trust" v={m.trust} tone={m.trust >= 55 ? 'up' : m.trust >= 35 ? 'warn' : 'down'} />
                <Meter k="Stress" v={m.stress} tone={m.stress >= 60 ? 'down' : m.stress >= 40 ? 'warn' : 'up'} />
                <Meter k="Form" v={m.performance} tone="violet" />
              </div>
              {EFFECT[m.id] && <div className="mt-2 rounded bg-ink-900 px-2 py-1 text-2xs text-txt-mute">{EFFECT[m.id]}</div>}
            </div>
          ))}
        </div>
        <Panel title="Recruitment" icon={<UserPlus size={13} />} className="mt-2.5"
          right={!data?.hiring_unlocked && <Badge tone="warn"><Lock size={10} /> Unlocks at Level 2</Badge>}>
          <div className={clsx('grid grid-cols-1 gap-2 p-3 md:grid-cols-3', !data?.hiring_unlocked && 'pointer-events-none opacity-45 blur-[0.5px]')}>
            {data?.candidates.map((c) => (
              <div key={c.id} className="rounded-md border border-line bg-ink-900 p-2.5 text-xs">
                <div className="flex items-center gap-2">
                  <Avatar id={c.avatar} size={36} />
                  <div><div className="font-semibold">{c.name}</div><div className="text-2xs text-txt-mute">{c.role} · {c.experience}y</div></div>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1">{Object.entries(c.skills).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, v]) => <Badge key={k}>{k.replace('_', ' ')} {v}</Badge>)}</div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="num text-2xs text-txt-mute">₹{c.salary_lakh}L / yr</span>
                  {data?.hiring_unlocked && (
                    <Button size="sm" variant="primary" disabled={data.members.some((m) => m.id === c.id)} onClick={() => run(() => api.hire(c.id))}>
                      {data.members.some((m) => m.id === c.id) ? 'Hired' : 'Hire'}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
          {!data?.hiring_unlocked && <div className="px-3 pb-3 text-2xs text-txt-mute">Get promoted to Investment Director to build your own research team and delegate the book while you're on leave.</div>}
        </Panel>
      </div>
      <Panel title="Inbox" icon={<Inbox size={13} />} className="col-span-12 lg:col-span-4" bodyClass="overflow-y-auto"><MessagesList limit={40} /></Panel>
    </div>
  )
}

function Meter({ k, v, tone }: { k: string; v: number; tone: 'up' | 'down' | 'warn' | 'violet' }) {
  return (
    <div>
      <div className="flex justify-between text-2xs"><span className="text-txt-mute">{k}</span><span className="num">{Math.round(v)}</span></div>
      <Bar value={v} max={100} tone={tone} className="mt-0.5" />
    </div>
  )
}
