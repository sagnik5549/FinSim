// Technical indicators computed in the browser so charts update live with every minute.
// Arrays align with the candle array; null where the indicator is not defined yet.

export type Series = (number | null)[]

export function sma(x: number[], n: number): Series {
  const out: Series = new Array(x.length).fill(null)
  let sum = 0
  for (let i = 0; i < x.length; i++) {
    sum += x[i]
    if (i >= n) sum -= x[i - n]
    if (i >= n - 1) out[i] = sum / n
  }
  return out
}

export function ema(x: number[], n: number): Series {
  const out: Series = new Array(x.length).fill(null)
  if (x.length < n) return out
  const k = 2 / (n + 1)
  let prev = x.slice(0, n).reduce((a, b) => a + b, 0) / n
  out[n - 1] = prev
  for (let i = n; i < x.length; i++) {
    prev = x[i] * k + prev * (1 - k)
    out[i] = prev
  }
  return out
}

export function bollinger(x: number[], n = 20, mult = 2): { upper: Series; mid: Series; lower: Series } {
  const mid = sma(x, n)
  const upper: Series = new Array(x.length).fill(null)
  const lower: Series = new Array(x.length).fill(null)
  for (let i = n - 1; i < x.length; i++) {
    const m = mid[i] as number
    let v = 0
    for (let j = i - n + 1; j <= i; j++) v += (x[j] - m) ** 2
    const sd = Math.sqrt(v / n)
    upper[i] = m + mult * sd
    lower[i] = m - mult * sd
  }
  return { upper, mid, lower }
}

/** Wilder's RSI. */
export function rsi(x: number[], n = 14): Series {
  const out: Series = new Array(x.length).fill(null)
  if (x.length <= n) return out
  let gain = 0
  let loss = 0
  for (let i = 1; i <= n; i++) {
    const d = x[i] - x[i - 1]
    if (d >= 0) gain += d
    else loss -= d
  }
  gain /= n
  loss /= n
  out[n] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss)
  for (let i = n + 1; i < x.length; i++) {
    const d = x[i] - x[i - 1]
    gain = (gain * (n - 1) + Math.max(d, 0)) / n
    loss = (loss * (n - 1) + Math.max(-d, 0)) / n
    out[i] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss)
  }
  return out
}

export function macd(x: number[], fast = 12, slow = 26, signal = 9): { macd: Series; signal: Series; hist: Series } {
  const f = ema(x, fast)
  const s = ema(x, slow)
  const line: Series = x.map((_, i) => (f[i] !== null && s[i] !== null ? (f[i] as number) - (s[i] as number) : null))
  const first = line.findIndex((v) => v !== null)
  const sig: Series = new Array(x.length).fill(null)
  if (first >= 0) {
    const vals = line.slice(first) as number[]
    ema(vals, signal).forEach((v, i) => (sig[first + i] = v))
  }
  const hist: Series = line.map((v, i) => (v !== null && sig[i] !== null ? v - (sig[i] as number) : null))
  return { macd: line, signal: sig, hist }
}

/** Volume-weighted average price, restarting each trading day (intraday charts). */
export function vwap(c: { time: number; h: number; l: number; c: number; v: number }[]): Series {
  const out: Series = []
  let day = -1
  let pv = 0
  let vol = 0
  for (const k of c) {
    const d = Math.floor(k.time / 86400)
    if (d !== day) {
      day = d
      pv = 0
      vol = 0
    }
    const tp = (k.h + k.l + k.c) / 3
    pv += tp * k.v
    vol += k.v
    out.push(vol > 0 ? pv / vol : tp)
  }
  return out
}

export function atr(c: { h: number; l: number; c: number }[], n = 14): Series {
  const tr = c.map((k, i) => (i === 0 ? k.h - k.l : Math.max(k.h - k.l, Math.abs(k.h - c[i - 1].c), Math.abs(k.l - c[i - 1].c))))
  return ema(tr, n)
}
