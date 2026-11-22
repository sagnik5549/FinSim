import clsx from 'clsx'
import { ArrowRight, Loader2 } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/common/ui'
import { ApiError } from '../services/api'
import { Backdrop } from './Onboarding'

interface GoogleId {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void; ux_mode?: 'popup' }) => void
  renderButton: (el: HTMLElement, o: Record<string, unknown>) => void
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } }
  }
}

const GSI_SRC = 'https://accounts.google.com/gsi/client'

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GSI_SRC}"]`)
    const s = existing ?? Object.assign(document.createElement('script'), { src: GSI_SRC, async: true, defer: true })
    s.addEventListener('load', () => resolve())
    s.addEventListener('error', () => reject(new Error('Google sign-in failed to load')))
    if (!existing) document.head.appendChild(s)
  })
}

function message(e: unknown): string {
  if (e instanceof ApiError) return e.message
  return 'Could not reach the game server. Check your connection and try again.'
}

export default function Login() {
  const { login, signup, loginWithGoogle, googleClientId } = useAuth()
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [working, setWorking] = useState(false)
  const googleRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!googleClientId) return
    let cancelled = false
    loadGoogleScript()
      .then(() => {
        if (cancelled || !googleRef.current || !window.google) return
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          ux_mode: 'popup',
          callback: async ({ credential }) => {
            setError(null)
            setWorking(true)
            try {
              await loginWithGoogle(credential)
            } catch (e) {
              setError(message(e))
              setWorking(false)
            }
          },
        })
        window.google.accounts.id.renderButton(googleRef.current, {
          theme: 'filled_black', size: 'large', shape: 'pill', text: 'continue_with', width: 320,
        })
      })
      .catch(() => !cancelled && setError('Google sign-in could not load. You can still use email and password.'))
    return () => {
      cancelled = true
    }
  }, [googleClientId, loginWithGoogle])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (mode === 'signup' && password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setWorking(true)
    try {
      if (mode === 'signin') await login(email, password)
      else await signup(email, password, name)
    } catch (err) {
      setError(message(err))
      setWorking(false)
    }
  }

  const switchMode = (m: 'signin' | 'signup') => {
    setMode(m)
    setError(null)
  }

  return (
    <div className="relative flex h-full items-center justify-center overflow-y-auto bg-ink-950 px-4 py-8">
      <Backdrop />
      <div className="relative w-full max-w-[400px] animate-rise">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 h-px w-32 bg-gradient-to-r from-transparent via-gold to-transparent" />
          <h1 className="font-display text-3xl font-bold tracking-[0.3em] text-txt">APEX CAPITAL</h1>
          <div className="mt-2 text-2xs uppercase tracking-[0.4em] text-txt-dim">Investment Management Division</div>
        </div>

        <div className="panel overflow-hidden">
          <div className="grid grid-cols-2 border-b border-line text-xs font-bold uppercase tracking-[0.18em]">
            {(['signin', 'signup'] as const).map((m) => (
              <button key={m} type="button" onClick={() => switchMode(m)}
                className={clsx('py-3 transition', mode === m ? 'bg-gold/10 text-gold shadow-[inset_0_-2px_0_#E9B949]' : 'text-txt-mute hover:text-txt')}>
                {m === 'signin' ? 'Sign in' : 'Create account'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-3 px-6 py-5">
            {mode === 'signup' && (
              <label className="block">
                <span className="label">Name</span>
                <input className="input mt-1" value={name} maxLength={80} autoComplete="name"
                  onChange={(e) => setName(e.target.value)} placeholder="How Apex Capital should address you" />
              </label>
            )}
            <label className="block">
              <span className="label">Email</span>
              <input className="input mt-1" type="email" required value={email} maxLength={254} autoComplete="email"
                onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Password</span>
              <input className="input mt-1" type="password" required value={password} maxLength={128}
                minLength={mode === 'signup' ? 8 : undefined}
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                onChange={(e) => setPassword(e.target.value)} />
              {mode === 'signup' && <span className="mt-1 block text-2xs text-txt-mute">At least 8 characters.</span>}
            </label>

            {error && (
              <div role="alert" className="rounded-md border border-down/40 bg-down-soft px-3 py-2 text-xs text-down">{error}</div>
            )}

            <Button type="submit" variant="gold" size="lg" disabled={working} className="w-full tracking-[0.2em]">
              {working ? <Loader2 className="animate-spin" size={18} />
                : <>{mode === 'signin' ? 'SIGN IN' : 'CREATE ACCOUNT'} <ArrowRight size={18} /></>}
            </Button>
          </form>

          {googleClientId && (
            <div className="px-6 pb-6">
              <div className="mb-4 flex items-center gap-3 text-2xs uppercase tracking-[0.2em] text-txt-mute">
                <span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" />
              </div>
              {/* Google's button iframe paints an opaque white box when it inherits color-scheme: dark. */}
              <div ref={googleRef} className="flex min-h-[44px] justify-center" style={{ colorScheme: 'light' }} />
            </div>
          )}
        </div>

        <p className="mt-4 text-center text-2xs leading-relaxed text-txt-mute">
          A simulation game. Every company, index, price and person is fictional. Not financial advice.
        </p>
      </div>
    </div>
  )
}
