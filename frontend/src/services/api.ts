import type { ActionResponse, GameState, Quote, ResearchReport, SaveSlot, SymbolDetail, Transaction } from '../types/game'

const GAME_KEY = 'ibm.gameId'
const PLAYER_KEY = 'ibm.playerId'

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
    try {
      return localStorage.getItem(GAME_KEY)
    } catch {
      return null
    }
  },
  get playerId(): string | null {
    try {
      return localStorage.getItem(PLAYER_KEY)
    } catch {
      return null
    }
  },
  set playerId(id: string | null) {
    try {
      if (id) localStorage.setItem(PLAYER_KEY, id)
    } catch {
      /* ignore */
    }
  },
  set gameId(id: string | null) {
    try {
      if (id) localStorage.setItem(GAME_KEY, id)
      else localStorage.removeItem(GAME_KEY)
    } catch {
      /* storage unavailable: session-only play */
    }
  },
}

async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const gid = session.gameId
  if (gid) headers['X-Game-Id'] = gid
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
    throw new ApiError(res.status, code, message)
  }
  return res.json() as Promise<T>
}

type Act<R = unknown> = Promise<ActionResponse<R>>

export const api = {
  newGame: (seed?: number, player_name?: string) =>
    request<{ player_id: string; state: GameState }>('POST', '/game/new', { seed, player_name, player_id: session.playerId ?? undefined }),
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
