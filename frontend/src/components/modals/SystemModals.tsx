import clsx from 'clsx'
import { Download, Palmtree, RotateCcw, Save, ShieldAlert, Upload } from 'lucide-react'
import { useEffect, useState } from 'react'
import { LIVE_SPEEDS, useGame, useGameState } from '../../game/GameContext'
import { gameTime, money } from '../../game/format'
import { api } from '../../services/api'
import type { SaveSlot } from '../../types/game'
import { Avatar } from '../common/Avatar'
import { Badge, Button, Modal } from '../common/ui'

export function LeaveModal() {
  const s = useGameState()
  const { run, setModal, busy } = useGame()
  const [days, setDays] = useState(1)
  const [custom, setCustom] = useState('')
  const n = custom ? Number(custom) : days
  const valid = Number.isInteger(n) && n >= 1 && n <= Math.min(30, s.leave.remaining)
  const delegate = s.career.delegate
  const blocked = s.popups.some((p) => p.blocking)
  return (
    <Modal onClose={() => setModal(null)} width="max-w-[520px]">
      <div className="flex items-center gap-4 border-b border-line bg-gradient-to-r from-violet/15 px-5 py-4">
        <Avatar id="hr" size={52} />
        <div>
          <div className="font-display text-base font-bold">Request paid leave</div>
          <div className="text-xs text-txt-dim">"The market won't stop while you're away. Plan for it."</div>
        </div>
      </div>
      <div className="space-y-4 px-5 py-4">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-md border border-line bg-ink-900 py-2"><div className="label">Allowance</div><div className="num text-lg font-bold">{s.leave.allowance}</div></div>
          <div className="rounded-md border border-line bg-ink-900 py-2"><div className="label">Used</div><div className="num text-lg font-bold">{s.leave.used}</div></div>
          <div className="rounded-md border border-violet/40 bg-violet-soft py-2"><div className="label !text-violet">Remaining</div><div className="num text-lg font-bold text-violet">{s.leave.remaining}</div></div>
        </div>
        <div>
          <div className="label mb-1.5">Duration (business days)</div>
          <div className="flex flex-wrap gap-2">
            {[1, 3, 5].map((d) => (
              <button key={d} onClick={() => { setDays(d); setCustom('') }} className={clsx('chip !h-8 !px-4 !text-xs', !custom && days === d && 'chip-on')}>{d} day{d > 1 ? 's' : ''}</button>
            ))}
            <input className="input !h-8 w-28" placeholder="Custom" inputMode="numeric" value={custom} onChange={(e) => setCustom(e.target.value.replace(/\D/g, ''))} />
          </div>
          <p className="mt-2 text-2xs text-txt-mute">
            {s.clock.game_hour === 9 && s.clock.market_status === 'OPEN' ? 'Leave starts today at the open.' : 'The rest of today passes as you hand over the desk; leave starts next business day.'} Weekends don't count.
          </p>
        </div>
        <div className={clsx('flex items-start gap-2 rounded-md border px-3 py-2 text-xs', delegate ? 'border-info/30 bg-info-soft text-info' : 'border-warn/30 bg-warn-soft text-warn')}>
          <ShieldAlert size={14} className="mt-0.5 shrink-0" />
          {delegate
            ? <span>Your {delegate.replace('_', ' ')} will run stop-losses (−10%) and trim policy breaches while you're away.</span>
            : <span>At Level 1 you have no dedicated portfolio manager. Your {s.holdings.length} position{s.holdings.length === 1 ? '' : 's'} ({money(s.portfolio.invested)}) will be left untouched while markets, news and events continue.</span>}
        </div>
        <div className="flex gap-2">
          <Button className="flex-1" onClick={() => setModal(null)}>Stay at the desk</Button>
          <Button className="flex-[2]" variant="primary" disabled={!valid || busy || blocked || s.career.status !== 'ACTIVE'}
            onClick={async () => { const r = await run(() => api.takeLeave(n)); if (r) setModal(null) }}>
            <Palmtree size={15} /> Take {valid ? n : '—'} day{n === 1 ? '' : 's'} off
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export function SavesModal() {
  const s = useGameState()
  const { setModal, replaceState, toast } = useGame()
  const [slots, setSlots] = useState<SaveSlot[] | null>(null)
  const [name, setName] = useState(`Q${s.career.quarter_index} · ${s.clock.label} ${s.clock.time}`)
  const [working, setWorking] = useState(false)
  const load = () => api.saves().then(setSlots).catch(() => setSlots([]))
  useEffect(() => { load() }, [])
  return (
    <Modal onClose={() => setModal(null)} width="max-w-[560px]">
      <div className="border-b border-line px-5 py-4">
        <div className="font-display text-base font-bold">Save / Load</div>
        <div className="text-xs text-txt-mute">Your career autosaves after every action. Named saves let you return to a moment.</div>
      </div>
      <div className="space-y-4 px-5 py-4">
        <div className="flex gap-2">
          <input className="input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
          <Button variant="primary" disabled={working} onClick={async () => {
            setWorking(true)
            try { await api.save(name); toast({ kind: 'success', title: 'Game saved', body: name }); await load() } finally { setWorking(false) }
          }}><Save size={14} /> Save</Button>
        </div>
        <div className="max-h-[320px] space-y-1.5 overflow-y-auto">
          {slots === null && <div className="text-xs text-txt-mute">Loading…</div>}
          {slots?.length === 0 && <div className="text-xs text-txt-mute">No named saves yet.</div>}
          {slots?.map((sl) => (
            <div key={sl.id} className="flex items-center gap-3 rounded-md border border-line bg-ink-900 px-3 py-2">
              <Download size={14} className="text-txt-mute" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-semibold">{sl.name}</div>
                <div className="text-2xs text-txt-mute">{sl.summary.date} · L{sl.summary.level} {sl.summary.title} · {money(sl.summary.nav)}</div>
              </div>
              <Button size="sm" disabled={working} onClick={async () => {
                setWorking(true)
                try {
                  const r = await api.load(sl.id)
                  replaceState(r.state)
                  toast({ kind: 'success', title: 'Game loaded', body: sl.name })
                  setModal(null)
                } catch { toast({ kind: 'error', title: 'Load failed' }) } finally { setWorking(false) }
              }}><Upload size={12} /> Load</Button>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  )
}

export function SettingsModal() {
  const s = useGameState()
  const { setModal, speed, setSpeed, restart } = useGame()
  const [confirm, setConfirm] = useState(false)
  return (
    <Modal onClose={() => setModal(null)} width="max-w-[480px]">
      <div className="border-b border-line px-5 py-4 font-display text-base font-bold">Settings</div>
      <div className="space-y-4 px-5 py-4 text-xs">
        <div>
          <div className="label mb-1.5">Live mode speed (real seconds per game hour)</div>
          <div className="flex gap-2">
            {LIVE_SPEEDS.map((sp, i) => (
              <button key={sp.label} onClick={() => setSpeed(i)} className={clsx('chip !h-8 !px-4', speed === i && 'chip-on')}>{sp.label} · {sp.ms / 1000}s</button>
            ))}
          </div>
        </div>
        <div className="rounded-md border border-line bg-ink-900 p-3 text-txt-dim">
          <div className="flex justify-between"><span>Career seed</span><span className="num text-txt">{s.seed}</span></div>
          <div className="flex justify-between"><span>Game ID</span><span className="num text-txt">{s.game_id}</span></div>
          <div className="flex justify-between"><span>Started</span><span className="num text-txt">{gameTime(s.career.quarter_start)}</span></div>
        </div>
        <p className="leading-relaxed text-txt-mute">
          Investment Banker Mode is a simulation game. Every company, index, price, person and event is fictional and
          generated by the game. Nothing here is financial advice or real market data.
        </p>
        {!confirm ? (
          <Button variant="warn" onClick={() => setConfirm(true)}><RotateCcw size={14} /> Restart career</Button>
        ) : (
          <div className="flex items-center gap-2 rounded-md border border-down/40 bg-down-soft p-2">
            <span className="flex-1 text-down">Abandon this career and return to the title screen? (Saves are kept.)</span>
            <Button size="sm" onClick={() => setConfirm(false)}>Cancel</Button>
            <Button size="sm" variant="sell" onClick={restart}>Restart</Button>
          </div>
        )}
      </div>
    </Modal>
  )
}

export function ToastHost() {
  const { toasts, dismissToast } = useGame()
  return (
    <div className="pointer-events-none fixed bottom-12 right-4 z-[60] flex w-80 flex-col gap-2">
      {toasts.map((t) => (
        <button key={t.id} onClick={() => dismissToast(t.id)}
          className={clsx('pointer-events-auto panel animate-fadeIn px-3 py-2 text-left',
            t.kind === 'error' ? 'border-down/50' : t.kind === 'success' ? 'border-up/50' : 'border-info/50')}>
          <div className={clsx('text-2xs font-bold uppercase tracking-wider', t.kind === 'error' ? 'text-down' : t.kind === 'success' ? 'text-up' : 'text-info')}>{t.title}</div>
          {t.body && <div className="mt-0.5 text-xs text-txt-dim">{t.body}</div>}
        </button>
      ))}
    </div>
  )
}

export function Speaker({ id, name, role, line, tone }: { id: string; name: string; role: string; line: string; tone?: string }) {
  return (
    <div className="flex items-start gap-3">
      <Avatar id={id} size={46} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2"><span className="text-xs font-bold">{name}</span><Badge>{role}</Badge></div>
        <div className={clsx('mt-1 rounded-lg rounded-tl-none border border-line bg-ink-900 px-3 py-2 text-[13px] leading-relaxed', tone)}>"{line}"</div>
      </div>
    </div>
  )
}
