// Live prices outside React state.
//
// The server advances the market one game minute at a time (every 15 s at 1x). Each
// tick brings the minute bars just completed; the store animates every symbol's
// displayed price along those bars (open → high/low → close) over the next tick
// interval, so prices move continuously. Components subscribe per symbol, so a price
// change re-renders only the cells that show it, not the whole terminal.
import { useSyncExternalStore } from 'react'
import { toUnix } from './format'
import type { GameState } from '../types/game'

export interface MinuteBar {
  time: number // unix seconds (game time, treated as UTC)
  o: number
  h: number
  l: number
  c: number
  v: number
}

type Listener = () => void
type BarListener = (symbol: string, bars: MinuteBar[]) => void

interface Anim {
  pts: number[]
  start: number
  dur: number
}

const FRAME_MS = 250

/** Waypoints through a bar in the order a real minute tends to trade: open, the near extreme, the far one, close. */
export function barPath(from: number, bars: { o: number; h: number; l: number; c: number }[]): number[] {
  const pts = [from]
  for (const b of bars) {
    const up = b.c >= b.o
    pts.push(b.o, up ? b.l : b.h, (b.o + b.c) / 2, up ? b.h : b.l, b.c)
  }
  return pts
}

/** Position along a waypoint path at progress p in [0, 1]. */
export function samplePath(pts: number[] | undefined, p: number): number | null {
  if (!pts || pts.length === 0) return null
  if (pts.length === 1) return pts[0]
  const x = Math.min(1, Math.max(0, p)) * (pts.length - 1)
  const i = Math.floor(x)
  if (i >= pts.length - 1) return pts[pts.length - 1]
  return pts[i] + (pts[i + 1] - pts[i]) * (x - i)
}

class LiveStore {
  private price = new Map<string, number>()
  private anim = new Map<string, Anim>()
  private lastBar = new Map<string, number>()
  private subs = new Map<string, Set<Listener>>()
  private any = new Set<Listener>()
  private barSubs = new Set<BarListener>()
  private timer: ReturnType<typeof setInterval> | null = null
  private gameId: string | null = null

  get(symbol: string): number | undefined {
    return this.price.get(symbol)
  }

  /** Latest completed minute (unix seconds) seen for a symbol. */
  lastMinute(symbol: string): number | undefined {
    return this.lastBar.get(symbol)
  }

  /** Take a fresh server state. `animMs` is how long to spread the new minute(s) over. */
  ingest(s: GameState, animMs: number): void {
    const reset = s.game_id !== this.gameId
    this.gameId = s.game_id
    const now = performance.now()
    const finals = new Map<string, number>()
    for (const x of s.stocks) finals.set(x.symbol, x.price)
    for (const x of s.indices) finals.set(x.key, x.value)
    const times = (s.minutes?.t ?? []).map(toUnix)
    const changed: string[] = []
    for (const [sym, final] of finals) {
      const raw = s.minutes?.bars[sym] ?? []
      const seen = reset ? -1 : this.lastBar.get(sym) ?? -1
      const fresh: MinuteBar[] = []
      raw.forEach((b, i) => {
        const t = times[i]
        if (t !== undefined && t > seen) fresh.push({ time: t, o: b[0], h: b[1], l: b[2], c: b[3], v: b[4] ?? 0 })
      })
      if (fresh.length) {
        this.lastBar.set(sym, fresh[fresh.length - 1].time)
        if (!reset) this.barSubs.forEach((fn) => fn(sym, fresh))
      }
      const cur = this.price.get(sym)
      if (reset || cur === undefined || animMs <= 0 || !fresh.length) {
        // No new minute for this symbol (or first load): settle on the server price.
        if (!this.anim.has(sym) || reset || animMs <= 0) {
          this.anim.delete(sym)
          if (cur !== final) {
            this.price.set(sym, final)
            changed.push(sym)
          }
        }
        continue
      }
      const pts = barPath(cur, fresh)
      pts[pts.length - 1] = final
      this.anim.set(sym, { pts, start: now, dur: animMs })
    }
    this.emit(changed)
    this.ensureTimer()
  }

  private ensureTimer(): void {
    if (this.timer || this.anim.size === 0) return
    this.timer = setInterval(() => this.frame(), FRAME_MS)
  }

  private frame(): void {
    const now = performance.now()
    const changed: string[] = []
    for (const [sym, a] of this.anim) {
      const p = (now - a.start) / a.dur
      const v = samplePath(a.pts, p) ?? a.pts[a.pts.length - 1]
      const rounded = Math.round(v * 10000) / 10000
      if (this.price.get(sym) !== rounded) {
        this.price.set(sym, rounded)
        changed.push(sym)
      }
      if (p >= 1) this.anim.delete(sym)
    }
    this.emit(changed)
    if (this.anim.size === 0 && this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  }

  private emit(symbols: string[]): void {
    if (!symbols.length) return
    for (const s of symbols) this.subs.get(s)?.forEach((fn) => fn())
    this.any.forEach((fn) => fn())
  }

  subscribe(symbol: string, fn: Listener): () => void {
    let set = this.subs.get(symbol)
    if (!set) this.subs.set(symbol, (set = new Set()))
    set.add(fn)
    return () => set!.delete(fn)
  }

  subscribeAll(fn: Listener): () => void {
    this.any.add(fn)
    return () => this.any.delete(fn)
  }

  onBars(fn: BarListener): () => void {
    this.barSubs.add(fn)
    return () => this.barSubs.delete(fn)
  }
}

export const liveStore = new LiveStore()

/** The live (animated) price of a stock or index. */
export function useLivePrice(symbol: string, fallback: number): number {
  return useSyncExternalStore(
    (fn) => liveStore.subscribe(symbol, fn),
    () => liveStore.get(symbol) ?? fallback,
  )
}

let version = 0
liveStore.subscribeAll(() => {
  version++
})

/** Re-render on any live price change (throttled to the store's frame rate). */
export function useLiveVersion(): number {
  return useSyncExternalStore((fn) => liveStore.subscribeAll(fn), () => version)
}

/** Portfolio value marked at live prices. */
export function useLiveNav(s: GameState): number {
  useLiveVersion()
  let v = s.portfolio.cash
  for (const h of s.holdings) v += h.qty * (liveStore.get(h.symbol) ?? h.price)
  return v
}
