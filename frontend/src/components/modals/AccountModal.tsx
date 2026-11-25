import { Check, KeyRound, Loader2, LogOut, Mail, UserRound } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { CodeInput, errorText, Notice } from '../../auth/fields'
import { PASSWORD_HINT, passwordProblem } from '../../auth/password'
import { useGame } from '../../game/GameContext'
import { authApi } from '../../services/api'
import { Badge, Button, Modal } from '../common/ui'

function Section({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="space-y-2 border-b border-line px-5 py-4 last:border-b-0">
      <div className="flex items-center gap-2 text-2xs font-bold text-txt-dim">{icon}{title}</div>
      {children}
    </section>
  )
}

/** Shared "working / error" state for each section's async action. */
function useAction() {
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const run = async (fn: () => Promise<void>) => {
    setError(null)
    setWorking(true)
    try {
      await fn()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setWorking(false)
    }
  }
  return { working, error, setError, run }
}

function NameSection() {
  const { user, updateUser } = useAuth()
  const { toast } = useGame()
  const [name, setName] = useState(user?.name ?? '')
  const a = useAction()
  const save = (e: FormEvent) => {
    e.preventDefault()
    a.run(async () => {
      updateUser(await authApi.updateProfile(name))
      toast({ kind: 'success', title: 'Name updated' })
    })
  }
  return (
    <Section icon={<UserRound size={13} />} title="Name">
      <form onSubmit={save} className="flex gap-2">
        <input className="input" value={name} maxLength={80} required onChange={(e) => setName(e.target.value)} aria-label="Name" />
        <Button type="submit" disabled={a.working || !name.trim() || name.trim() === user?.name}>Save</Button>
      </form>
      {a.error && <Notice tone="error">{a.error}</Notice>}
    </Section>
  )
}

function EmailSection() {
  const { user, updateUser } = useAuth()
  const { toast } = useGame()
  const [editing, setEditing] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const a = useAction()

  const close = () => {
    setEditing(false)
    setSentTo(null)
    setCode('')
    setNewEmail('')
    a.setError(null)
  }
  const send = (e?: FormEvent) => {
    e?.preventDefault()
    a.run(async () => {
      setSentTo((await authApi.requestCode('change_email', newEmail)).sent_to)
      setCode('')
    })
  }
  const confirm = (e: FormEvent) => {
    e.preventDefault()
    a.run(async () => {
      updateUser(await authApi.changeEmail(newEmail, code))
      toast({ kind: 'success', title: 'Email changed', body: `Sign in with ${newEmail.trim().toLowerCase()} from now on.` })
      close()
    })
  }

  return (
    <Section icon={<Mail size={13} />} title="Email">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm">{user?.email}</span>
        {!editing && <Button size="sm" onClick={() => setEditing(true)}>Change</Button>}
      </div>
      {editing && !sentTo && (
        <form onSubmit={send} className="space-y-2">
          <input className="input" type="email" required maxLength={254} placeholder="New email address" autoFocus
            value={newEmail} onChange={(e) => setNewEmail(e.target.value)} aria-label="New email" />
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={a.working}>{a.working ? <Loader2 size={14} className="animate-spin" /> : 'Send code'}</Button>
            <Button variant="subtle" onClick={close}>Cancel</Button>
          </div>
        </form>
      )}
      {editing && sentTo && (
        <form onSubmit={confirm} className="space-y-2">
          <Notice tone="info">We sent a code to {sentTo}. Enter it to confirm the new address.</Notice>
          <CodeInput value={code} onChange={setCode} autoFocus />
          <div className="flex items-center gap-2">
            <Button type="submit" variant="primary" disabled={a.working || code.length !== 6}>Confirm</Button>
            <Button variant="subtle" onClick={close}>Cancel</Button>
            <button type="button" onClick={() => send()} disabled={a.working} className="ml-auto text-2xs font-semibold text-info hover:underline disabled:opacity-50">
              Send a new code
            </button>
          </div>
        </form>
      )}
      {a.error && <Notice tone="error">{a.error}</Notice>}
    </Section>
  )
}

function PasswordSection() {
  const { user, renewSession } = useAuth()
  const { toast } = useGame()
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const a = useAction()
  const verb = user?.has_password ? 'Change' : 'Add'

  const send = () => a.run(async () => {
    setSentTo((await authApi.requestCode('change_password')).sent_to)
    setCode('')
  })
  const save = (e: FormEvent) => {
    e.preventDefault()
    const weak = passwordProblem(password, user?.email)
    if (weak) {
      a.setError(weak)
      return
    }
    a.run(async () => {
      renewSession(await authApi.changePassword(code, password))
      toast({ kind: 'success', title: 'Password saved', body: 'Other devices have been signed out.' })
      setSentTo(null)
      setPassword('')
      setCode('')
    })
  }

  return (
    <Section icon={<KeyRound size={13} />} title="Password">
      <div className="flex flex-wrap items-center gap-2 text-xs text-txt-dim">
        <span>Sign-in methods:</span>
        {user?.has_password && <Badge tone="up"><Check size={10} /> Password</Badge>}
        {user?.has_google && <Badge tone="info"><Check size={10} /> Google</Badge>}
      </div>
      {!sentTo ? (
        <div className="flex items-center gap-3">
          <Button size="sm" onClick={send} disabled={a.working}>
            {a.working ? <Loader2 size={12} className="animate-spin" /> : `${verb} password`}
          </Button>
          <span className="text-2xs text-txt-mute">We'll email a code to confirm it's you.</span>
        </div>
      ) : (
        <form onSubmit={save} className="space-y-2">
          <Notice tone="info">We sent a code to {sentTo}.</Notice>
          <CodeInput value={code} onChange={setCode} autoFocus />
          <input className="input" type="password" required minLength={8} maxLength={128} autoComplete="new-password"
            placeholder="New password" value={password} onChange={(e) => setPassword(e.target.value)} aria-label="New password" />
          <div className="text-2xs text-txt-mute">{PASSWORD_HINT} Saving signs out your other devices.</div>
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={a.working || code.length !== 6}>Save password</Button>
            <Button variant="subtle" onClick={() => { setSentTo(null); a.setError(null) }}>Cancel</Button>
          </div>
        </form>
      )}
      {a.error && <Notice tone="error">{a.error}</Notice>}
    </Section>
  )
}

function SessionsSection() {
  const { renewSession } = useAuth()
  const { toast } = useGame()
  const [confirm, setConfirm] = useState(false)
  const a = useAction()
  const go = () => a.run(async () => {
    renewSession(await authApi.signOutEverywhere())
    toast({ kind: 'success', title: 'Signed out elsewhere', body: 'Every other device now needs to sign in again.' })
    setConfirm(false)
  })
  return (
    <Section icon={<LogOut size={13} />} title="Devices">
      {!confirm ? (
        <div className="flex items-center gap-3">
          <Button size="sm" variant="warn" onClick={() => setConfirm(true)}>Sign out of other devices</Button>
          <span className="text-2xs text-txt-mute">Use this if you signed in on a computer you don't own.</span>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="flex-1 text-xs text-txt-dim">Sign out everywhere except this browser?</span>
          <Button size="sm" onClick={() => setConfirm(false)}>Cancel</Button>
          <Button size="sm" variant="sell" onClick={go} disabled={a.working}>Sign out others</Button>
        </div>
      )}
      {a.error && <Notice tone="error">{a.error}</Notice>}
    </Section>
  )
}

export function AccountModal() {
  const { setModal } = useGame()
  return (
    <Modal onClose={() => setModal(null)} width="max-w-[500px]">
      <div className="flex items-center justify-between border-b border-line py-4 pl-5 pr-12">
        <span className="font-display text-base font-bold">Account</span>
        <Button size="sm" variant="subtle" onClick={() => setModal({ kind: 'settings' })}>← Settings</Button>
      </div>
      <div className="max-h-[75vh] overflow-y-auto text-xs">
        <NameSection />
        <EmailSection />
        <PasswordSection />
        <SessionsSection />
      </div>
    </Modal>
  )
}
