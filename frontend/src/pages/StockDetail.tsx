import clsx from 'clsx'
import { ArrowLeft, CalendarClock, FileSearch, Newspaper } from 'lucide-react'
import { useState } from 'react'
import { Badge, Bar, Button, Change, Empty, LivePrice, Panel, Segmented } from '../components/common/ui'
import { OscillatorChart, PriceChart, type Overlay } from '../components/market/PriceChart'
import { ReportCard, ThesisForm } from '../components/research/ResearchParts'
import { NewsList } from '../components/terminal/widgets'
import { useGame, useGameState } from '../game/GameContext'
import { compactVol, gameTime, int, money, num, pct, price, toneClass } from '../game/format'
import type { SymbolDetail } from '../types/game'
import { sentimentTone } from './Markets'

export default function StockDetail() {
  const s = useGameState()
  const { symbol, setPage, setModal } = useGame()
  const [tf, setTf] = useState<'1h' | '1d'>('1h')
  const [overlays, setOverlays] = useState<Overlay[]>(['sma20', 'bb'])
  const [detail, setDetail] = useState<SymbolDetail | null>(null)
  const stock = s.stocks.find((x) => x.symbol === symbol)
  if (!stock) return <Empty>Select a stock from the Markets screener.</Empty>
  const f = detail?.symbol === symbol ? detail.fundamentals : undefined
  const pos = s.holdings.find((h) => h.symbol === symbol)
  const open = s.clock.market_status === 'OPEN'
  const atr = detail?.indicators.atr14.filter((x) => x !== null).slice(-1)[0]
  const rsi = detail?.indicators.rsi14.filter((x) => x !== null).slice(-1)[0]
  const toggle = (o: Overlay) => setOverlays((xs) => (xs.includes(o) ? xs.filter((x) => x !== o) : [...xs, o]))
  const earnings = detail?.calendar?.find((c) => c.kind === 'EARNINGS')

  return (
    <div className="grid h-full min-h-0 grid-cols-12 grid-rows-[auto_minmax(0,1fr)] gap-2.5 p-2.5">
      <div className="panel col-span-12 flex flex-wrap items-center gap-4 px-4 py-3">
        <button onClick={() => setPage('markets')} className="rounded-md p-1.5 text-txt-mute hover:bg-ink-700 hover:text-txt" aria-label="Back to markets"><ArrowLeft size={18} /></button>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-display text-xl font-bold">{stock.name}</span>
            <Badge tone="info">{stock.sector}</Badge>
            <Badge tone={sentimentTone(stock.sentiment_label)}>{stock.sentiment_label}</Badge>
            {pos && <Badge tone="gold">Held · {pct(pos.weight, 1, false)}</Badge>}
          </div>
          <div className="text-2xs text-txt-mute">{stock.symbol} · Dalal Street Exchange (simulated) · {f?.about}</div>
        </div>
        <div className="ml-4">
          <LivePrice symbol={stock.symbol} value={stock.price} className="text-2xl font-bold" />
          <div className="flex gap-2 text-xs"><Change value={stock.change_pct} className="font-semibold" /><span className="num text-txt-mute">{stock.change >= 0 ? '+' : ''}{num(stock.change)}</span></div>
        </div>
        <div className="ml-4 grid grid-cols-4 gap-x-6 text-2xs">
          <KV k="Open" v={price(stock.open)} /><KV k="Day high" v={price(stock.day_high)} /><KV k="Day low" v={price(stock.day_low)} /><KV k="Volume" v={compactVol(stock.volume)} />
        </div>
        <div className="ml-auto flex gap-2">
          <Button variant="buy" disabled={!open} onClick={() => setModal({ kind: 'trade', side: 'BUY', symbol })}>BUY</Button>
          <Button variant="sell" disabled={!open || !pos} onClick={() => setModal({ kind: 'trade', side: 'SELL', symbol })}>SELL</Button>
          <Button disabled={!open} onClick={() => setModal({ kind: 'research', symbol })}><FileSearch size={14} /> RESEARCH</Button>
        </div>
      </div>

      <div className="col-span-12 flex min-h-0 flex-col gap-2.5 xl:col-span-8">
        <Panel title="Price" className="min-h-0 flex-[3]" bodyClass="flex flex-col"
          right={<>
            {(['sma20', 'sma50', 'ema20', 'bb'] as Overlay[]).map((o) => (
              <button key={o} onClick={() => toggle(o)} className={clsx('chip !h-5 !px-2 uppercase', overlays.includes(o) && 'chip-on')}>{o}</button>
            ))}
            <Segmented value={tf} onChange={setTf} options={[{ value: '1h', label: '1H' }, { value: '1d', label: '1D' }]} />
          </>}>
          <PriceChart symbol={symbol} tf={tf} overlays={overlays} limit={tf === '1h' ? 240 : 120} onDetail={setDetail} />
        </Panel>
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-2.5">
          <Panel title={<>RSI 14 <span className="num ml-1 text-violet">{rsi !== undefined && rsi !== null ? rsi.toFixed(1) : ''}</span></>} bodyClass="h-full"><OscillatorChart detail={detail} kind="rsi" /></Panel>
          <Panel title={<>MACD 12·26·9 <span className="num ml-2 normal-case text-txt-mute">ATR14 {atr ? num(atr) : '—'}</span></>} bodyClass="h-full"><OscillatorChart detail={detail} kind="macd" /></Panel>
        </div>
      </div>

      <div className="col-span-12 flex min-h-0 flex-col gap-2.5 overflow-y-auto xl:col-span-4 [&>*]:shrink-0">
        <Panel title="Key statistics">
          <div className="grid grid-cols-3 gap-x-4 gap-y-2.5 p-3 text-xs">
            <KV k="P/E" v={stock.pe ? `${stock.pe.toFixed(1)}×` : '—'} /><KV k="Market cap" v={`₹${int(stock.market_cap_cr)} Cr`} /><KV k="Beta" v={num(stock.beta)} />
            <KV k="Volatility (d)" v={pct(stock.volatility, 2, false)} /><KV k="Momentum" v={num(stock.momentum)} tone={toneClass(stock.momentum)} /><KV k="Week" v={pct(stock.week_change_pct)} tone={toneClass(stock.week_change_pct)} />
            <KV k="Risk rating" v={`${Math.round(stock.risk)}/100`} tone={stock.risk > 65 ? 'text-down' : undefined} /><KV k="Inst. flow" v={f?.institutional_flow ?? '—'} tone={f?.institutional_flow === 'BUYING' ? 'text-up' : f?.institutional_flow === 'SELLING' ? 'text-down' : undefined} /><KV k="EPS" v={f ? price(f.eps) : '—'} />
          </div>
          {f && (
            <div className="space-y-2 border-t border-line p-3">
              <FundBar k="Revenue growth" v={f.growth} max={0.35} tone="up" />
              <FundBar k="Profitability" v={f.profitability} max={0.3} tone="info" />
              <FundBar k="Debt / assets" v={f.debt} max={1} tone={f.debt > 0.55 ? 'down' : 'warn'} />
              <FundBar k="Valuation (rich →)" v={f.valuation} max={1} tone={f.valuation > 0.7 ? 'warn' : 'violet'} />
            </div>
          )}
        </Panel>
        {pos && (
          <Panel title="Your position">
            <div className="grid grid-cols-3 gap-3 p-3 text-xs">
              <KV k="Quantity" v={int(pos.qty)} /><KV k="Avg cost" v={price(pos.avg_cost)} /><KV k="Value" v={money(pos.value)} />
              <KV k="P&L" v={money(pos.pnl, { signed: true })} tone={toneClass(pos.pnl)} /><KV k="Return" v={pct(pos.pnl_pct)} tone={toneClass(pos.pnl_pct)} /><KV k="Weight" v={pct(pos.weight, 1, false)} />
            </div>
          </Panel>
        )}
        {earnings && (
          <div className="flex items-center gap-2 rounded-lg border border-info/30 bg-info-soft px-3 py-2 text-xs text-info">
            <CalendarClock size={14} /> Quarterly results scheduled {gameTime(earnings.time)}
          </div>
        )}
        <Panel title="Research & thesis">
          <div className="space-y-2 p-3">
            {detail?.research?.[0] ? <ReportCard r={detail.research[0]} current={stock.price} /> : <div className="text-xs text-txt-mute">No research on file. A quick look costs 1 working hour.</div>}
            <ThesisForm symbol={symbol} />
            {detail?.theses?.map((t) => (
              <div key={t.id} className="rounded border border-line bg-ink-900 px-2.5 py-1.5 text-xs">
                <Badge tone={t.stance === 'BULLISH' ? 'up' : t.stance === 'BEARISH' ? 'down' : 'neutral'}>{t.stance}</Badge>
                <span className="ml-2 text-txt-dim">"{t.text}"</span>
                <span className="num ml-2 text-2xs text-txt-mute">@ {price(t.price_at)} → <span className={toneClass(stock.price - t.price_at)}>{pct(stock.price / t.price_at - 1)}</span></span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="News & events" icon={<Newspaper size={13} />} bodyClass="max-h-72 overflow-y-auto">
          <NewsList items={detail?.news ?? []} />
        </Panel>
      </div>
    </div>
  )
}

function KV({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div className="min-w-0">
      <div className="label">{k}</div>
      <div className={clsx('num truncate font-semibold', tone ?? 'text-txt')}>{v}</div>
    </div>
  )
}

function FundBar({ k, v, max, tone }: { k: string; v: number; max: number; tone: 'up' | 'down' | 'warn' | 'info' | 'violet' }) {
  return (
    <div>
      <div className="flex justify-between text-2xs"><span className="text-txt-mute">{k}</span><span className="num text-txt-dim">{pct(v, 0, false)}</span></div>
      <Bar value={v} max={max} tone={tone} className="mt-1" />
    </div>
  )
}
