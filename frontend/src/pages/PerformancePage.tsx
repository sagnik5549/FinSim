import clsx from 'clsx'
import { BarChart3, Target, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Badge, Empty, Panel, Stat } from '../components/common/ui'
import { NavChart } from '../components/portfolio/NavChart'
import { useGameState } from '../game/GameContext'
import { money, pct, toneClass } from '../game/format'
import { api } from '../services/api'
import type { NavPoint } from '../types/game'

interface Trade { symbol: string; pnl: number; pct: number; t: string }
interface Perf {
  portfolio_return: number; benchmark_return: number; alpha: number; max_drawdown: number; risk_score: number; volatility: number
  sharpe: number | null; win_rate: number | null; average_trade: number | null; best_trade: Trade | null; worst_trade: Trade | null
  closed_trades: number; fees_paid: number; sector_attribution: Record<string, number>
  monthly: { month: string; return: number; benchmark: number }[]
  quarterly: { quarter: number; outcome: string; return_pct: number; target_pct: number; max_drawdown: number }[]
  target: { target: number; actual: number; difference: number; target_return: number; actual_return: number }
  nav_series: NavPoint[]
}

export default function PerformancePage() {
  const s = useGameState()
  const [p, setP] = useState<Perf | null>(null)
  useEffect(() => { api.get<Perf>('/performance').then(setP).catch(() => setP(null)) }, [s.version])
  if (!p) return <Empty>Loading performance…</Empty>
  const attr = Object.entries(p.sector_attribution)
  const maxAbs = Math.max(1, ...attr.map(([, v]) => Math.abs(v)))
  return (
    <div className="grid h-full min-h-0 grid-cols-12 grid-rows-[auto_minmax(0,1fr)_minmax(0,0.8fr)] gap-2.5 overflow-y-auto p-2.5">
      <div className="panel col-span-12 grid grid-cols-2 gap-4 p-4 md:grid-cols-5 xl:grid-cols-10">
        <Stat label="Portfolio return" value={<span className={toneClass(p.portfolio_return)}>{pct(p.portfolio_return)}</span>} />
        <Stat label="Benchmark" value={<span className={toneClass(p.benchmark_return)}>{pct(p.benchmark_return)}</span>} sub="BHARAT 50" />
        <Stat label="Alpha" value={<span className={toneClass(p.alpha)}>{pct(p.alpha)}</span>} />
        <Stat label="Max drawdown" value={pct(p.max_drawdown, 2, false)} />
        <Stat label="Risk score" value={Math.round(p.risk_score)} />
        <Stat label="Sharpe (ann.)" value={p.sharpe === null ? '—' : p.sharpe.toFixed(2)} />
        <Stat label="Win rate" value={p.win_rate === null ? '—' : pct(p.win_rate, 0, false)} sub={`${p.closed_trades} closed`} />
        <Stat label="Average trade" value={p.average_trade === null ? '—' : <span className={toneClass(p.average_trade)}>{money(p.average_trade, { signed: true })}</span>} />
        <Stat label="Best trade" value={p.best_trade ? <span className="text-up">{money(p.best_trade.pnl, { signed: true })}</span> : '—'} sub={p.best_trade?.symbol} />
        <Stat label="Worst trade" value={p.worst_trade ? <span className={toneClass(p.worst_trade.pnl)}>{money(p.worst_trade.pnl, { signed: true })}</span> : '—'} sub={p.worst_trade?.symbol} />
      </div>

      <Panel title="Equity curve vs benchmark" icon={<TrendingUp size={13} />} className="col-span-12 lg:col-span-8" bodyClass="h-full p-1">
        {p.nav_series.length > 1 ? <NavChart series={p.nav_series} start={p.nav_series[0].nav} target={p.target.target} /> : <Empty>No history yet.</Empty>}
      </Panel>
      <Panel title="Target vs actual" icon={<Target size={13} />} className="col-span-12 lg:col-span-4">
        <div className="grid grid-cols-3 gap-px bg-line">
          {[['Target', money(p.target.target), pct(p.target.target_return, 0)], ['Actual', money(p.target.actual), pct(p.target.actual_return)], ['Difference', money(p.target.difference, { signed: true }), '']].map(([k, v, sub]) => (
            <div key={k} className="bg-ink-850 px-3 py-4 text-center">
              <div className="label">{k}</div>
              <div className={clsx('num mt-1 text-lg font-bold', k === 'Difference' && toneClass(p.target.difference), k === 'Target' && 'text-gold')}>{v}</div>
              <div className="num text-2xs text-txt-mute">{sub}</div>
            </div>
          ))}
        </div>
        <div className="p-3">
          <div className="label mb-2">Quarterly performance</div>
          {p.quarterly.length === 0 ? <div className="text-xs text-txt-mute">First review pending.</div> : p.quarterly.map((q) => (
            <div key={q.quarter} className="flex items-center gap-2 border-b border-line/60 py-1.5 text-xs">
              <span className="num">Q{q.quarter}</span><Badge tone={q.outcome === 'PROMOTED' ? 'gold' : q.outcome === 'WARNING' ? 'warn' : q.outcome.includes('ACHIEVED') ? 'up' : 'down'}>{q.outcome}</Badge>
              <span className={clsx('num ml-auto', toneClass(q.return_pct))}>{pct(q.return_pct)}</span>
            </div>
          ))}
          <div className="mt-2 text-2xs text-txt-mute">Fees paid this career: {money(p.fees_paid)}</div>
        </div>
      </Panel>

      <Panel title="Sector attribution (P&L this quarter)" icon={<BarChart3 size={13} />} className="col-span-12 lg:col-span-7" bodyClass="overflow-y-auto">
        {attr.length === 0 ? <Empty>Attribution appears once you hold positions.</Empty> : (
          <div className="space-y-1.5 p-3">
            {attr.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[120px_1fr_90px] items-center gap-2 text-xs">
                <span className="truncate text-txt-dim">{k}</span>
                <div className="relative h-3 rounded bg-ink-800">
                  <div className="absolute top-0 h-3 w-px bg-line" style={{ left: '50%' }} />
                  <div className={clsx('absolute top-0 h-3 rounded', v >= 0 ? 'bg-up/70' : 'bg-down/70')}
                    style={v >= 0 ? { left: '50%', width: `${(v / maxAbs) * 50}%` } : { right: '50%', width: `${(-v / maxAbs) * 50}%` }} />
                </div>
                <span className={clsx('num text-right', toneClass(v))}>{money(v, { signed: true })}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Monthly performance" className="col-span-12 lg:col-span-5" bodyClass="overflow-y-auto">
        {p.monthly.length === 0 ? <Empty>First month in progress.</Empty> : (
          <table className="w-full text-xs">
            <thead className="table-head"><tr><th>Month</th><th className="!text-right">Portfolio</th><th className="!text-right">Benchmark</th><th className="!text-right">Excess</th></tr></thead>
            <tbody>{p.monthly.map((m) => (
              <tr key={m.month} className="table-row">
                <td className="num">{m.month}</td>
                <td className={clsx('num text-right', toneClass(m.return))}>{pct(m.return)}</td>
                <td className={clsx('num text-right', toneClass(m.benchmark))}>{pct(m.benchmark)}</td>
                <td className={clsx('num text-right font-semibold', toneClass(m.return - m.benchmark))}>{pct(m.return - m.benchmark)}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </Panel>
    </div>
  )
}
