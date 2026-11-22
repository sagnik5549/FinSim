import clsx from 'clsx'
import { ArrowRight, Loader2 } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { CodeInput, errorText, Notice } from '../auth/fields'
import { PASSWORD_HINT, passwordProblem } from '../auth/password'
import { Button } from '../components/common/ui'
import { authApi } from '../services/api'
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

export default function Login() {
  const { login, signup, loginWithGoogle, googleClientId } = useAuth()
  const [mode, setMode] = useState<'signin' | 'signup' | 'forgot'>('signin')
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
              setError(errorText(e))
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
    const weak = mode === 'signup' ? passwordProblem(password, email) : null
    if (weak) {
      setError(weak)
      return
    }
    setWorking(true)
    try {
      if (mode === 'signin') await login(email, password)
      else await signup(email, password, name)
    } catch (err) {
      setError(errorText(err))
      setWorking(false)
    }
  }

  const switchMode = (m: 'signin' | 'signup' | 'forgot') => {
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
          {mode === 'forgot' ? <ForgotPassword initialEmail={email} onDone={() => switchMode('signin')} /> : <>
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
              {mode === 'signup' && <span className="mt-1 block text-2xs text-txt-mute">{PASSWORD_HINT}</span>}
            </label>
            {mode === 'signin' && (
              <div className="-mt-1 text-right">
                <button type="button" onClick={() => switchMode('forgot')} className="text-2xs font-semibold text-info hover:underline">
                  Forgot password?
                </button>
              </div>
            )}

            {error && <Notice tone="error">{error}</Notice>}

            <Button type="submit" variant="gold" size="lg" disabled={working} className="w-full tracking-[0.2em]">
              {working ? <Loader2 className="animate-spin" size={18} />
                : <>{mode === 'signin' ? 'SIGN IN' : 'CREATE ACCOUNT'} <ArrowRight size={18} /></>}
            </Button>
          </form>
          </>}

          {/* Kept mounted while resetting a password so Google's button doesn't have to be re-rendered. */}
          {googleClientId && (
            <div className={clsx('px-6 pb-6', mode === 'forgot' && 'hidden')}>
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

/** Two steps: email a code, then enter it with a new password (which also signs in). */
function ForgotPassword({ initialEmail, onDone }: { initialEmail: string; onDone: () => void }) {
  const { resetPassword } = useAuth()
  const [email, setEmail] = useState(initialEmail)
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [working, setWorking] = useState(false)

  const send = async (e?: FormEvent) => {
    e?.preventDefault()
    setError(null)
    setWorking(true)
    try {
      setSentTo((await authApi.forgotPassword(email)).sent_to)
      setCode('')
    } catch (err) {
      setError(errorText(err))
    } finally {
      setWorking(false)
    }
  }

  const reset = async (e: FormEvent) => {
    e.preventDefault()
    const weak = passwordProblem(password, email)
    if (weak) {
      setError(weak)
      return
    }
    setError(null)
    setWorking(true)
    try {
      await resetPassword(email, code, password)
    } catch (err) {
      setError(errorText(err))
      setWorking(false)
    }
  }

  return (
    <div className="px-6 py-5">
      <div className="mb-1 font-display text-lg font-bold">Reset your password</div>
      {!sentTo ? (
        <form onSubmit={send} className="space-y-3">
          <p className="text-xs text-txt-dim">Enter your account email and we'll send you a 6-digit code.</p>
          <label className="block">
            <span className="label">Email</span>
            <input className="input mt-1" type="email" required value={email} maxLength={254} autoComplete="email" autoFocus
              onChange={(e) => setEmail(e.target.value)} />
          </label>
          {error && <Notice tone="error">{error}</Notice>}
          <Button type="submit" variant="gold" size="lg" disabled={working} className="w-full tracking-[0.2em]">
            {working ? <Loader2 className="animate-spin" size={18} /> : <>SEND CODE <ArrowRight size={18} /></>}
          </Button>
        </form>
      ) : (
        <form onSubmit={reset} className="space-y-3">
          <Notice tone="info">If an account exists for that email, a code is on its way to {sentTo}. It expires in 10 minutes.</Notice>
          <label className="block">
            <span className="label">Code</span>
            <CodeInput value={code} onChange={setCode} autoFocus />
          </label>
          <label className="block">
            <span className="label">New password</span>
            <input className="input mt-1" type="password" required minLength={8} maxLength={128} autoComplete="new-password"
              value={password} onChange={(e) => setPassword(e.target.value)} />
            <span className="mt-1 block text-2xs text-txt-mute">{PASSWORD_HINT}</span>
          </label>
          {error && <Notice tone="error">{error}</Notice>}
          <Button type="submit" variant="gold" size="lg" disabled={working || code.length !== 6} className="w-full tracking-[0.2em]">
            {working ? <Loader2 className="animate-spin" size={18} /> : <>SET PASSWORD &amp; SIGN IN <ArrowRight size={18} /></>}
          </Button>
          <button type="button" onClick={() => send()} disabled={working} className="text-2xs font-semibold text-info hover:underline disabled:opacity-50">
            Send a new code
          </button>
        </form>
      )}
      <button type="button" onClick={onDone} className="mt-4 block text-2xs font-semibold text-txt-mute hover:text-txt">
        ← Back to sign in
      </button>
    </div>
  )
}
