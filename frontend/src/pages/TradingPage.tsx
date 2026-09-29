import clsx from 'clsx'
import { History, ShoppingCart, Zap } from 'lucide-react'
import { Badge, Button, Change, Empty, LivePrice, Panel } from '../components/common/ui'
import { OpportunityCards } from '../components/terminal/widgets'
import { useGame, useGameState } from '../game/GameContext'
import { gameTime, int, money, pct, price, toneClass } from '../game/format'

export default function TradingPage() {
  const s = useGameState()
  const { setModal } = useGame()
  const open = s.clock.market_status === 'OPEN'
  const past = s.opportunities.filter((o) => o.status !== 'OPEN')
  const movers = [...s.stocks].sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct)).slice(0, 8)
  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-2.5 p-2.5">
      <div className="col-span-12 flex min-h-0 flex-col gap-2.5 lg:col-span-5">
        <Panel title="Execution desk" icon={<ShoppingCart size={13} />}>
          <div className="grid grid-cols-2 gap-3 p-4">
            <button disabled={!open} onClick={() => setModal({ kind: 'trade', side: 'BUY' })}
              className="rounded-lg border border-up/40 bg-gradient-to-br from-up/20 to-transparent p-4 text-left transition hover:border-up disabled:opacity-40">
              <div className="font-display text-xl font-bold text-up">BUY</div>
              <div className="mt-1 text-xs text-txt-dim">Cash available <span className="num text-txt">{money(s.portfolio.cash)}</span></div>
            </button>
            <button disabled={!open || s.holdings.length === 0} onClick={() => setModal({ kind: 'trade', side: 'SELL', symbol: s.holdings[0]?.symbol })}
              className="rounded-lg border border-down/40 bg-gradient-to-br from-down/20 to-transparent p-4 text-left transition hover:border-down disabled:opacity-40">
              <div className="font-display text-xl font-bold text-down">SELL</div>
              <div className="mt-1 text-xs text-txt-dim">{s.holdings.length} open position{s.holdings.length === 1 ? '' : 's'}</div>
            </button>
          </div>
          <div className="border-t border-line px-4 py-2.5 text-2xs text-txt-mute">
            Market orders fill at the live price plus market impact (bigger orders relative to hourly volume move the price more; your Head Trader's skill reduces it).
            Fees 0.02% · sell-side transaction tax 0.1%. {open ? `${s.clock.hours_to_close}h until the close.` : 'Market closed — orders resume at 09:00.'}
          </div>
        </Panel>
        <Panel title="Block deals · time-limited" icon={<Zap size={13} />} className="min-h-0 flex-1" bodyClass="overflow-y-auto p-3">
          {s.opportunities.some((o) => o.status === 'OPEN') ? <OpportunityCards /> : <Empty>No live block deals. Sellers approach the desk during market hours — offers expire within hours.</Empty>}
          {past.length > 0 && (
            <div className="mt-3">
              <div className="label mb-1">Earlier offers</div>
              {past.map((o) => (
                <div key={o.id} className="flex items-center gap-2 border-b border-line/60 py-1.5 text-xs">
                  <span className="font-bold">{o.symbol}</span>
                  <span className="text-txt-mute">{int(o.qty)} @ {price(o.price)}</span>
                  <Badge tone={o.status === 'ACCEPTED' ? 'up' : o.status === 'EXPIRED' ? 'warn' : 'neutral'} className="ml-auto">{o.status}</Badge>
                  <span className={clsx('num w-16 text-right', toneClass(o.market_price - o.price))}>{pct(o.market_price / o.price - 1, 1)}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
      <Panel title="Top movers today" className="col-span-12 lg:col-span-3" bodyClass="overflow-y-auto">
        <ul>
          {movers.map((m) => (
            <li key={m.symbol} className="flex items-center gap-2 border-b border-line/60 px-3 py-2 text-xs">
              <span className="w-12 font-bold">{m.symbol}</span>
              <LivePrice symbol={m.symbol} value={m.price} className="text-txt-dim" />
              <Change value={m.change_pct} className="ml-auto font-semibold" />
              <Button size="sm" variant="subtle" disabled={!open} onClick={() => setModal({ kind: 'trade', side: 'BUY', symbol: m.symbol })}>Trade</Button>
            </li>
          ))}
        </ul>
      </Panel>
      <Panel title="Blotter" icon={<History size={13} />} className="col-span-12 lg:col-span-4" bodyClass="overflow-y-auto">
        {s.transactions.length === 0 ? <Empty>No executions yet.</Empty> : (
          <table className="w-full text-xs">
            <thead className="table-head"><tr><th>Time</th><th>Order</th><th className="!text-right">Value</th><th className="!text-right">Fee</th></tr></thead>
            <tbody>{s.transactions.map((t) => (
              <tr key={t.id} className="table-row">
                <td className="num text-2xs text-txt-mute">{gameTime(t.time)}</td>
                <td><span className={t.side === 'BUY' ? 'font-bold text-up' : 'font-bold text-down'}>{t.side}</span> {int(t.qty)} <b>{t.symbol}</b> @ {price(t.price)}</td>
                <td className="num text-right">{money(t.value)}</td>
                <td className="num text-right text-txt-mute">{money(t.fee)}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </Panel>
    </div>
  )
}
