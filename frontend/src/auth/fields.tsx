import clsx from 'clsx'
import type { ReactNode } from 'react'
import { ApiError } from '../services/api'

/** 6-digit one-time code box: digits only, autofills from SMS/email suggestions where supported. */
export function CodeInput({ value, onChange, autoFocus }: { value: string; onChange: (v: string) => void; autoFocus?: boolean }) {
  return (
    <input className="input num mt-1 text-center text-xl" inputMode="numeric" autoComplete="one-time-code"
      required pattern="\d{6}" maxLength={6} placeholder="••••••" value={value} autoFocus={autoFocus}
      aria-label="6-digit code" onChange={(e) => onChange(e.target.value.replace(/\D/g, '').slice(0, 6))} />
  )
}

export function Notice({ tone, children }: { tone: 'error' | 'info'; children: ReactNode }) {
  return (
    <div role={tone === 'error' ? 'alert' : 'status'}
      className={clsx('rounded-md border px-3 py-2 text-xs', tone === 'error' ? 'border-down/40 bg-down-soft text-down' : 'border-info/40 bg-info-soft text-info')}>
      {children}
    </div>
  )
}

export function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.message
  return 'Could not reach the game server. Check your connection and try again.'
}
