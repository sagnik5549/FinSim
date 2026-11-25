import clsx from 'clsx'
import { AlertOctagon, BookOpenCheck, Clock, Microscope } from 'lucide-react'
import { useState } from 'react'
import { useGame, useGameState } from '../../game/GameContext'
import { gameTime, pct, price } from '../../game/format'
import { api } from '../../services/api'
import type { ResearchReport } from '../../types/game'
import { Avatar } from '../common/Avatar'
import { Badge, Button, Modal, Segmented } from '../common/ui'

export function ReportCard({ r, current }: { r: ResearchReport; current?: number }) {
  const upside = r.est_fair_value / (current ?? r.price_at) - 1
  const tone = r.rating === 'BUY' ? 'up' : r.rating === 'SELL' ? 'down' : 'neutral'
  return (
    <div className="rounded-lg border border-line bg-ink-900 p-3">
      <div className="flex items-center gap-2">
        <Avatar id={r.depth === 'DEEP' ? 'research_director' : 'senior_analyst'} size={30} />
        <div className="min-w-0">
          <div className="text-xs font-semibold">{r.symbol} · {r.depth === 'DEEP' ? 'Deep dive' : 'Quick look'}</div>
          <div className="text-2xs text-txt-mute">{r.analyst} · {gameTime(r.time)}</div>
        </div>
        <Badge tone={tone} className="ml-auto !text-xs">{r.rating}</Badge>
      </div>
      <div className="mt-2.5 grid grid-cols-3 gap-2 text-center">
        <div className="rounded bg-ink-800 py-1.5"><div className="label">Est. fair value</div><div className="num text-sm font-semibold">{price(r.est_fair_value)}</div></div>
        <div className="rounded bg-ink-800 py-1.5"><div className="label">Upside</div><div className={clsx('num text-sm font-semibold', upside >= 0 ? 'text-up' : 'text-down')}>{pct(upside, 1)}</div></div>
        <div className="rounded bg-ink-800 py-1.5"><div className="label">Confidence</div><div className="num text-sm font-semibold">{Math.round(r.confidence * 100)}%</div></div>
      </div>
      <ul className="mt-2.5 space-y-1 text-xs text-txt-dim">
        {r.notes.map((n, i) => <li key={i}>• {n}</li>)}
      </ul>
      {r.earnings_view && <div className="mt-2 rounded border border-info/30 bg-info-soft px-2 py-1 text-2xs text-info">{r.earnings_view}</div>}
      {r.red_flags.map((f, i) => (
        <div key={i} className="mt-2 flex items-start gap-1.5 rounded border border-down/40 bg-down-soft px-2 py-1 text-2xs font-semibold text-down">
          <AlertOctagon size={12} className="mt-px shrink-0" /> RED FLAG: {f}
        </div>
      ))}
      <div className="mt-2 text-[10px] text-txt-mute">Research is an estimate, not a guarantee. Price when written: {price(r.price_at)}.</div>
    </div>
  )
}

export function ThesisForm({ symbol }: { symbol: string }) {
  const { run, busy } = useGame()
  const [stance, setStance] = useState<'BULLISH' | 'BEARISH' | 'NEUTRAL'>('BULLISH')
  const [text, setText] = useState('')
  const [saved, setSaved] = useState(false)
  return (
    <div className="rounded-lg border border-line bg-ink-900 p-3">
      <div className="flex items-center gap-2">
        <BookOpenCheck size={14} className="text-violet" />
        <span className="label">Investment thesis · {symbol}</span>
        <div className="ml-auto">
          <Segmented value={stance} onChange={setStance} options={[
            { value: 'BULLISH', label: <span className="text-up">BULLISH</span> },
            { value: 'NEUTRAL', label: 'NEUTRAL' },
            { value: 'BEARISH', label: <span className="text-down">BEARISH</span> },
          ]} />
        </div>
      </div>
      <textarea className="input mt-2 h-16 resize-none py-2" maxLength={500} placeholder={stance === 'BEARISH' ? '"Valuation appears excessive."' : '"Strong growth and improving fundamentals."'}
        value={text} onChange={(e) => { setText(e.target.value); setSaved(false) }} />
      <div className="mt-2 flex items-center justify-between">
        <span className="text-2xs text-txt-mute">Theses are scored for decision quality at your quarterly review.</span>
        <Button size="sm" variant="primary" disabled={busy || text.trim().length < 3}
          onClick={async () => { const r = await run(() => api.thesis(symbol, stance, text.trim())); if (r) { setSaved(true); setText('') } }}>
          {saved ? 'Recorded ✓' : 'Record thesis'}
        </Button>
      </div>
    </div>
  )
}

export function ResearchModal({ symbol: initial }: { symbol?: string }) {
  const s = useGameState()
  const { run, setModal, busy, toast } = useGame()
  const [symbol, setSymbol] = useState(initial ?? s.stocks[0].symbol)
  const mins = s.clock.minutes_to_close
  const open = s.clock.market_status === 'OPEN'
  const job = s.research_jobs.find((j) => j.symbol === symbol)
  const latest = s.research.find((r) => r.symbol === symbol)
  const stock = s.stocks.find((x) => x.symbol === symbol)!
  const ready = (h: number) => {
    const t = s.clock.game_hour * 60 + s.clock.game_minute + h * 60
    return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`
  }

  const go = async (depth: 'QUICK' | 'DEEP') => {
    const r = await run(() => api.research(symbol, depth))
    if (r?.job) {
      toast({ kind: 'info', title: 'Research started', body: `${symbol} ${depth === 'DEEP' ? 'deep dive' : 'quick look'} due at ${r.job.ready_at.slice(11, 16)}. The market keeps moving meanwhile.` })
      setModal(null)
    }
  }
  const deal = s.opportunities.find((o) => o.symbol === symbol && o.status === 'OPEN')

  return (
    <Modal onClose={() => setModal(null)} width="max-w-[620px]">
      <div className="border-b border-line px-5 py-4">
        <div className="flex items-center gap-2"><Microscope size={16} className="text-info" /><span className="text-base font-semibold">Research desk</span></div>
        <div className="mt-3 flex items-center gap-3">
          <select className="input font-medium" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {s.stocks.map((x) => <option key={x.symbol} value={x.symbol}>{x.symbol} · {x.name}</option>)}
          </select>
          <div className="shrink-0 text-right text-2xs text-txt-mute">
            <div className="flex items-center gap-1"><Clock size={11} /> now {s.clock.time}</div>
            <div className="num">{open ? `${Math.floor(mins / 60)}h ${mins % 60}m to close` : 'market closed'}</div>
          </div>
        </div>
        {deal && <div className="mt-2 rounded border border-gold/40 bg-gold-soft px-2 py-1 text-2xs text-gold">Block deal on {symbol} expires at {deal.expires_at.slice(11, 16)}. A deep dive would be ready at {ready(3)}.</div>}
      </div>
      <div className="space-y-3 px-5 py-4">
        {job ? (
          <div className="rounded border border-line bg-ink-800 px-3 py-2.5 text-xs text-txt-dim">
            The desk is already working on {symbol}: {job.depth === 'DEEP' ? 'deep dive' : 'quick look'} due at {job.ready_at.slice(11, 16)}.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <ResearchOption title="Quick look" hours={1} who="senior_analyst" disabled={!open || mins < 60 || busy}
              points={['Fair-value estimate (wider error)', 'Momentum, flows and balance sheet', 'Results view if reporting soon']}
              onClick={() => go('QUICK')} ends={ready(1)} />
            <ResearchOption title="Deep dive" hours={3} who="research_director" disabled={!open || mins < 180 || busy}
              points={['Tighter fair-value estimate', 'Next results: beat or miss view', 'Red-flag scan (hidden risks)']}
              onClick={() => go('DEEP')} ends={ready(3)} />
          </div>
        )}
        <p className="text-2xs text-txt-mute">Analysts work in game time while the market keeps trading. You get a notification when the report is ready.</p>
        {latest && <><div className="label">Latest report on file</div><ReportCard r={latest} current={stock.price} /></>}
        <ThesisForm symbol={symbol} />
        <div className="flex justify-end gap-2">
          <Button variant="buy" onClick={() => setModal({ kind: 'trade', side: 'BUY', symbol })}>Buy {symbol}</Button>
        </div>
      </div>
    </Modal>
  )
}

function ResearchOption({ title, hours, who, points, onClick, disabled, ends }: {
  title: string; hours: number; who: string; points: string[]; onClick: () => void; disabled: boolean; ends: string
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className="group rounded-md border border-line bg-ink-900 p-3 text-left transition-colors hover:border-info/60 hover:bg-info-soft disabled:cursor-not-allowed disabled:opacity-40">
      <div className="flex items-center gap-2">
        <Avatar id={who} size={34} />
        <div>
          <div className="text-sm font-medium">{title}</div>
          <div className="num text-2xs text-txt-mute">takes {hours}h · ready {ends}</div>
        </div>
      </div>
      <ul className="mt-2 space-y-0.5 text-2xs text-txt-dim">{points.map((p) => <li key={p}>• {p}</li>)}</ul>
    </button>
  )
}
