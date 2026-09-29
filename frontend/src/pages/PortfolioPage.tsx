import clsx from 'clsx'
import { History, PieChart, ShieldCheck, TrendingUp, Wallet } from 'lucide-react'
import { Badge, Bar, Empty, Panel, Stat } from '../components/common/ui'
import { NavChart } from '../components/portfolio/NavChart'
import { HoldingsTable, PortfolioCard } from '../components/terminal/widgets'
import { useGameState } from '../game/GameContext'
import { gameTime, int, money, pct, price, toneClass } from '../game/format'

const SECTOR_COLORS = ['#4C8DFF', '#26D07C', '#E9B949', '#9B7BFF', '#F2728A', '#38C6E8', '#F5A524', '#8FA3BF', '#FF8A5B', '#6EE7B7', '#C084FC']

export function Donut({ parts, size = 150 }: { parts: { label: string; value: number; color: string }[]; size?: number }) {
  const total = parts.reduce((a, p) => a + p.value, 0) || 1
  const r = size / 2 - 12
  const c = 2 * Math.PI * r
  let acc = 0
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#172136" strokeWidth={16} />
      {parts.filter((p) => p.value > 0).map((p) => {
        const len = (p.value / total) * c
        const el = <circle key={p.label} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={p.color} strokeWidth={16}
          strokeDasharray={`${Math.max(0, len - 2)} ${c}`} strokeDashoffset={-acc} />
        acc += len
        return el
      })}
    </svg>
  )
}

export function RiskLimits() {
  const s = useGameState()
  const r = s.risk
  const topSector = Object.entries(r.sector_weights).sort((a, b) => b[1] - a[1])[0]
  const rows = [
    { k: 'Largest position', sub: r.largest_position.symbol ?? '—', v: r.largest_position.weight, lim: r.limits.max_single_stock },
    { k: 'Largest sector', sub: topSector?.[1] ? topSector[0] : '—', v: topSector?.[1] ?? 0, lim: r.limits.max_sector },
    { k: 'Drawdown', sub: 'from peak', v: r.drawdown, lim: r.limits.max_drawdown },
  ]
  return (
    <div className="space-y-3 p-3">
      <div className="flex items-center gap-3">
        <div className={clsx('num text-3xl font-bold', r.level === 'LOW' ? 'text-up' : r.level === 'MEDIUM' ? 'text-info' : r.level === 'HIGH' ? 'text-warn' : 'text-down')}>{Math.round(r.score)}</div>
        <div>
          <Badge tone={r.level === 'LOW' ? 'up' : r.level === 'MEDIUM' ? 'info' : r.level === 'HIGH' ? 'warn' : 'down'}>{r.level} RISK</Badge>
          <div className="mt-1 text-2xs text-txt-mute">Composite of concentration, drawdown and volatility</div>
        </div>
      </div>
      {rows.map((x) => (
        <div key={x.k}>
          <div className="flex justify-between text-xs">
            <span className="text-txt-dim">{x.k} <span className="text-txt-mute">· {x.sub}</span></span>
            <span className={clsx('num font-semibold', x.v > x.lim ? 'text-down' : x.v > x.lim * 0.85 ? 'text-warn' : 'text-txt')}>{pct(x.v, 1, false)} / {pct(x.lim, 0, false)}</span>
          </div>
          <Bar value={x.v} max={x.lim * 1.4} marker={x.lim} tone={x.v > x.lim ? 'down' : x.v > x.lim * 0.85 ? 'warn' : 'up'} className="mt-1" />
        </div>
      ))}
      <div className="grid grid-cols-3 gap-3 border-t border-line pt-3">
        <Stat label="Volatility (ann.)" value={pct(r.volatility, 1, false)} />
        <Stat label="Beta" value={r.beta.toFixed(2)} />
        <Stat label="1-day VaR 95%" value={money(r.var_95)} />
      </div>
      {r.exceptions.length > 0 && <div className="text-2xs text-warn">Active exceptions: {r.exceptions.map((e) => `${e.subject} until ${gameTime(e.until)}`).join(', ')}</div>}
    </div>
  )
}

export default function PortfolioPage() {
  const s = useGameState()
  const sectors = Object.entries(s.risk.sector_weights).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])
  const parts = [...sectors.map(([k, v], i) => ({ label: k, value: v, color: SECTOR_COLORS[i % SECTOR_COLORS.length] })),
    { label: 'Cash', value: s.risk.cash_ratio, color: '#2A3857' }]
  return (
    <div className="h-full overflow-y-auto p-2.5">
    <div className="grid grid-cols-12 gap-2.5 lg:grid-rows-[460px_minmax(360px,auto)]">
      <div className="col-span-12 flex min-h-0 flex-col gap-2.5 lg:col-span-4 [&>*]:shrink-0"><PortfolioCard />
        <Panel title="Sector allocation" icon={<PieChart size={13} />} className="!shrink min-h-0 flex-1" bodyClass="overflow-y-auto">
          <div className="flex items-center gap-4 p-3">
            <div className="relative">
              <Donut parts={parts} size={140} />
              <div className="absolute inset-0 flex flex-col items-center justify-center"><span className="label">Invested</span><span className="num text-base font-bold">{pct(s.risk.invested_ratio, 0, false)}</span></div>
            </div>
            <ul className="min-w-0 flex-1 space-y-1 text-xs">
              {parts.map((p) => (
                <li key={p.label} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />
                  <span className="truncate text-txt-dim">{p.label}</span>
                  <span className={clsx('num ml-auto', p.label !== 'Cash' && p.value > s.risk.limits.max_sector ? 'font-bold text-down' : 'text-txt')}>{pct(p.value, 1, false)}</span>
                </li>
              ))}
            </ul>
          </div>
        </Panel>
      </div>
      <Panel title="Portfolio vs benchmark (BHARAT 50, rebased)" icon={<TrendingUp size={13} />} className="col-span-12 h-[460px] lg:col-span-5" bodyClass="h-full p-1">
        {s.nav_series.length > 1 ? <NavChart series={s.nav_series} start={s.nav_series[0].nav} target={s.portfolio.target_value} /> : <Empty>Advance time to build a track record.</Empty>}
      </Panel>
      <Panel title="Risk vs firm policy" icon={<ShieldCheck size={13} />} className="col-span-12 lg:col-span-3" bodyClass="overflow-y-auto"><RiskLimits /></Panel>
      <Panel title="Holdings" icon={<Wallet size={13} />} className="col-span-12 lg:col-span-8" bodyClass="overflow-auto"><HoldingsTable /></Panel>
      <Panel title="Transaction history" icon={<History size={13} />} className="col-span-12 lg:col-span-4" bodyClass="overflow-y-auto">
        {s.transactions.length === 0 ? <Empty>No trades yet.</Empty> : (
          <table className="w-full text-xs">
            <thead className="table-head"><tr><th>Time</th><th>Side</th><th className="!text-right">Qty</th><th className="!text-right">Price</th><th className="!text-right">P&L</th></tr></thead>
            <tbody>
              {s.transactions.map((t) => (
                <tr key={t.id} className="table-row">
                  <td className="num text-2xs text-txt-mute">{gameTime(t.time)}</td>
                  <td><span className={t.side === 'BUY' ? 'font-bold text-up' : 'font-bold text-down'}>{t.side}</span> <span className="font-semibold">{t.symbol}</span>{t.source !== 'PLAYER' && <Badge className="ml-1">{t.source.replace('_', ' ')}</Badge>}</td>
                  <td className="num text-right">{int(t.qty)}</td>
                  <td className="num text-right">{price(t.price)}</td>
                  <td className={clsx('num text-right', toneClass(t.realized_pnl))}>{t.side === 'SELL' ? money(t.realized_pnl, { signed: true }) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
    </div>
  )
}
