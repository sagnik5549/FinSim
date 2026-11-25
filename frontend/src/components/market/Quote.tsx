import clsx from 'clsx'
import { useEffect, useRef, useState } from 'react'
import { compactVol, num, pct } from '../../game/format'
import { useLivePrice } from '../../game/live'
import type { SymbolDetail } from '../../types/game'

/** Live price that flashes green/red on each change. */
export function LiveNum({ symbol, value, decimals = 2, className, flash = true }: {
  symbol: string; value: number; decimals?: number; className?: string; flash?: boolean
}) {
  const v = useLivePrice(symbol, value)
  // Flash once per new traded minute (server price), not on every animation step.
  const prev = useRef(value)
  const [dir, setDir] = useState<'up' | 'down' | null>(null)
  useEffect(() => {
    if (!flash || value === prev.current) return
    setDir(value > prev.current ? 'up' : 'down')
    prev.current = value
    const t = setTimeout(() => setDir(null), 800)
    return () => clearTimeout(t)
  }, [value, flash])
  return (
    <span className={clsx('num rounded-sm', dir === 'up' && 'animate-flashUp', dir === 'down' && 'animate-flashDown', className)}>
      {num(v, decimals)}
    </span>
  )
}

/** Day change of a live price against the previous close. */
export function LiveChange({ symbol, value, prevClose, className, abs = false }: {
  symbol: string; value: number; prevClose: number; className?: string; abs?: boolean
}) {
  const v = useLivePrice(symbol, value)
  const ch = v - prevClose
  const p = prevClose ? ch / prevClose : 0
  return (
    <span className={clsx('num', ch > 0 ? 'text-up' : ch < 0 ? 'text-down' : 'text-txt-dim', className)}>
      {abs && `${ch >= 0 ? '+' : '−'}${num(Math.abs(ch))} `}{abs ? `(${pct(p)})` : pct(p)}
    </span>
  )
}

export function MarketDepth({ depth }: { depth: NonNullable<SymbolDetail['depth']> }) {
  const max = Math.max(...depth.bids.map((b) => b.qty), ...depth.asks.map((a) => a.qty), 1)
  const total = depth.total_bid + depth.total_ask || 1
  return (
    <div className="text-xs">
      <div className="grid grid-cols-2 gap-px">
        <table className="w-full">
          <thead><tr className="text-2xs text-txt-mute"><th className="px-2 py-1 text-left font-medium">Bid</th><th className="font-medium">Orders</th><th className="px-2 text-right font-medium">Qty</th></tr></thead>
          <tbody>
            {depth.bids.map((b, i) => (
              <tr key={i} className="relative">
                <td className="num relative px-2 py-[3px] text-info">
                  <span className="absolute inset-y-0.5 right-0 bg-info/10" style={{ width: `${(b.qty / max) * 100}%` }} />
                  <span className="relative">{num(b.price)}</span>
                </td>
                <td className="num text-center text-txt-mute">{b.orders}</td>
                <td className="num px-2 text-right">{compactVol(b.qty)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <table className="w-full">
          <thead><tr className="text-2xs text-txt-mute"><th className="px-2 py-1 text-left font-medium">Offer</th><th className="font-medium">Orders</th><th className="px-2 text-right font-medium">Qty</th></tr></thead>
          <tbody>
            {depth.asks.map((a, i) => (
              <tr key={i}>
                <td className="num relative px-2 py-[3px] text-down">
                  <span className="absolute inset-y-0.5 left-0 bg-down/10" style={{ width: `${(a.qty / max) * 100}%` }} />
                  <span className="relative">{num(a.price)}</span>
                </td>
                <td className="num text-center text-txt-mute">{a.orders}</td>
                <td className="num px-2 text-right">{compactVol(a.qty)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-1.5 flex h-1 overflow-hidden rounded-full">
        <div className="bg-info/70" style={{ width: `${(depth.total_bid / total) * 100}%` }} />
        <div className="flex-1 bg-down/70" />
      </div>
      <div className="num mt-1 flex justify-between px-0.5 text-2xs text-txt-mute">
        <span>Total bid {compactVol(depth.total_bid)}</span>
        <span>Total offer {compactVol(depth.total_ask)}</span>
      </div>
    </div>
  )
}
