import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, ApiError, session } from '../services/api'
import type { ActionResponse, GameState, Page } from '../types/game'

export interface Toast {
  id: number
  kind: 'error' | 'success' | 'info'
  title: string
  body?: string
}

export type Modal =
  | { kind: 'trade'; side: 'BUY' | 'SELL'; symbol?: string }
  | { kind: 'research'; symbol?: string }
  | { kind: 'leave' }
  | { kind: 'saves' }
  | { kind: 'settings' }
  | { kind: 'executed'; tx: { side: string; symbol: string; qty: number; price: number; value: number; realized_pnl: number; fee: number } }
  | null

export const LIVE_SPEEDS = [
  { label: '1×', ms: 6000 },
  { label: '2×', ms: 3000 },
  { label: '4×', ms: 1500 },
] as const

interface Ctx {
  state: GameState | null
  booting: boolean
  busy: boolean
  page: Page
  setPage: (p: Page) => void
  symbol: string
  openSymbol: (s: string, page?: Page) => void
  modal: Modal
  setModal: (m: Modal) => void
  toasts: Toast[]
  toast: (t: Omit<Toast, 'id'>) => void
  dismissToast: (id: number) => void
  run: <R>(fn: () => Promise<ActionResponse<R>>, opts?: { quiet?: boolean }) => Promise<R | undefined>
  startNewGame: (seed?: number, name?: string) => Promise<void>
  restart: () => Promise<void>
  replaceState: (s: GameState) => void
  refresh: () => Promise<void>
  live: boolean
  setLive: (v: boolean) => void
  speed: number
  setSpeed: (i: number) => void
  leaveGame: () => void
}

const GameCtx = createContext<Ctx | null>(null)

// ------------------------------------------------------------------ live replay
export interface Replay {
  t: string
  paths: Record<string, number[]>
  start: number
  duration: number
}

interface LiveCtxValue {
  replay: Replay | null
  now: number
}
const LiveCtx = createContext<LiveCtxValue>({ replay: null, now: 0 })

/** Interpolated position along an intra-hour path. Returns null when not animating. */
export function samplePath(path: number[] | undefined, progress: number): number | null {
  if (!path || path.length < 2) return null
  const p = Math.min(1, Math.max(0, progress))
  const x = p * (path.length - 1)
  const i = Math.floor(x)
  if (i >= path.length - 1) return path[path.length - 1]
  const f = x - i
  return path[i] + (path[i + 1] - path[i]) * f
}

export function useLiveProgress(): { replay: Replay | null; progress: number } {
  const { replay, now } = useContext(LiveCtx)
  if (!replay) return { replay: null, progress: 1 }
  return { replay, progress: Math.min(1, (now - replay.start) / replay.duration) }
}

/** Live value for a symbol/index key: animates along the last hour's tick path. */
export function useLiveValue(key: string, finalValue: number): number {
  const { replay, progress } = useLiveProgress()
  if (!replay || progress >= 1) return finalValue
  return samplePath(replay.paths[key], progress) ?? finalValue
}

// ------------------------------------------------------------------ provider
export function GameProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GameState | null>(null)
  const [booting, setBooting] = useState(true)
  const [busy, setBusy] = useState(false)
  const [page, setPage] = useState<Page>('dashboard')
  const [symbol, setSymbol] = useState('BH50')
  const [modal, setModal] = useState<Modal>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [live, setLiveRaw] = useState(false)
  const [speed, setSpeedRaw] = useState(() => {
    try {
      return Number(localStorage.getItem('ibm.speed') ?? 1) || 1
    } catch {
      return 1
    }
  })
  const [replay, setReplay] = useState<Replay | null>(null)
  const [now, setNow] = useState(0)
  const busyRef = useRef(false)
  const lastTickRef = useRef<string | null>(null)

  const toast = useCallback((t: Omit<Toast, 'id'>) => {
    const id = Date.now() + Math.random()
    setToasts((xs) => [...xs.slice(-3), { ...t, id }])
    setTimeout(() => setToasts((xs) => xs.filter((x) => x.id !== id)), t.kind === 'error' ? 5000 : 3200)
  }, [])
  const dismissToast = useCallback((id: number) => setToasts((xs) => xs.filter((x) => x.id !== id)), [])

  const liveMs = LIVE_SPEEDS[Math.min(speed, LIVE_SPEEDS.length - 1)].ms

  const acceptState = useCallback(
    (s: GameState, animate = true) => {
      const t = s.last_tick?.t ?? null
      if (animate && t && t !== lastTickRef.current && s.last_tick) {
        const duration = live ? Math.min(liveMs * 0.85, 4200) : 1400
        setReplay({ t, paths: s.last_tick.paths, start: performance.now(), duration })
      }
      lastTickRef.current = t
      setState(s)
    },
    [live, liveMs],
  )

  // RAF loop only while a replay is running
  useEffect(() => {
    if (!replay) return
    let raf = 0
    let last = 0
    const loop = (ts: number) => {
      if (ts - last > 45) {
        last = ts
        setNow(ts)
      }
      if (ts - replay.start < replay.duration + 60) raf = requestAnimationFrame(loop)
      else setNow(ts)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [replay])

  const handleError = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError) {
        if (e.code === 'NO_GAME') {
          session.gameId = null
          setState(null)
        }
        toast({ kind: 'error', title: e.code.replace(/_/g, ' '), body: e.message })
      } else {
        toast({ kind: 'error', title: 'Connection problem', body: 'The game server did not respond. Is the backend running?' })
      }
    },
    [toast],
  )

  const run = useCallback(
    async <R,>(fn: () => Promise<ActionResponse<R>>, opts: { quiet?: boolean } = {}) => {
      if (busyRef.current) return undefined
      busyRef.current = true
      setBusy(true)
      try {
        const res = await fn()
        acceptState(res.state)
        return res.result
      } catch (e) {
        if (!opts.quiet) handleError(e)
        else if (e instanceof ApiError && e.code !== 'DECISION_REQUIRED') handleError(e)
        return undefined
      } finally {
        busyRef.current = false
        setBusy(false)
      }
    },
    [acceptState, handleError],
  )

  const refresh = useCallback(async () => {
    try {
      acceptState(await api.state(), false)
    } catch (e) {
      handleError(e)
    }
  }, [acceptState, handleError])

  // Boot: resume the career stored in this browser (backend state is authoritative).
  useEffect(() => {
    ;(async () => {
      if (session.gameId) {
        try {
          const s = await api.state()
          lastTickRef.current = s.last_tick?.t ?? null
          setState(s)
        } catch {
          session.gameId = null
        }
      }
      setBooting(false)
    })()
  }, [])

  const startNewGame = useCallback(
    async (seed?: number, name?: string) => {
      setBusy(true)
      try {
        const res = await api.newGame(seed, name)
        session.gameId = res.state.game_id
        session.playerId = res.player_id
        lastTickRef.current = res.state.last_tick?.t ?? null
        setState(res.state)
        setPage('dashboard')
        setSymbol('BH50')
      } catch (e) {
        handleError(e)
      } finally {
        setBusy(false)
      }
    },
    [handleError],
  )

  const restart = useCallback(async () => {
    setLiveRaw(false)
    session.gameId = null
    setState(null)
    setModal(null)
  }, [])

  const leaveGame = useCallback(() => {
    setLiveRaw(false)
    setState(null)
    setModal(null)
  }, [])

  const replaceState = useCallback(
    (s: GameState) => {
      session.gameId = s.game_id
      acceptState(s, false)
    },
    [acceptState],
  )

  const openSymbol = useCallback((s: string, p?: Page) => {
    setSymbol(s)
    if (p) setPage(p)
  }, [])

  const setLive = useCallback((v: boolean) => setLiveRaw(v), [])
  const setSpeed = useCallback((i: number) => {
    setSpeedRaw(i)
    try {
      localStorage.setItem('ibm.speed', String(i))
    } catch {
      /* ignore */
    }
  }, [])

  // ---------------------------------------------------------------- live auto-play
  useEffect(() => {
    if (!live || !state) return
    const paused =
      busy || modal !== null || state.popups.length > 0 || state.career.status !== 'ACTIVE' || state.clock.is_on_leave
    if (paused) return
    const status = state.clock.market_status
    const delay = status === 'OPEN' ? liveMs : Math.max(1200, liveMs / 2)
    const id = setTimeout(() => {
      if (status === 'OPEN') run(api.advanceHour, { quiet: true })
      else run(api.nextBusinessDay, { quiet: true })
    }, delay)
    return () => clearTimeout(id)
  }, [live, state, busy, modal, liveMs, run])

  useEffect(() => {
    if (state && state.career.status !== 'ACTIVE') setLiveRaw(false)
  }, [state])

  const value = useMemo<Ctx>(
    () => ({
      state, booting, busy, page, setPage, symbol, openSymbol, modal, setModal, toasts, toast, dismissToast, run,
      startNewGame, restart, replaceState, refresh, live, setLive, speed, setSpeed, leaveGame,
    }),
    [state, booting, busy, page, symbol, openSymbol, modal, toasts, toast, dismissToast, run, startNewGame, restart,
      replaceState, refresh, live, setLive, speed, setSpeed, leaveGame],
  )

  return (
    <GameCtx.Provider value={value}>
      <LiveCtx.Provider value={{ replay, now }}>{children}</LiveCtx.Provider>
    </GameCtx.Provider>
  )
}

export function useGame(): Ctx {
  const c = useContext(GameCtx)
  if (!c) throw new Error('useGame outside GameProvider')
  return c
}

export function useGameState(): GameState {
  const { state } = useGame()
  if (!state) throw new Error('No game loaded')
  return state
}
