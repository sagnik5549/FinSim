import clsx from 'clsx'
import { BookOpenCheck, Clock, FileSearch, Microscope } from 'lucide-react'
import { useState } from 'react'
import { Avatar } from '../components/common/Avatar'
import { Badge, Bar, Button, Empty, Panel } from '../components/common/ui'
import { ReportCard } from '../components/research/ResearchParts'
import { useGame, useGameState } from '../game/GameContext'
import { gameTime, pct, price, toneClass } from '../game/format'
import { sentimentTone } from './Markets'

export default function ResearchPage() {
  const s = useGameState()
  const { setModal, openSymbol } = useGame()
  const [pick, setPick] = useState(s.stocks[0].symbol)
  const stock = s.stocks.find((x) => x.symbol === pick)!
  const reports = s.research
  const open = s.clock.market_status === 'OPEN'
  const rd = s.team.find((t) => t.id === 'research_director')

  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-2.5 p-2.5">
      <Panel title="Coverage universe" icon={<FileSearch size={13} />} className="col-span-12 lg:col-span-3" bodyClass="overflow-y-auto">
        <ul>
          {s.stocks.map((x) => {
            const last = reports.find((r) => r.symbol === x.symbol)
            return (
              <li key={x.symbol}>
                <button onClick={() => setPick(x.symbol)} className={clsx('flex w-full items-center gap-2 border-b border-line/60 px-3 py-2 text-left text-xs transition hover:bg-ink-800', pick === x.symbol && 'bg-info-soft')}>
                  <span className="w-11 font-bold">{x.symbol}</span>
                  <span className="truncate text-txt-dim">{x.name}</span>
                  {last && <Badge tone={last.rating === 'BUY' ? 'up' : last.rating === 'SELL' ? 'down' : 'neutral'} className="ml-auto">{last.rating}</Badge>}
                </button>
              </li>
            )
          })}
        </ul>
      </Panel>

      <div className="col-span-12 flex min-h-0 flex-col gap-2.5 overflow-y-auto lg:col-span-5">
        <div className="panel p-4">
          <div className="flex items-center gap-3">
            <div>
              <div className="font-display text-lg font-bold">{stock.name}</div>
              <div className="text-2xs text-txt-mute">{stock.symbol} · {stock.sector}</div>
            </div>
            <div className="ml-auto text-right">
              <div className="num text-lg font-bold">{price(stock.price)}</div>
              <div className={clsx('num text-xs', toneClass(stock.change_pct))}>{pct(stock.change_pct)}</div>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-4 gap-3 text-xs">
            <div><div className="label">P/E</div><div className="num font-semibold">{stock.pe?.toFixed(1)}×</div></div>
            <div><div className="label">Momentum</div><div className={clsx('num font-semibold', toneClass(stock.momentum))}>{stock.momentum.toFixed(2)}</div></div>
            <div><div className="label">Sentiment</div><Badge tone={sentimentTone(stock.sentiment_label)}>{stock.sentiment_label}</Badge></div>
            <div><div className="label">Risk</div><div className="num font-semibold">{Math.round(stock.risk)}</div></div>
          </div>
          <div className="mt-2"><div className="label mb-1">Valuation (cheap → rich)</div><Bar value={stock.valuation} tone={stock.valuation > 0.7 ? 'warn' : 'violet'} /></div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="primary" disabled={!open} onClick={() => setModal({ kind: 'research', symbol: pick })}><Microscope size={14} /> Commission research</Button>
            <Button onClick={() => openSymbol(pick, 'stock')}>Open chart & fundamentals</Button>
          </div>
          {!open && <div className="mt-2 flex items-center gap-1 text-2xs text-warn"><Clock size={11} /> Research runs during market hours.</div>}
        </div>
        {reports.filter((r) => r.symbol === pick).map((r) => <ReportCard key={r.id} r={r} current={stock.price} />)}
        {!reports.some((r) => r.symbol === pick) && (
          <div className="panel flex items-center gap-3 p-4 text-xs text-txt-dim">
            {rd && <Avatar id="research_director" size={44} />}
            <p>"No coverage on {stock.name} yet. A quick look takes an hour of your day; a deep dive takes three but tells you what the tape won't."</p>
          </div>
        )}
      </div>

      <div className="col-span-12 flex min-h-0 flex-col gap-2.5 lg:col-span-4">
        <Panel title="Recent reports" icon={<FileSearch size={13} />} className="min-h-0 flex-1" bodyClass="overflow-y-auto">
          {reports.length === 0 ? <Empty>No reports yet.</Empty> : (
            <ul>{reports.map((r) => {
              const up = r.est_fair_value / (s.stocks.find((x) => x.symbol === r.symbol)?.price ?? r.price_at) - 1
              return (
                <li key={r.id} className="flex items-center gap-2 border-b border-line/60 px-3 py-2 text-xs">
                  <Badge tone={r.rating === 'BUY' ? 'up' : r.rating === 'SELL' ? 'down' : 'neutral'}>{r.rating}</Badge>
                  <button className="font-bold hover:text-info" onClick={() => setPick(r.symbol)}>{r.symbol}</button>
                  <span className="text-txt-mute">{r.depth === 'DEEP' ? 'deep' : 'quick'}</span>
                  {r.red_flags.length > 0 && <Badge tone="down">{r.red_flags.length} flag</Badge>}
                  <span className={clsx('num ml-auto', toneClass(up))}>{pct(up, 1)}</span>
                  <span className="num text-2xs text-txt-mute">{gameTime(r.time).slice(4, 10)}</span>
                </li>
              )
            })}</ul>
          )}
        </Panel>
        <Panel title="Thesis journal" icon={<BookOpenCheck size={13} />} className="min-h-0 flex-1" bodyClass="overflow-y-auto">
          {s.theses.length === 0 ? <Empty>Record a thesis from any research report or stock page.</Empty> : (
            <ul>{s.theses.map((t) => {
              const now = s.stocks.find((x) => x.symbol === t.symbol)?.price ?? t.price_at
              const move = now / t.price_at - 1
              const right = (t.stance === 'BULLISH' && move > 0.01) || (t.stance === 'BEARISH' && move < -0.01)
              return (
                <li key={t.id} className="border-b border-line/60 px-3 py-2 text-xs">
                  <div className="flex items-center gap-2">
                    <Badge tone={t.stance === 'BULLISH' ? 'up' : t.stance === 'BEARISH' ? 'down' : 'neutral'}>{t.stance}</Badge>
                    <span className="font-bold">{t.symbol}</span>
                    <span className={clsx('num ml-auto', toneClass(move))}>{pct(move)}</span>
                    {t.stance !== 'NEUTRAL' && <Badge tone={right ? 'up' : 'neutral'}>{right ? 'on track' : 'not yet'}</Badge>}
                  </div>
                  <div className="mt-1 text-txt-dim">"{t.text}"</div>
                </li>
              )
            })}</ul>
          )}
        </Panel>
      </div>
    </div>
  )
}
