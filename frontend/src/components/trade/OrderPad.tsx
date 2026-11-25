import clsx from 'clsx'
import { AlertTriangle, GripHorizontal, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useGame, useGameState, type Ticket } from '../../game/GameContext'
import { CRORE, int, money, num, pct } from '../../game/format'
import { useLivePrice } from '../../game/live'
import { api, ApiError } from '../../services/api'
import type { Order, OrderType, Quote, Transaction } from '../../types/game'

const TYPES: { value: OrderType; label: string; hint: string }[] = [
  { value: 'MARKET', label: 'Market', hint: 'Fills now at the best available price.' },
  { value: 'LIMIT', label: 'Limit', hint: 'Fills only at your price or better.' },
  { value: 'SL', label: 'SL', hint: 'Stop-limit: becomes a limit order once the trigger trades.' },
  { value: 'SL-M', label: 'SL-M', hint: 'Stop-market: fills at market once the trigger trades.' },
]

function parse(v: string): number {
  const n = Number(v.replace(/,/g, ''))
  return Number.isFinite(n) ? n : NaN
}

export function OrderPad({ ticket }: { ticket: NonNullable<Ticket> }) {
  const s = useGameState()
  const { run, setTicket, busy, toast } = useGame()
  const [side, setSide] = useState<'BUY' | 'SELL'>(ticket.side)
  const [symbol, setSymbol] = useState(ticket.symbol ?? (ticket.side === 'SELL' ? s.holdings[0]?.symbol : undefined) ?? s.stocks[0].symbol)
  const [type, setType] = useState<OrderType>(ticket.type ?? 'MARKET')
  const [qtyText, setQtyText] = useState(ticket.qty ? String(ticket.qty) : '')
  const [priceText, setPriceText] = useState(ticket.price ? ticket.price.toFixed(2) : '')
  const [trigText, setTrigText] = useState(ticket.trigger ? ticket.trigger.toFixed(2) : '')
  const [validity, setValidity] = useState<'DAY' | 'GTC'>('DAY')
  const [bracket, setBracket] = useState(false)
  const [tgtText, setTgtText] = useState('')
  const [slText, setSlText] = useState('')
  const [quote, setQuote] = useState<Quote | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null)

  const stock = s.stocks.find((x) => x.symbol === symbol)!
  const ltp = useLivePrice(symbol, stock.price)
  const holding = s.holdings.find((h) => h.symbol === symbol)
  const qty = parse(qtyText)
  const validQty = Number.isInteger(qty) && qty > 0
  const px = parse(priceText)
  const trig = parse(trigText)
  const needPrice = type === 'LIMIT' || type === 'SL'
  const needTrig = type === 'SL' || type === 'SL-M'
  const open = s.clock.market_status === 'OPEN'
  const entry = needPrice && px > 0 ? px : needTrig && trig > 0 ? trig : ltp
  const isBuy = side === 'BUY'

  // Reset the symbol when switching to SELL on something not held.
  useEffect(() => {
    if (side === 'SELL' && !holding && s.holdings[0]) setSymbol(s.holdings[0].symbol)
    if (side === 'SELL') setBracket(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [side])

  // Prefill a sensible price when switching to a priced order type.
  useEffect(() => {
    if (needPrice && !priceText) setPriceText(ltp.toFixed(2))
    if (needTrig && !trigText) setTrigText((ltp * (isBuy ? 1.005 : 0.995)).toFixed(2))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type])

  useEffect(() => {
    setQuote(null)
    setErr(null)
    if (!validQty) return
    const t = setTimeout(() => {
      api.quote(side, symbol, qty).then(setQuote).catch((e) => setErr(e instanceof ApiError ? e.message : 'Quote unavailable'))
    }, 250)
    return () => clearTimeout(t)
  }, [side, symbol, qty, validQty, s.version])

  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && setTicket(null)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [setTicket])

  const sizes = useMemo(() => {
    if (!isBuy) {
      const q = holding?.qty ?? 0
      return [{ label: '25%', qty: Math.floor(q * 0.25) }, { label: '50%', qty: Math.floor(q * 0.5) }, { label: 'All', qty: q }]
    }
    const unit = entry * 1.003
    const by = (v: number) => Math.floor(v / unit)
    return [
      { label: '₹1 Cr', qty: by(CRORE) },
      { label: '₹5 Cr', qty: by(5 * CRORE) },
      { label: '5% NAV', qty: by(0.05 * s.portfolio.value) },
      { label: '10% NAV', qty: by(0.1 * s.portfolio.value) },
      { label: 'Max', qty: by(s.portfolio.cash * 0.997) },
    ]
  }, [isBuy, holding, entry, s.portfolio])

  const value = validQty ? qty * (type === 'MARKET' ? quote?.exec_price ?? ltp : entry) : 0
  const charges = value ? Math.max(20, value * (isBuy ? 0.0002 : 0.0012)) : 0
  const tgt = parse(tgtText)
  const sl = parse(slText)

  const problems: string[] = []
  if (needPrice && !(px > 0)) problems.push('Enter a limit price.')
  if (needTrig && !(trig > 0)) problems.push('Enter a trigger price.')
  if (type === 'MARKET' && !open) problems.push('Market orders need the market open. Use a limit order to queue for the next session.')
  if (needTrig && trig > 0 && isBuy && trig <= ltp) problems.push('A buy stop triggers above the current price.')
  if (needTrig && trig > 0 && !isBuy && trig >= ltp) problems.push('A sell stop triggers below the current price.')
  if (!isBuy && validQty && qty > (holding?.qty ?? 0)) problems.push(`You hold ${int(holding?.qty ?? 0)} shares.`)
  if (isBuy && value + charges > s.portfolio.cash) problems.push('Not enough cash for this order.')
  if (bracket && tgt > 0 && tgt <= entry) problems.push('Target must be above the entry price.')
  if (bracket && sl > 0 && sl >= entry) problems.push('Stop-loss must be below the entry price.')

  const submit = async () => {
    if (!validQty || problems.length || busy) return
    const res = await run<{ order: Order; transaction?: Transaction }>(() => api.placeOrder({
      symbol, side, type, quantity: qty, validity,
      price: needPrice ? px : undefined, trigger: needTrig ? trig : undefined,
      target: bracket && tgt > 0 ? tgt : undefined, stoploss: bracket && sl > 0 ? sl : undefined,
    }))
    if (!res) return
    const o = res.order
    if (o.status === 'EXECUTED') {
      toast({ kind: 'success', title: `${o.side === 'BUY' ? 'Bought' : 'Sold'} ${int(o.qty)} ${o.symbol}`, body: `Filled at ₹${num(o.fill_price ?? 0)}` })
    } else {
      toast({ kind: 'info', title: 'Order placed', body: `${o.side} ${int(o.qty)} ${o.symbol} · ${o.type}${o.price ? ` @ ₹${num(o.price)}` : ''}${o.trigger ? ` trg ₹${num(o.trigger)}` : ''} · ${o.validity}` })
    }
    setTicket(null)
  }

  const onDown = (e: React.MouseEvent) => {
    drag.current = { x: e.clientX, y: e.clientY, px: pos.x, py: pos.y }
    const move = (ev: MouseEvent) => {
      const d = drag.current
      if (d) setPos({ x: d.px + ev.clientX - d.x, y: d.py + ev.clientY - d.y })
    }
    const up = () => {
      drag.current = null
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mouseup', up)
    }
    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', up)
  }

  return (
    <div role="dialog" aria-label={`${side} order`}
      className="fixed right-3 top-14 z-40 w-[380px] max-w-[calc(100vw-24px)] animate-slideIn rounded-md border border-line bg-ink-850 shadow-pop"
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
      onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLElement).tagName === 'INPUT' && submit()}>
      <div onMouseDown={onDown} className={clsx('flex cursor-move select-none items-center gap-2 rounded-t-md px-3 py-2.5', isBuy ? 'bg-info/15' : 'bg-down/15')}>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={clsx('text-sm font-semibold', isBuy ? 'text-info' : 'text-down')}>{isBuy ? 'Buy' : 'Sell'}</span>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)} onMouseDown={(e) => e.stopPropagation()}
              className="min-w-0 rounded border border-transparent bg-transparent py-0.5 text-sm font-semibold text-txt hover:border-line focus:outline-none">
              {(isBuy ? s.stocks.map((x) => x.symbol) : s.holdings.map((h) => h.symbol)).map((o) => <option key={o} value={o} className="bg-ink-850">{o}</option>)}
            </select>
          </div>
          <div className="num text-2xs text-txt-mute">
            DSX · LTP <span className="text-txt">₹{num(ltp)}</span>{' '}
            <span className={ltp >= stock.prev_close ? 'text-up' : 'text-down'}>{pct(ltp / stock.prev_close - 1)}</span>
          </div>
        </div>
        <GripHorizontal size={14} className="text-txt-mute" />
        <div className="flex rounded border border-line bg-ink-900 p-0.5" onMouseDown={(e) => e.stopPropagation()}>
          {(['BUY', 'SELL'] as const).map((x) => (
            <button key={x} onClick={() => setSide(x)} disabled={x === 'SELL' && s.holdings.length === 0}
              className={clsx('h-6 rounded px-2.5 text-xs font-semibold disabled:opacity-40',
                side === x ? (x === 'BUY' ? 'bg-info text-white' : 'bg-down text-white') : 'text-txt-mute hover:text-txt')}>
              {x === 'BUY' ? 'B' : 'S'}
            </button>
          ))}
        </div>
        <button onClick={() => setTicket(null)} onMouseDown={(e) => e.stopPropagation()} aria-label="Close" className="icon-btn !h-7 !w-7"><X size={15} /></button>
      </div>

      <div className="space-y-3 p-3">
        <div className="flex rounded border border-line">
          {TYPES.map((t) => (
            <button key={t.value} onClick={() => setType(t.value)} title={t.hint}
              className={clsx('h-8 flex-1 text-xs font-medium first:rounded-l last:rounded-r',
                type === t.value ? (isBuy ? 'bg-info/15 text-info' : 'bg-down/15 text-down') : 'text-txt-dim hover:bg-ink-800')}>
              {t.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-2">
          <Field label="Qty" className="col-span-1">
            <input autoFocus inputMode="numeric" className="input num h-9" placeholder="0" value={qtyText}
              onChange={(e) => setQtyText(e.target.value.replace(/[^\d,]/g, ''))} />
          </Field>
          <Field label="Price">
            <input inputMode="decimal" className="input num h-9 disabled:opacity-40" disabled={!needPrice}
              placeholder={needPrice ? '0.00' : 'Market'} value={needPrice ? priceText : ''} onChange={(e) => setPriceText(e.target.value.replace(/[^\d.]/g, ''))} />
          </Field>
          <Field label="Trigger">
            <input inputMode="decimal" className="input num h-9 disabled:opacity-40" disabled={!needTrig}
              placeholder={needTrig ? '0.00' : '—'} value={needTrig ? trigText : ''} onChange={(e) => setTrigText(e.target.value.replace(/[^\d.]/g, ''))} />
          </Field>
        </div>
        <div className="flex flex-wrap gap-1">
          {sizes.map((z) => <button key={z.label} className="chip" disabled={z.qty <= 0} onClick={() => setQtyText(String(z.qty))}>{z.label}</button>)}
          {holding && <span className="ml-auto self-center text-2xs text-txt-mute">Holding {int(holding.qty)} @ ₹{num(holding.avg_cost)}</span>}
        </div>

        <div className="flex items-center gap-4 text-xs">
          <span className="text-txt-mute">Validity</span>
          {(['DAY', 'GTC'] as const).map((v) => (
            <label key={v} className="flex cursor-pointer items-center gap-1.5 text-txt-dim">
              <input type="radio" name="validity" checked={validity === v} onChange={() => setValidity(v)} disabled={type === 'MARKET'} />
              {v === 'DAY' ? 'Day' : 'Good till cancelled'}
            </label>
          ))}
        </div>

        {isBuy && (
          <div className="rounded border border-line">
            <label className="flex cursor-pointer items-center gap-2 px-2.5 py-2 text-xs text-txt-dim">
              <input type="checkbox" checked={bracket} onChange={(e) => setBracket(e.target.checked)} />
              Add target and stop-loss <span className="text-txt-mute">(placed once this order fills)</span>
            </label>
            {bracket && (
              <div className="grid grid-cols-2 gap-2 border-t border-line p-2.5">
                <Field label={<>Target {tgt > 0 && <span className="text-up">{pct(tgt / entry - 1, 1)}</span>}</>}>
                  <input inputMode="decimal" className="input num h-8" placeholder={(entry * 1.05).toFixed(2)} value={tgtText}
                    onChange={(e) => setTgtText(e.target.value.replace(/[^\d.]/g, ''))} />
                </Field>
                <Field label={<>Stop-loss {sl > 0 && <span className="text-down">{pct(sl / entry - 1, 1)}</span>}</>}>
                  <input inputMode="decimal" className="input num h-8" placeholder={(entry * 0.95).toFixed(2)} value={slText}
                    onChange={(e) => setSlText(e.target.value.replace(/[^\d.]/g, ''))} />
                </Field>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded bg-ink-800 px-2.5 py-2 text-xs">
          <Row k="Order value" v={value ? money(value) : '—'} />
          <Row k="Charges (est.)" v={charges ? money(charges) : '—'} />
          <Row k="Cash available" v={money(s.portfolio.cash)} />
          <Row k="Weight after" v={quote ? pct(quote.weight_after, 1, false) : '—'}
            tone={quote && quote.weight_after > s.risk.limits.max_single_stock ? 'text-down' : undefined} />
          {type === 'MARKET' && quote && quote.impact_pct > 0 && <Row k="Market impact" v={`${quote.impact_pct.toFixed(2)}%`} tone="text-warn" />}
          {!isBuy && quote && <Row k="Realised P&L" v={money(quote.realized_pnl, { signed: true })} tone={quote.realized_pnl >= 0 ? 'text-up' : 'text-down'} />}
        </div>

        {(err || problems.length > 0 || (quote?.warnings.length ?? 0) > 0) && validQty && (
          <div className="space-y-1">
            {[...(err ? [err] : []), ...problems, ...(quote?.warnings ?? []).filter((w) => !w.startsWith('Insufficient') && !w.startsWith('You hold'))].map((w, i) => (
              <div key={i} className="flex items-start gap-1.5 text-2xs text-warn"><AlertTriangle size={12} className="mt-px shrink-0" />{w}</div>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <button onClick={submit} disabled={!validQty || problems.length > 0 || busy}
            className={clsx('h-9 flex-1 rounded text-sm font-semibold text-white transition disabled:opacity-40',
              isBuy ? 'bg-info hover:bg-info/90' : 'bg-down hover:bg-down/90')}>
            {isBuy ? 'Buy' : 'Sell'}{validQty ? ` ${int(qty)}` : ''}{type !== 'MARKET' ? ` · ${type}` : ''}
          </button>
          <button onClick={() => setTicket(null)} className="h-9 rounded border border-line px-4 text-sm text-txt-dim hover:bg-ink-800">Cancel</button>
        </div>
        {!open && <div className="text-2xs text-txt-mute">The market is closed. Limit and stop orders queue for the next session.</div>}
      </div>
    </div>
  )
}

function Field({ label, children, className }: { label: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <label className={clsx('block', className)}>
      <span className="label mb-1 block">{label}</span>
      {children}
    </label>
  )
}

function Row({ k, v, tone }: { k: string; v: string; tone?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-txt-mute">{k}</span>
      <span className={clsx('num text-right text-txt', tone)}>{v}</span>
    </div>
  )
}
