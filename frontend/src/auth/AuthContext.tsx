import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi, onUnauthorized, session, type AuthResponse, type User } from '../services/api'

interface AuthCtx {
  user: User | null
  /** True while the stored session token is being checked on page load. */
  checking: boolean
  googleClientId: string | null
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, name: string) => Promise<void>
  loginWithGoogle: (credential: string) => Promise<void>
  /** Sets a new password with an emailed code and signs in. */
  resetPassword: (email: string, code: string, password: string) => Promise<void>
  /** Takes a re-issued token (password change, sign out everywhere) without leaving the current game. */
  renewSession: (res: AuthResponse) => void
  updateUser: (u: User) => void
  logout: () => void
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(true)
  const [googleClientId, setGoogleClientId] = useState<string | null>(null)

  const logout = useCallback(() => {
    session.token = null
    session.gameId = null
    setUser(null)
  }, [])

  // The account's most recent career follows the user to whichever browser they sign in on.
  const adopt = useCallback((u: User) => {
    session.gameId = u.latest_game_id
    setUser(u)
  }, [])

  const accept = useCallback(
    (res: AuthResponse) => {
      session.token = res.token
      session.guestPlayerId = null
      adopt(res.user)
    },
    [adopt],
  )

  useEffect(() => {
    onUnauthorized(logout)
    return () => onUnauthorized(null)
  }, [logout])

  useEffect(() => {
    authApi.config().then((c) => setGoogleClientId(c.google_client_id), () => setGoogleClientId(null))
    if (!session.token) {
      setChecking(false)
      return
    }
    authApi
      .me()
      // A 401 signs out via onUnauthorized; a network error keeps the token for the next visit.
      .then(adopt, () => undefined)
      .finally(() => setChecking(false))
  }, [adopt, logout])

  const value = useMemo<AuthCtx>(
    () => ({
      user,
      checking,
      googleClientId,
      login: async (email, password) => accept(await authApi.login(email, password)),
      signup: async (email, password, name) => accept(await authApi.signup(email, password, name)),
      loginWithGoogle: async (credential) => accept(await authApi.google(credential)),
      resetPassword: async (email, code, password) => accept(await authApi.resetPassword(email, code, password)),
      renewSession: (res) => {
        session.token = res.token
        setUser(res.user)
      },
      updateUser: setUser,
      logout,
    }),
    [user, checking, googleClientId, accept, logout],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx)
  if (!c) throw new Error('useAuth outside AuthProvider')
  return c
}
