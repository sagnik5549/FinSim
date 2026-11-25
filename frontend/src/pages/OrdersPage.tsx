import clsx from 'clsx'
import { Check, Pencil, X } from 'lucide-react'
import { useState } from 'react'
import { Badge, Empty } from '../components/common/ui'
import { LiveNum } from '../components/market/Quote'
import { OpportunityCards } from '../components/terminal/widgets'
import { useGame, useGameState } from '../game/GameContext'
import { gameTime, hhmm, int, money, num, pct, toneClass } from '../game/format'
import { api } from '../services/api'
import type { Order } from '../types/game'

type Tab = 'open' | 'history' | 'trades' | 'alerts' | 'deals'

const STATUS_TONE: Record<string, 'up' | 'down' | 'warn' | 'info' | 'neutral'> = {
  OPEN: 'info', TRIGGERED: 'warn', EXECUTED: 'up', CANCELLED: 'neutral', REJECTED: 'down', EXPIRED: 'neutral',
}

export default function OrdersPage() {
  const s = useGameState()
  const [tab, setTab] = useState<Tab>('open')
  const open = s.orders.filter((o) => o.status === 'OPEN' || o.status === 'TRIGGERED')
  const history = s.orders.filter((o) => o.status !== 'OPEN' && o.status !== 'TRIGGERED')
  const alerts = s.alerts
  const deals = s.opportunities.filter((o) => o.status === 'OPEN').length
  const tabs: { id: Tab; label: string; n?: number }[] = [
    { id: 'open', label: 'Open orders', n: open.length },
    { id: 'history', label: 'Order history', n: history.length },
    { id: 'trades', label: 'Trade book', n: s.transactions.length },
    { id: 'alerts', label: 'Alerts', n: alerts.filter((a) => a.status === 'ACTIVE').length },
    { id: 'deals', label: 'Block deals', n: deals },
  ]
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-10 shrink-0 items-stretch border-b border-line bg-ink-900 px-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={clsx('tab', tab === t.id && 'tab-on')}>
            {t.label}{t.n ? <span className="num ml-1.5 text-txt-mute">{t.n}</span> : null}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {tab === 'open' && <OpenOrders orders={open} />}
        {tab === 'history' && <History orders={history} />}
        {tab === 'trades' && <Trades />}
        {tab === 'alerts' && <Alerts />}
        {tab === 'deals' && (
          <div className="max-w-3xl p-4">
            {deals ? <OpportunityCards /> : <Empty>No block deals on offer. Sellers approach the desk during market hours; offers expire within hours.</Empty>}
          </div>
        )}
      </div>
    </div>
  )
}

function OpenOrders({ orders }: { orders: Order[] }) {
  const { run } = useGame()
  const [edit, setEdit] = useState<{ id: string; qty: string; price: string; trigger: string } | null>(null)
  if (!orders.length) {
    return <Empty>No open orders. Place limit or stop orders from the order pad, or click “Buy at” / “Sell at” on a chart.</Empty>
  }
  const save = async () => {
    if (!edit) return
    const o = orders.find((x) => x.id === edit.id)!
    const m: { quantity?: number; price?: number; trigger?: number } = {}
    if (Number(edit.qty) !== o.qty) m.quantity = Number(edit.qty)
    if (o.price !== null && Number(edit.price) !== o.price) m.price = Number(edit.price)
    if (o.trigger !== null && Number(edit.trigger) !== o.trigger) m.trigger = Number(edit.trigger)
    const r = await run(() => api.modifyOrder(o.id, m))
    if (r) setEdit(null)
  }
  return (
    <table className="w-full text-xs">
      <thead className="table-head">
        <tr><th>Time</th><th>Type</th><th>Instrument</th><th className="!text-right">Qty</th><th className="!text-right">Price</th>
          <th className="!text-right">Trigger</th><th className="!text-right">LTP</th><th>Validity</th><th>Status</th><th /></tr>
      </thead>
      <tbody>
        {orders.map((o) => {
          const editing = edit?.id === o.id
          return (
            <tr key={o.id} className="table-row">
              <td className="num text-txt-mute">{hhmm(o.created)}</td>
              <td><span className={clsx('rounded px-1.5 py-0.5 text-2xs font-semibold', o.side === 'BUY' ? 'bg-info-soft text-info' : 'bg-down-soft text-down')}>{o.side}</span></td>
              <td><span className="font-medium">{o.symbol}</span> <span className="text-txt-mute">{o.tag ? o.tag.toLowerCase() : o.type}</span></td>
              <td className="num text-right">{editing ? <input className="input num h-7 w-20 text-right" value={edit.qty} onChange={(e) => setEdit({ ...edit, qty: e.target.value.replace(/\D/g, '') })} /> : int(o.qty)}</td>
              <td className="num text-right">{editing && o.price !== null ? <input className="input num h-7 w-24 text-right" value={edit.price} onChange={(e) => setEdit({ ...edit, price: e.target.value })} /> : o.price !== null ? num(o.price) : '—'}</td>
              <td className="num text-right">{editing && o.trigger !== null ? <input className="input num h-7 w-24 text-right" value={edit.trigger} onChange={(e) => setEdit({ ...edit, trigger: e.target.value })} /> : o.trigger !== null ? num(o.trigger) : '—'}</td>
              <td className="text-right"><LiveNum symbol={o.symbol} value={o.ltp ?? 0} /></td>
              <td className="text-txt-dim">{o.validity}</td>
              <td><Badge tone={STATUS_TONE[o.status]}>{o.status.toLowerCase()}</Badge></td>
              <td className="whitespace-nowrap text-right">
                {editing ? (
                  <>
                    <button className="icon-btn inline-grid !h-7 !w-7 text-up" aria-label="Save" onClick={save}><Check size={14} /></button>
                    <button className="icon-btn inline-grid !h-7 !w-7" aria-label="Discard" onClick={() => setEdit(null)}><X size={14} /></button>
                  </>
                ) : (
                  <>
                    <button className="icon-btn inline-grid !h-7 !w-7" aria-label="Modify" title="Modify"
                      onClick={() => setEdit({ id: o.id, qty: String(o.qty), price: o.price?.toFixed(2) ?? '', trigger: o.trigger?.toFixed(2) ?? '' })}><Pencil size={13} /></button>
                    <button className="icon-btn inline-grid !h-7 !w-7 hover:text-down" aria-label="Cancel order" title="Cancel" onClick={() => run(() => api.cancelOrder(o.id))}><X size={14} /></button>
                  </>
                )}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function History({ orders }: { orders: Order[] }) {
  if (!orders.length) return <Empty>No completed orders yet.</Empty>
  return (
    <table className="w-full text-xs">
      <thead className="table-head">
        <tr><th>Updated</th><th>Type</th><th>Instrument</th><th className="!text-right">Qty</th><th className="!text-right">Order price</th><th className="!text-right">Avg fill</th><th>Status</th><th>Note</th></tr>
      </thead>
      <tbody>
        {orders.map((o) => (
          <tr key={o.id} className="table-row">
            <td className="num text-txt-mute">{gameTime(o.updated)}</td>
            <td><span className={o.side === 'BUY' ? 'font-semibold text-info' : 'font-semibold text-down'}>{o.side}</span></td>
            <td><span className="font-medium">{o.symbol}</span> <span className="text-txt-mute">{o.tag ? o.tag.toLowerCase() : o.type}</span></td>
            <td className="num text-right">{int(o.qty)}</td>
            <td className="num text-right">{o.price !== null ? num(o.price) : o.trigger !== null ? `trg ${num(o.trigger)}` : 'Market'}</td>
            <td className="num text-right">{o.fill_price !== null ? num(o.fill_price) : '—'}</td>
            <td><Badge tone={STATUS_TONE[o.status]}>{o.status.toLowerCase()}</Badge></td>
            <td className="max-w-[260px] truncate text-txt-mute" title={o.reason}>{o.reason}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Trades() {
  const s = useGameState()
  if (!s.transactions.length) return <Empty>No trades yet.</Empty>
  return (
    <table className="w-full text-xs">
      <thead className="table-head">
        <tr><th>Time</th><th>Side</th><th>Instrument</th><th className="!text-right">Qty</th><th className="!text-right">Price</th><th className="!text-right">Value</th><th className="!text-right">Charges</th><th className="!text-right">Realised P&L</th><th>Source</th></tr>
      </thead>
      <tbody>
        {s.transactions.map((t) => (
          <tr key={t.id} className="table-row">
            <td className="num text-txt-mute">{gameTime(t.time)}</td>
            <td><span className={t.side === 'BUY' ? 'font-semibold text-info' : 'font-semibold text-down'}>{t.side}</span></td>
            <td className="font-medium">{t.symbol}</td>
            <td className="num text-right">{int(t.qty)}</td>
            <td className="num text-right">{num(t.price)}</td>
            <td className="num text-right">{money(t.value)}</td>
            <td className="num text-right text-txt-mute">{money(t.fee)}</td>
            <td className={clsx('num text-right', toneClass(t.realized_pnl))}>{t.side === 'SELL' ? money(t.realized_pnl, { signed: true }) : '—'}</td>
            <td className="text-txt-mute">{t.source.replace('_', ' ').toLowerCase()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Alerts() {
  const s = useGameState()
  const { run } = useGame()
  const [sym, setSym] = useState(s.stocks[0].symbol)
  const [priceText, setPriceText] = useState('')
  const [note, setNote] = useState('')
  const st = s.stocks.find((x) => x.symbol === sym)
  const add = async () => {
    const p = Number(priceText)
    if (!(p > 0)) return
    const r = await run(() => api.addAlert(sym, p, note))
    if (r) {
      setPriceText('')
      setNote('')
    }
  }
  return (
    <div>
      <div className="flex flex-wrap items-end gap-2 border-b border-line p-3">
        <label><span className="label mb-1 block">Stock</span>
          <select className="input h-8 w-44" value={sym} onChange={(e) => setSym(e.target.value)}>
            {s.stocks.map((x) => <option key={x.symbol} value={x.symbol}>{x.symbol} · {x.name}</option>)}
          </select>
        </label>
        <label><span className="label mb-1 block">Alert price {st && <span className="text-txt-mute">(LTP {num(st.price)})</span>}</span>
          <input className="input num h-8 w-32" inputMode="decimal" value={priceText} onChange={(e) => setPriceText(e.target.value.replace(/[^\d.]/g, ''))}
            onKeyDown={(e) => e.key === 'Enter' && add()} />
        </label>
        <label className="min-w-[200px] flex-1"><span className="label mb-1 block">Note (optional)</span>
          <input className="input h-8" maxLength={120} value={note} onChange={(e) => setNote(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add()} />
        </label>
        <button className="h-8 rounded bg-info px-4 text-sm font-medium text-white disabled:opacity-40" disabled={!(Number(priceText) > 0)} onClick={add}>Create alert</button>
      </div>
      {s.alerts.length === 0 ? <Empty>No alerts. You can also set one by clicking a chart with the bell tool.</Empty> : (
        <table className="w-full text-xs">
          <thead className="table-head"><tr><th>Created</th><th>Instrument</th><th>Condition</th><th className="!text-right">LTP</th><th>Status</th><th>Note</th><th /></tr></thead>
          <tbody>
            {s.alerts.map((a) => {
              const row = s.stocks.find((x) => x.symbol === a.symbol)
              return (
                <tr key={a.id} className="table-row">
                  <td className="num text-txt-mute">{gameTime(a.created)}</td>
                  <td className="font-medium">{a.symbol}</td>
                  <td>{a.op === 'ABOVE' ? 'Crosses above' : 'Falls below'} <span className="num">{num(a.price)}</span>
                    {row && a.status === 'ACTIVE' && <span className="num ml-1 text-txt-mute">({pct(a.price / row.price - 1, 1)} away)</span>}</td>
                  <td className="text-right">{row ? <LiveNum symbol={a.symbol} value={row.price} /> : '—'}</td>
                  <td><Badge tone={a.status === 'ACTIVE' ? 'info' : a.status === 'TRIGGERED' ? 'warn' : 'neutral'}>{a.status.toLowerCase()}</Badge>
                    {a.triggered_at && <span className="num ml-1 text-txt-mute">{hhmm(a.triggered_at)}</span>}</td>
                  <td className="text-txt-mute">{a.note}</td>
                  <td className="text-right">{a.status === 'ACTIVE' && <button className="icon-btn inline-grid !h-7 !w-7 hover:text-down" aria-label="Remove alert" onClick={() => run(() => api.cancelAlert(a.id))}><X size={14} /></button>}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
