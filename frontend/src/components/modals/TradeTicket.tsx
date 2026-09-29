import clsx from 'clsx'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useGame, useGameState } from '../../game/GameContext'
import { CRORE, int, money, pct, price, toneClass } from '../../game/format'
import { api, ApiError } from '../../services/api'
import type { Quote, Transaction } from '../../types/game'
import { Badge, Button, LivePrice, Modal, Segmented } from '../common/ui'

export function TradeTicket({ side: initialSide, symbol: initialSymbol }: { side: 'BUY' | 'SELL'; symbol?: string }) {
  const s = useGameState()
  const { run, setModal, busy } = useGame()
  const [side, setSide] = useState<'BUY' | 'SELL'>(initialSide)
  const [symbol, setSymbol] = useState(initialSymbol ?? (initialSide === 'SELL' ? s.holdings[0]?.symbol : s.stocks[0].symbol) ?? s.stocks[0].symbol)
  const [qtyText, setQtyText] = useState('')
  const [quote, setQuote] = useState<Quote | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const stock = s.stocks.find((x) => x.symbol === symbol)!
  const holding = s.holdings.find((h) => h.symbol === symbol)
  const qty = Number(qtyText.replace(/,/g, ''))
  const validQty = Number.isInteger(qty) && qty > 0
  const research = s.research.find((r) => r.symbol === symbol)
  const options = side === 'SELL' ? s.holdings.map((h) => h.symbol) : s.stocks.map((x) => x.symbol)

  useEffect(() => {
    if (side === 'SELL' && !holding && s.holdings[0]) setSymbol(s.holdings[0].symbol)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [side])

  useEffect(() => {
    setQuote(null)
    setErr(null)
    if (!validQty) return
    const t = setTimeout(() => {
      api.quote(side, symbol, qty).then(setQuote).catch((e) => setErr(e instanceof ApiError ? e.message : 'Quote unavailable'))
    }, 200)
    return () => clearTimeout(t)
  }, [side, symbol, qty, validQty, s.version])

  const sizes = useMemo(() => {
    if (side === 'SELL') {
      const q = holding?.qty ?? 0
      return [
        { label: '25%', qty: Math.floor(q * 0.25) },
        { label: '50%', qty: Math.floor(q * 0.5) },
        { label: 'ALL', qty: q },
      ]
    }
    const px = stock.price * 1.003
    const byValue = (v: number) => Math.floor(v / px)
    return [
      { label: '₹1 Cr', qty: byValue(CRORE) },
      { label: '₹5 Cr', qty: byValue(5 * CRORE) },
      { label: '5% NAV', qty: byValue(0.05 * s.portfolio.value) },
      { label: '10% NAV', qty: byValue(0.1 * s.portfolio.value) },
      { label: 'MAX', qty: byValue(s.portfolio.cash * 0.997) },
    ]
  }, [side, holding, stock.price, s.portfolio])

  const confirm = async () => {
    const res = await run<{ transaction: Transaction }>(() => (side === 'BUY' ? api.buy(symbol, qty) : api.sell(symbol, qty)))
    if (res?.transaction) setModal({ kind: 'executed', tx: res.transaction })
  }
  const blocking = quote?.warnings.some((w) => w.startsWith('Insufficient') || w.startsWith('You hold'))

  return (
    <Modal onClose={() => setModal(null)} width="max-w-[560px]">
      <div className={clsx('border-b border-line px-5 py-4', side === 'BUY' ? 'bg-gradient-to-r from-up/10' : 'bg-gradient-to-r from-down/10')}>
        <div className="flex items-center gap-3">
          <Segmented size="md" value={side} onChange={setSide}
            options={[{ value: 'BUY', label: <span className={side === 'BUY' ? 'text-up' : ''}>BUY</span> },
              { value: 'SELL', label: <span className={side === 'SELL' ? 'text-down' : ''}>SELL</span> }]} />
          <span className="label">Order ticket · market order</span>
        </div>
        <div className="mt-3 flex items-end justify-between gap-3">
          <div className="min-w-0 flex-1">
            <label className="label" htmlFor="sym">Stock</label>
            <select id="sym" className="input mt-1 font-semibold" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
              {options.map((o) => {
                const st = s.stocks.find((x) => x.symbol === o)!
                return <option key={o} value={o}>{o} — {st.name}</option>
              })}
            </select>
          </div>
          <div className="text-right">
            <LivePrice symbol={symbol} value={stock.price} className="text-xl font-bold" />
            <div className={clsx('num text-xs', toneClass(stock.change_pct))}>{pct(stock.change_pct)} today</div>
          </div>
        </div>
      </div>

      <div className="space-y-4 px-5 py-4">
        <div>
          <div className="flex items-center justify-between">
            <label className="label" htmlFor="qty">Quantity (shares)</label>
            {holding && <span className="text-2xs text-txt-mute">You hold <span className="num text-txt">{int(holding.qty)}</span> @ {price(holding.avg_cost)}</span>}
          </div>
          <input id="qty" autoFocus inputMode="numeric" className="input num mt-1 h-11 text-lg" placeholder="0" value={qtyText}
            onChange={(e) => setQtyText(e.target.value.replace(/[^\d,]/g, ''))} onKeyDown={(e) => e.key === 'Enter' && quote && !blocking && confirm()} />
          <div className="mt-2 flex flex-wrap gap-1.5">
            {sizes.map((z) => (
              <button key={z.label} className="chip" disabled={z.qty <= 0} onClick={() => setQtyText(String(z.qty))}>{z.label}</button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-ink-900 p-3">
          {!validQty && <div className="py-3 text-center text-xs text-txt-mute">Enter a quantity to see the execution preview.</div>}
          {err && <div className="py-3 text-center text-xs text-down">{err}</div>}
          {quote && (
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
              <Row k="Price (est. fill)" v={price(quote.exec_price)} sub={quote.impact_pct > 0 ? `impact ${quote.impact_pct.toFixed(2)}%` : undefined} />
              <Row k="Quantity" v={int(quote.qty)} />
              <Row k="Transaction value" v={money(quote.value)} />
              <Row k={side === 'BUY' ? 'Estimated fee' : 'Fee + STT'} v={money(quote.fee)} />
              <Row k={side === 'BUY' ? 'Total cost' : 'Net proceeds'} v={money(quote.total)} strong />
              <Row k="Cash after" v={money(quote.cash_after)} tone={quote.cash_after < 0 ? 'text-down' : undefined} />
              <Row k="Position weight after" v={pct(quote.weight_after, 1, false)} tone={quote.weight_after > s.risk.limits.max_single_stock ? 'text-down' : undefined} />
              {side === 'SELL'
                ? <Row k="Realised P&L" v={money(quote.realized_pnl, { signed: true })} tone={toneClass(quote.realized_pnl)} />
                : <Row k="Sector after" v={quote.sector_after !== undefined ? pct(quote.sector_after, 1, false) : '—'} tone={(quote.sector_after ?? 0) > s.risk.limits.max_sector ? 'text-down' : undefined} />}
            </div>
          )}
          {quote && quote.warnings.length > 0 && (
            <div className="mt-3 space-y-1">
              {quote.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 rounded border border-warn/30 bg-warn-soft px-2 py-1.5 text-2xs text-warn">
                  <AlertTriangle size={12} className="mt-px shrink-0" /> {w}
                </div>
              ))}
            </div>
          )}
        </div>

        {side === 'BUY' && (
          <div className="text-2xs text-txt-mute">
            {research
              ? <>Latest research: <Badge tone={research.rating === 'BUY' ? 'up' : research.rating === 'SELL' ? 'down' : 'neutral'}>{research.rating}</Badge> est. fair value <span className="num text-txt-dim">{price(research.est_fair_value)}</span></>
              : 'No research on file. Compliance expects documentation for positions above 8% of the book.'}
          </div>
        )}

        <div className="flex gap-2">
          <Button variant="ghost" className="flex-1" onClick={() => setModal(null)}>Cancel</Button>
          <Button variant={side === 'BUY' ? 'buy' : 'sell'} size="lg" className="flex-[2]" disabled={!quote || busy || !!blocking || s.clock.market_status !== 'OPEN'} onClick={confirm}>
            CONFIRM {side}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

function Row({ k, v, sub, strong, tone }: { k: string; v: string; sub?: string; strong?: boolean; tone?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-txt-mute">{k}</span>
      <span className={clsx('num text-right', strong ? 'font-bold text-txt' : 'text-txt', tone)}>
        {v}{sub && <span className="ml-1 text-2xs text-warn">{sub}</span>}
      </span>
    </div>
  )
}

export function ExecutedModal({ tx }: { tx: { side: string; symbol: string; qty: number; price: number; value: number; realized_pnl: number; fee: number } }) {
  const { setModal } = useGame()
  useEffect(() => {
    const t = setTimeout(() => setModal(null), 2600)
    return () => clearTimeout(t)
  }, [setModal])
  return (
    <Modal onClose={() => setModal(null)} width="max-w-sm">
      <div className="flex flex-col items-center px-6 py-7 text-center">
        <div className={clsx('grid h-14 w-14 place-items-center rounded-full', tx.side === 'BUY' ? 'bg-up-soft text-up shadow-glowUp' : 'bg-down-soft text-down shadow-glowDown')}>
          <CheckCircle2 size={30} />
        </div>
        <div className="mt-3 font-display text-lg font-bold tracking-[0.2em]">TRADE EXECUTED</div>
        <div className="mt-1 text-sm text-txt-dim">
          {tx.side} <span className="num font-semibold text-txt">{int(tx.qty)}</span> {tx.symbol} @ <span className="num text-txt">{price(tx.price)}</span>
        </div>
        <div className="num mt-1 text-xs text-txt-mute">{money(tx.value)} · fee {money(tx.fee)}</div>
        {tx.side === 'SELL' && <div className={clsx('num mt-2 text-sm font-bold', toneClass(tx.realized_pnl))}>Realised {money(tx.realized_pnl, { signed: true })}</div>}
      </div>
    </Modal>
  )
}
