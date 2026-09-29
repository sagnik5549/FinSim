import clsx from 'clsx'
import { X } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useLiveValue } from '../../game/GameContext'
import { num, pct, price as fmtPrice, toneClass } from '../../game/format'

export function Panel({
  title, right, children, className, bodyClass, icon,
}: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string; bodyClass?: string; icon?: ReactNode }) {
  return (
    <section className={clsx('panel flex min-h-0 flex-col', className)}>
      {title !== undefined && (
        <header className="flex h-9 shrink-0 items-center justify-between gap-2 border-b border-line px-3">
          <h2 className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-[0.14em] text-txt-dim">
            {icon}
            {title}
          </h2>
          <div className="flex items-center gap-2">{right}</div>
        </header>
      )}
      <div className={clsx('min-h-0 flex-1', bodyClass)}>{children}</div>
    </section>
  )
}

export function Sparkline({ data, width = 80, height = 24, color, fill = true, className }: {
  data: number[]; width?: number; height?: number; color?: string; fill?: boolean; className?: string
}) {
  if (!data || data.length < 2) return <svg width={width} height={height} className={className} />
  const min = Math.min(...data)
  const max = Math.max(...data)
  const span = max - min || 1
  const pts = data.map((v, i) => [(i / (data.length - 1)) * width, height - 2 - ((v - min) / span) * (height - 4)])
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('')
  const up = data[data.length - 1] >= data[0]
  const c = color ?? (up ? '#26D07C' : '#F2495C')
  return (
    <svg width={width} height={height} className={className} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {fill && <path d={`${d}L${width},${height}L0,${height}Z`} fill={c} opacity={0.12} />}
      <path d={d} fill="none" stroke={c} strokeWidth={1.4} strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r={1.8} fill={c} />
    </svg>
  )
}

export function Badge({ children, tone = 'neutral', className }: {
  children: ReactNode; tone?: 'up' | 'down' | 'warn' | 'info' | 'violet' | 'gold' | 'neutral'; className?: string
}) {
  const map = {
    up: 'bg-up-soft text-up border-up/30',
    down: 'bg-down-soft text-down border-down/30',
    warn: 'bg-warn-soft text-warn border-warn/30',
    info: 'bg-info-soft text-info border-info/30',
    violet: 'bg-violet-soft text-violet border-violet/30',
    gold: 'bg-gold-soft text-gold border-gold/30',
    neutral: 'bg-ink-700 text-txt-dim border-line',
  }
  return (
    <span className={clsx('inline-flex items-center gap-1 rounded border px-1.5 py-px text-2xs font-semibold uppercase tracking-wider', map[tone], className)}>
      {children}
    </span>
  )
}

export function Button({
  children, onClick, variant = 'ghost', disabled, className, title, size = 'md', type = 'button',
}: {
  children: ReactNode; onClick?: () => void; variant?: 'primary' | 'buy' | 'sell' | 'ghost' | 'warn' | 'gold' | 'subtle'
  disabled?: boolean; className?: string; title?: string; size?: 'sm' | 'md' | 'lg'; type?: 'button' | 'submit'
}) {
  const v = {
    primary: 'bg-info text-white hover:bg-[#5d99ff] shadow-glowInfo border-info',
    buy: 'bg-up/90 text-ink-950 hover:bg-up border-up shadow-glowUp',
    sell: 'bg-down/90 text-white hover:bg-down border-down shadow-glowDown',
    warn: 'bg-warn/15 text-warn hover:bg-warn/25 border-warn/40',
    gold: 'bg-gold text-ink-950 hover:brightness-110 border-gold shadow-glowGold',
    ghost: 'bg-ink-750 text-txt hover:bg-ink-700 border-line hover:border-ink-500',
    subtle: 'bg-transparent text-txt-dim hover:text-txt hover:bg-ink-750 border-transparent',
  }[variant]
  const s = { sm: 'h-7 px-2.5 text-xs', md: 'h-9 px-3.5 text-[13px]', lg: 'h-11 px-5 text-sm' }[size]
  return (
    <button
      type={type}
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'inline-flex select-none items-center justify-center gap-2 rounded-md border font-semibold tracking-wide transition',
        'disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none',
        v, s, className,
      )}
    >
      {children}
    </button>
  )
}

export function Bar({ value, max = 1, tone = 'info', className, marker }: {
  value: number; max?: number; tone?: 'up' | 'down' | 'warn' | 'info' | 'gold' | 'violet'; className?: string; marker?: number
}) {
  const w = Math.max(0, Math.min(1, value / max)) * 100
  const c = { up: 'bg-up', down: 'bg-down', warn: 'bg-warn', info: 'bg-info', gold: 'bg-gold', violet: 'bg-violet' }[tone]
  return (
    <div className={clsx('relative h-1.5 w-full overflow-hidden rounded-full bg-ink-700', className)}>
      <div className={clsx('h-full rounded-full transition-[width] duration-700', c)} style={{ width: `${w}%` }} />
      {marker !== undefined && (
        <div className="absolute top-[-2px] h-[10px] w-[2px] bg-txt" style={{ left: `${Math.min(100, (marker / max) * 100)}%` }} />
      )}
    </div>
  )
}

export function Ring({ value, size = 88, stroke = 7, color = '#4C8DFF', children }: {
  value: number; size?: number; stroke?: number; color?: string; children?: ReactNode
}) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const v = Math.max(0, Math.min(1, value))
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#172136" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - v)} style={{ transition: 'stroke-dashoffset .8s ease', filter: `drop-shadow(0 0 6px ${color}66)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">{children}</div>
    </div>
  )
}

/** Price that animates along the live intra-hour path and flashes on change. */
export function LivePrice({ symbol, value, decimals = 2, className, prefix = '₹' }: {
  symbol: string; value: number; decimals?: number; className?: string; prefix?: string
}) {
  const live = useLiveValue(symbol, value)
  const prev = useRef(value)
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  useEffect(() => {
    if (value !== prev.current) {
      setFlash(value > prev.current ? 'up' : 'down')
      prev.current = value
      const t = setTimeout(() => setFlash(null), 1000)
      return () => clearTimeout(t)
    }
  }, [value])
  return (
    <span className={clsx('num rounded px-0.5', flash === 'up' && 'animate-flashUp', flash === 'down' && 'animate-flashDown', className)}>
      {prefix === '₹' && decimals === 2 ? fmtPrice(live) : `${prefix}${num(live, decimals)}`}
    </span>
  )
}

export function Change({ value, className, decimals = 2 }: { value: number; className?: string; decimals?: number }) {
  return <span className={clsx('num', toneClass(value), className)}>{pct(value, decimals)}</span>
}

export function Stat({ label, value, sub, className }: { label: ReactNode; value: ReactNode; sub?: ReactNode; className?: string }) {
  return (
    <div className={clsx('min-w-0', className)}>
      <div className="label">{label}</div>
      <div className="num mt-0.5 truncate text-[15px] font-semibold text-txt">{value}</div>
      {sub && <div className="mt-0.5 text-2xs text-txt-mute">{sub}</div>}
    </div>
  )
}

export function Modal({ children, onClose, width = 'max-w-lg', className, closable = true, labelledBy }: {
  children: ReactNode; onClose?: () => void; width?: string; className?: string; closable?: boolean; labelledBy?: string
}) {
  useEffect(() => {
    if (!closable || !onClose) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [closable, onClose])
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/75 p-4 backdrop-blur-[3px] animate-fadeIn">
      <div role="dialog" aria-modal="true" aria-labelledby={labelledBy}
        className={clsx('panel relative max-h-[92vh] w-full overflow-y-auto animate-scaleIn', width, className)}>
        {closable && onClose && (
          <button onClick={onClose} aria-label="Close" className="absolute right-3 top-3 z-10 rounded p-1 text-txt-mute hover:bg-ink-700 hover:text-txt">
            <X size={16} />
          </button>
        )}
        {children}
      </div>
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="flex h-full min-h-[80px] items-center justify-center px-4 text-center text-xs text-txt-mute">{children}</div>
}

export function Segmented<T extends string>({ options, value, onChange, size = 'sm' }: {
  options: { value: T; label: ReactNode }[]; value: T; onChange: (v: T) => void; size?: 'sm' | 'md'
}) {
  return (
    <div className="inline-flex rounded-md border border-line bg-ink-900 p-0.5">
      {options.map((o) => (
        <button key={o.value} onClick={() => onChange(o.value)}
          className={clsx('rounded px-2.5 font-semibold transition', size === 'sm' ? 'h-6 text-2xs' : 'h-8 text-xs',
            value === o.value ? 'bg-ink-600 text-txt shadow' : 'text-txt-mute hover:text-txt-dim')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}
