import type { ActionResponse, GameState, Quote, ResearchReport, SaveSlot, SymbolDetail, Transaction } from '../types/game'

const GAME_KEY = 'ibm.gameId'
const PLAYER_KEY = 'ibm.playerId'
const TOKEN_KEY = 'ibm.token'

export interface User {
  id: string
  email: string
  name: string
  player_id: string
  has_password: boolean
  has_google: boolean
  latest_game_id: string | null
}

export interface AuthResponse {
  token: string
  user: User
}

function store(key: string, value: string | null) {
  try {
    if (value) localStorage.setItem(key, value)
    else localStorage.removeItem(key)
  } catch {
    /* storage unavailable: session-only play */
  }
}

function load(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

export class ApiError extends Error {
  code: string
  status: number
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export const session = {
  get gameId(): string | null {
    return load(GAME_KEY)
  },
  set gameId(id: string | null) {
    store(GAME_KEY, id)
  },
  /** Pre-login guest player from older versions; adopted by the first account created in this browser. */
  get guestPlayerId(): string | null {
    return load(PLAYER_KEY)
  },
  set guestPlayerId(id: string | null) {
    store(PLAYER_KEY, id)
  },
  get token(): string | null {
    return load(TOKEN_KEY)
  },
  set token(t: string | null) {
    store(TOKEN_KEY, t)
  },
}

let unauthorizedHandler: (() => void) | null = null
/** Called when the server rejects the session token (expired, revoked or tampered). */
export function onUnauthorized(fn: (() => void) | null) {
  unauthorizedHandler = fn
}

async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const gid = session.gameId
  if (gid) headers['X-Game-Id'] = gid
  const token = session.token
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
  if (!res.ok) {
    let code = 'ERROR'
    let message = `Request failed (${res.status})`
    try {
      const j = await res.json()
      if (j?.detail?.code) {
        code = j.detail.code
        message = j.detail.message
      } else if (Array.isArray(j?.detail)) {
        code = 'VALIDATION'
        message = j.detail.map((d: { msg: string }) => d.msg).join('; ')
      }
    } catch {
      /* non-JSON error */
    }
    if (res.status === 401 && code === 'UNAUTHORIZED' && token) unauthorizedHandler?.()
    throw new ApiError(res.status, code, message)
  }
  return res.json() as Promise<T>
}

type Act<R = unknown> = Promise<ActionResponse<R>>

export const authApi = {
  config: () => request<{ google_client_id: string | null }>('GET', '/auth/config'),
  me: () => request<User>('GET', '/auth/me'),
  login: (email: string, password: string) => request<AuthResponse>('POST', '/auth/login', { email, password }),
  signup: (email: string, password: string, name: string) =>
    request<AuthResponse>('POST', '/auth/signup', { email, password, name, guest_player_id: session.guestPlayerId ?? undefined }),
  google: (credential: string) =>
    request<AuthResponse>('POST', '/auth/google', { credential, guest_player_id: session.guestPlayerId ?? undefined }),
  forgotPassword: (email: string) => request<{ sent_to: string }>('POST', '/auth/password/forgot', { email }),
  resetPassword: (email: string, code: string, new_password: string) =>
    request<AuthResponse>('POST', '/auth/password/reset', { email, code, new_password }),
  requestCode: (purpose: 'change_email' | 'change_password', new_email?: string) =>
    request<{ sent_to: string }>('POST', '/auth/code', { purpose, new_email }),
  changeEmail: (new_email: string, code: string) => request<User>('POST', '/auth/email', { new_email, code }),
  changePassword: (code: string, new_password: string) =>
    request<AuthResponse>('POST', '/auth/password', { code, new_password }),
  updateProfile: (name: string) => request<User>('POST', '/auth/profile', { name }),
  signOutEverywhere: () => request<AuthResponse>('POST', '/auth/sign-out-everywhere'),
}

export const api = {
  newGame: (seed?: number, player_name?: string) =>
    request<{ player_id: string; state: GameState }>('POST', '/game/new', { seed, player_name }),
  restart: () => request<{ player_id: string; state: GameState }>('POST', '/game/restart'),
  state: () => request<GameState>('GET', '/game/state'),

  advanceHour: (): Act => request('POST', '/game/advance-hour'),
  advanceHours: (hours: number): Act => request('POST', '/game/advance-hours', { hours }),
  advanceToClose: (): Act => request('POST', '/game/advance-to-close'),
  nextBusinessDay: (): Act => request('POST', '/game/advance-next-business-day'),
  skipWeekend: (): Act => request('POST', '/game/skip-weekend'),
  nextWeek: (): Act => request('POST', '/game/advance-week'),

  ackPopup: (popup_id: string): Act => request('POST', '/game/popup/ack', { popup_id }),
  markRead: (kind: 'messages' | 'notifications', ids?: string[]): Act => request('POST', '/game/read', { kind, ids }),

  save: (name: string) => request<SaveSlot>('POST', '/game/save', { name }),
  saves: () => request<SaveSlot[]>('GET', '/game/saves'),
  load: (save_id: number) => request<{ game_id: string; state: GameState }>('POST', '/game/load', { save_id }),

  symbol: (symbol: string, tf: '1h' | '1d' = '1h', limit = 240) =>
    request<SymbolDetail>('GET', `/market/${symbol}?tf=${tf}&limit=${limit}`),

  quote: (side: 'BUY' | 'SELL', symbol: string, quantity: number) =>
    request<Quote>('POST', '/trade/quote', { side, symbol, quantity }),
  buy: (symbol: string, quantity: number): Act<{ transaction: Transaction }> => request('POST', '/trade/buy', { symbol, quantity }),
  sell: (symbol: string, quantity: number): Act<{ transaction: Transaction }> => request('POST', '/trade/sell', { symbol, quantity }),

  acceptDeal: (id: string, quantity?: number): Act => request('POST', `/opportunities/${id}/accept`, { quantity }),
  declineDeal: (id: string): Act => request('POST', `/opportunities/${id}/decline`),

  research: (symbol: string, depth: 'QUICK' | 'DEEP'): Act<{ report: ResearchReport; hours_used: number }> => request('POST', `/research/${symbol}`, { depth }),
  thesis: (symbol: string, stance: string, text: string): Act => request('POST', '/research/thesis', { symbol, stance, text }),

  resolveRisk: (warning_id: string, action: string): Act => request('POST', '/risk/resolve', { warning_id, action }),
  takeLeave: (days: number): Act => request('POST', '/leave/start', { days }),
  hire: (candidate_id: string): Act => request('POST', '/team/hire', { candidate_id }),

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  get: <T = any>(path: string) => request<T>('GET', path),
}
