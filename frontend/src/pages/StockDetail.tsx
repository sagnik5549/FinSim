import clsx from 'clsx'
import { Bell, CalendarClock, FileSearch, X } from 'lucide-react'
import { useState } from 'react'
import { ChartPanel } from '../components/chart/ChartPanel'
import { Badge, Bar, Empty } from '../components/common/ui'
import { LiveChange, LiveNum, MarketDepth } from '../components/market/Quote'
import { ReportCard, ThesisForm } from '../components/research/ResearchParts'
import { NewsList } from '../components/terminal/widgets'
import { useGame, useGameState } from '../game/GameContext'
import { compactVol, gameTime, hhmm, int, money, num, pct, price, toneClass } from '../game/format'
import { api } from '../services/api'
import type { SymbolDetail } from '../types/game'
import { sentimentTone } from './Markets'

type Tab = 'overview' | 'depth' | 'research' | 'news'

export default function StockDetail() {
  const s = useGameState()
  const { symbol, setModal, run } = useGame()
  const [detail, setDetail] = useState<SymbolDetail | null>(null)
  const [tab, setTab] = useState<Tab>('overview')
  const stock = s.stocks.find((x) => x.symbol === symbol)
  const idx = s.indices.find((x) => x.key === symbol)
  if (!stock && !idx) return <Empty>Pick a stock from the watchlist.</Empty>
  const d = detail?.symbol === symbol ? detail : null
  const value = stock?.price ?? idx!.value
  const prev = stock?.prev_close ?? idx!.prev_close
  const pos = stock ? s.holdings.find((h) => h.symbol === symbol) : undefined
  const job = s.research_jobs.find((j) => j.symbol === symbol)
  const orders = s.orders.filter((o) => o.symbol === symbol && (o.status === 'OPEN' || o.status === 'TRIGGERED'))
  const alerts = s.alerts.filter((a) => a.symbol === symbol && a.status === 'ACTIVE')
  const earnings = d?.calendar?.find((c) => c.kind === 'EARNINGS')
  const f = d?.fundamentals

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-x-5 gap-y-1 border-b border-line bg-ink-900 px-4 py-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[15px] font-semibold">{stock ? stock.name : idx!.name}</span>
            <span className="text-xs text-txt-mute">{stock ? `${stock.symbol} · ${stock.sector}` : 'Index'}</span>
            {pos && <Badge tone="gold">Held {pct(pos.weight, 1, false)}</Badge>}
          </div>
          <div className="flex items-baseline gap-2">
            <LiveNum symbol={symbol} value={value} decimals={symbol === 'USDINR' ? 4 : 2} className="text-xl font-semibold" />
            <LiveChange symbol={symbol} value={value} prevClose={prev} abs className="text-sm" />
          </div>
        </div>
        {stock && (
          <div className="grid grid-cols-3 gap-x-5 gap-y-0.5 text-xs sm:grid-cols-6">
            <KV k="Open" v={num(stock.open)} /><KV k="High" v={num(stock.day_high)} /><KV k="Low" v={num(stock.day_low)} />
            <KV k="Prev close" v={num(stock.prev_close)} /><KV k="Volume" v={compactVol(stock.volume)} />
            <KV k="Avg vol" v={compactVol(stock.avg_volume)} />
          </div>
        )}
        {stock && (
          <div className="ml-auto flex gap-2">
            <button className="h-8 rounded bg-info px-5 text-sm font-semibold text-white hover:bg-info/90" onClick={() => setModal({ kind: 'trade', side: 'BUY', symbol })}>Buy</button>
            <button className="h-8 rounded bg-down px-5 text-sm font-semibold text-white hover:bg-down/90 disabled:opacity-40" disabled={!pos}
              onClick={() => setModal({ kind: 'trade', side: 'SELL', symbol })}>Sell</button>
            <button className="flex h-8 items-center gap-1.5 rounded border border-line px-3 text-sm text-txt-dim hover:bg-ink-800 hover:text-txt disabled:opacity-40"
              disabled={!!job} onClick={() => setModal({ kind: 'research', symbol })}>
              <FileSearch size={14} />{job ? `Research due ${hhmm(job.ready_at)}` : 'Research'}
            </button>
          </div>
        )}
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <ChartPanel symbol={symbol} prefsKey="stock" defaultTf="5m" defaultStudies={['volume', 'sma20']} onDetail={setDetail} large />
        </div>
        {stock && (
          <aside className="hidden w-[340px] shrink-0 flex-col border-l border-line bg-ink-900 lg:flex">
            <div className="flex h-9 shrink-0 border-b border-line">
              {(['overview', 'depth', 'research', 'news'] as Tab[]).map((t) => (
                <button key={t} onClick={() => setTab(t)} className={clsx('tab flex-1 justify-center capitalize', tab === t && 'tab-on')}>{t}</button>
              ))}
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto">
              {tab === 'overview' && (
                <div className="space-y-4 p-3">
                  {pos && (
                    <Block title="Your position">
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <KV k="Qty" v={int(pos.qty)} /><KV k="Avg" v={num(pos.avg_cost)} /><KV k="Value" v={money(pos.value)} />
                        <KV k="P&L" v={money(pos.pnl, { signed: true })} tone={toneClass(pos.pnl)} /><KV k="Return" v={pct(pos.pnl_pct)} tone={toneClass(pos.pnl_pct)} /><KV k="Weight" v={pct(pos.weight, 1, false)} />
                      </div>
                    </Block>
                  )}
                  {(orders.length > 0 || alerts.length > 0) && (
                    <Block title="Working orders and alerts">
                      {orders.map((o) => (
                        <div key={o.id} className="flex items-center gap-2 py-1 text-xs">
                          <span className={o.side === 'BUY' ? 'text-info' : 'text-down'}>{o.side}</span>
                          <span className="text-txt-dim">{o.tag || o.type}</span><span className="num">{int(o.qty)}</span>
                          <span className="num ml-auto">{o.price ? num(o.price) : ''}{o.trigger ? ` trg ${num(o.trigger)}` : ''}</span>
                          <button className="text-txt-mute hover:text-down" aria-label="Cancel" onClick={() => run(() => api.cancelOrder(o.id))}><X size={13} /></button>
                        </div>
                      ))}
                      {alerts.map((a) => (
                        <div key={a.id} className="flex items-center gap-2 py-1 text-xs">
                          <Bell size={12} className="text-warn" /><span className="text-txt-dim">Alert {a.op === 'ABOVE' ? 'above' : 'below'}</span>
                          <span className="num ml-auto">{num(a.price)}</span>
                          <button className="text-txt-mute hover:text-down" aria-label="Remove" onClick={() => run(() => api.cancelAlert(a.id))}><X size={13} /></button>
                        </div>
                      ))}
                    </Block>
                  )}
                  {earnings && (
                    <div className="flex items-center gap-2 rounded border border-info/30 bg-info-soft px-2.5 py-1.5 text-xs text-info">
                      <CalendarClock size={13} /> Results due {gameTime(earnings.time)}
                    </div>
                  )}
                  <Block title="Key statistics">
                    <div className="grid grid-cols-3 gap-x-3 gap-y-2.5 text-xs">
                      <KV k="P/E" v={stock.pe ? `${stock.pe.toFixed(1)}×` : '—'} /><KV k="Market cap" v={`₹${int(stock.market_cap_cr)} Cr`} /><KV k="Beta" v={num(stock.beta)} />
                      <KV k="Volatility" v={pct(stock.volatility, 2, false)} /><KV k="1 week" v={pct(stock.week_change_pct)} tone={toneClass(stock.week_change_pct)} /><KV k="Risk" v={`${Math.round(stock.risk)}/100`} />
                      <KV k="EPS" v={f ? price(f.eps) : '—'} /><KV k="Inst. flow" v={f ? f.institutional_flow.toLowerCase() : '—'} tone={f?.institutional_flow === 'BUYING' ? 'text-up' : f?.institutional_flow === 'SELLING' ? 'text-down' : undefined} />
                      <div><div className="label">Sentiment</div><Badge tone={sentimentTone(stock.sentiment_label)}>{stock.sentiment_label.toLowerCase()}</Badge></div>
                    </div>
                  </Block>
                  {f && (
                    <Block title="Fundamentals">
                      <div className="space-y-2">
                        <FundBar k="Revenue growth" v={f.growth} max={0.35} tone="up" />
                        <FundBar k="Profitability" v={f.profitability} max={0.3} tone="info" />
                        <FundBar k="Debt / assets" v={f.debt} max={1} tone={f.debt > 0.55 ? 'down' : 'warn'} />
                        <FundBar k="Valuation (richer →)" v={f.valuation} max={1} tone={f.valuation > 0.7 ? 'warn' : 'violet'} />
                      </div>
                      <p className="mt-2 text-xs text-txt-mute">{f.about}</p>
                    </Block>
                  )}
                </div>
              )}
              {tab === 'depth' && (
                <div className="p-3">{d?.depth ? <MarketDepth depth={d.depth} /> : <Empty>Loading…</Empty>}
                  <p className="mt-3 text-2xs text-txt-mute">Simulated order book. Orders larger than a few minutes of volume move the price; your head trader's skill reduces the impact.</p>
                </div>
              )}
              {tab === 'research' && (
                <div className="space-y-3 p-3">
                  {job && <div className="rounded border border-line bg-ink-800 px-2.5 py-2 text-xs text-txt-dim">The desk is on it: {job.depth === 'DEEP' ? 'deep dive' : 'quick look'} due at {hhmm(job.ready_at)}.</div>}
                  {d?.research?.[0] ? <ReportCard r={d.research[0]} current={stock.price} /> : !job && <div className="text-xs text-txt-mute">No research on file. A quick look takes one hour of game time; the market keeps moving meanwhile.</div>}
                  <ThesisForm symbol={symbol} />
                  {d?.theses?.map((t) => (
                    <div key={t.id} className="rounded border border-line px-2.5 py-1.5 text-xs">
                      <Badge tone={t.stance === 'BULLISH' ? 'up' : t.stance === 'BEARISH' ? 'down' : 'neutral'}>{t.stance.toLowerCase()}</Badge>
                      <span className="ml-2 text-txt-dim">“{t.text}”</span>
                      <span className="num ml-2 text-2xs text-txt-mute">@ {num(t.price_at)} → <span className={toneClass(stock.price - t.price_at)}>{pct(stock.price / t.price_at - 1)}</span></span>
                    </div>
                  ))}
                </div>
              )}
              {tab === 'news' && <NewsList items={d?.news ?? []} />}
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-1.5 text-xs font-medium text-txt-dim">{title}</h3>
      {children}
    </section>
  )
}

function KV({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div className="min-w-0">
      <div className="label">{k}</div>
      <div className={clsx('num truncate', tone ?? 'text-txt')}>{v}</div>
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
