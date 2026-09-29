import clsx from 'clsx'
import { AlertOctagon, BookOpenCheck, Clock, Microscope, Search } from 'lucide-react'
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
  const { run, setModal, busy } = useGame()
  const [symbol, setSymbol] = useState(initial ?? s.stocks[0].symbol)
  const [report, setReport] = useState<ResearchReport | null>(null)
  const hours = s.clock.hours_to_close
  const open = s.clock.market_status === 'OPEN'
  const stock = s.stocks.find((x) => x.symbol === symbol)!

  const go = async (depth: 'QUICK' | 'DEEP') => {
    const r = await run<{ report: ResearchReport }>(() => api.research(symbol, depth))
    if (r?.report) setReport(r.report)
  }
  const deal = s.opportunities.find((o) => o.symbol === symbol && o.status === 'OPEN')

  return (
    <Modal onClose={() => setModal(null)} width="max-w-[620px]">
      <div className="border-b border-line bg-gradient-to-r from-info/10 px-5 py-4">
        <div className="flex items-center gap-2"><Microscope size={16} className="text-info" /><span className="font-display text-base font-bold">Research desk</span></div>
        <div className="mt-3 flex items-center gap-3">
          <select className="input font-semibold" value={symbol} onChange={(e) => { setSymbol(e.target.value); setReport(null) }}>
            {s.stocks.map((x) => <option key={x.symbol} value={x.symbol}>{x.symbol} — {x.name}</option>)}
          </select>
          <div className="shrink-0 text-right text-2xs text-txt-mute">
            <div className="flex items-center gap-1"><Clock size={11} /> now {s.clock.time}</div>
            <div className="num">{open ? `${hours}h to close` : 'market closed'}</div>
          </div>
        </div>
        {deal && <div className="mt-2 rounded border border-gold/40 bg-gold-soft px-2 py-1 text-2xs text-gold">Block deal on {symbol} expires at {deal.expires_at.slice(11, 16)} — a deep dive ends at {String(s.clock.game_hour + 3).padStart(2, '0')}:00.</div>}
      </div>
      <div className="space-y-3 px-5 py-4">
        {!report && (
          <div className="grid grid-cols-2 gap-3">
            <ResearchOption title="Quick look" hours={1} who="senior_analyst" disabled={!open || hours < 1 || busy}
              points={['Fair-value estimate (wider error)', 'Momentum, flows & balance sheet', 'Results view if reporting soon']}
              onClick={() => go('QUICK')} ends={s.clock.game_hour + 1} />
            <ResearchOption title="Deep dive" hours={3} who="research_director" disabled={!open || hours < 3 || busy}
              points={['Tighter fair-value estimate', 'Next results: beat / miss view', 'Red-flag scan (hidden risks)']}
              onClick={() => go('DEEP')} ends={s.clock.game_hour + 3} />
          </div>
        )}
        {report && <ReportCard r={report} current={stock.price} />}
        {report && <ThesisForm symbol={symbol} />}
        {report && (
          <div className="flex justify-end gap-2">
            <Button onClick={() => setReport(null)}><Search size={13} /> Research another</Button>
            <Button variant="buy" disabled={s.clock.market_status !== 'OPEN'} onClick={() => setModal({ kind: 'trade', side: 'BUY', symbol })}>Buy {symbol}</Button>
          </div>
        )}
      </div>
    </Modal>
  )
}

function ResearchOption({ title, hours, who, points, onClick, disabled, ends }: {
  title: string; hours: number; who: string; points: string[]; onClick: () => void; disabled: boolean; ends: number
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className="group rounded-lg border border-line bg-ink-900 p-3 text-left transition hover:border-info/60 hover:bg-info-soft disabled:cursor-not-allowed disabled:opacity-40">
      <div className="flex items-center gap-2">
        <Avatar id={who} size={34} />
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="num text-2xs font-bold text-warn">costs {hours}h · ready {String(Math.min(ends, 17)).padStart(2, '0')}:00</div>
        </div>
      </div>
      <ul className="mt-2 space-y-0.5 text-2xs text-txt-dim">{points.map((p) => <li key={p}>• {p}</li>)}</ul>
    </button>
  )
}
