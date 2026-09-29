// Indian-style number formatting (lakh / crore).
export const CRORE = 1e7
export const LAKH = 1e5

const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
const inr0 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

export function money(v: number, opts: { signed?: boolean; decimals?: number } = {}): string {
  const { signed = false, decimals = 2 } = opts
  const sign = v < 0 ? '−' : signed && v > 0 ? '+' : ''
  const a = Math.abs(v)
  if (a >= CRORE) return `${sign}₹${(a / CRORE).toFixed(decimals)} Cr`
  if (a >= LAKH) return `${sign}₹${(a / LAKH).toFixed(decimals)} L`
  return `${sign}₹${inr0.format(Math.round(a))}`
}

export function price(v: number): string {
  return `₹${inr.format(v)}`
}

export function num(v: number, decimals = 2): string {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: decimals, minimumFractionDigits: decimals }).format(v)
}

export function int(v: number): string {
  return inr0.format(Math.round(v))
}

export function pct(v: number, decimals = 2, signed = true): string {
  const x = v * 100
  const sign = x < 0 ? '−' : signed && x > 0 ? '+' : ''
  return `${sign}${Math.abs(x).toFixed(decimals)}%`
}

export function compactVol(v: number): string {
  if (v >= 1e7) return `${(v / 1e7).toFixed(2)}Cr`
  if (v >= 1e5) return `${(v / 1e5).toFixed(1)}L`
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`
  return `${Math.round(v)}`
}

export function tone(v: number): 'up' | 'down' | 'flat' {
  return v > 1e-9 ? 'up' : v < -1e-9 ? 'down' : 'flat'
}

export function toneClass(v: number): string {
  const t = tone(v)
  return t === 'up' ? 'text-up' : t === 'down' ? 'text-down' : 'text-txt-dim'
}

export function gameTime(iso: string): string {
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'))
  const wd = d.toLocaleDateString('en-GB', { weekday: 'short', timeZone: 'UTC' })
  const dm = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' })
  const hm = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })
  return `${wd} ${dm} · ${hm}`
}

export function hhmm(iso: string): string {
  return iso.slice(11, 16)
}

export function shortDate(iso: string): string {
  const d = new Date(iso.slice(0, 10) + 'T00:00:00Z')
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' })
}

/** Naive game timestamps are treated as UTC for charting. */
export function toUnix(iso: string): number {
  if (iso.length === 10) return Date.parse(iso + 'T00:00:00Z') / 1000
  return Date.parse(iso + (iso.endsWith('Z') ? '' : 'Z')) / 1000
}

export function titleCase(s: string): string {
  return s.toLowerCase().replace(/(^|[_\s])(\w)/g, (_, p, c) => (p ? ' ' : '') + c.toUpperCase())
}
