import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, ApiError, session } from '../services/api'
import type { ActionResponse, GameState, OrderType, Page, TickResponse } from '../types/game'
import { liveStore } from './live'

export interface Toast {
  id: number
  kind: 'error' | 'success' | 'info'
  title: string
  body?: string
}

export type Modal =
  | { kind: 'trade'; side: 'BUY' | 'SELL'; symbol?: string; type?: OrderType; price?: number; trigger?: number; qty?: number }
  | { kind: 'research'; symbol?: string }
  | { kind: 'leave' }
  | { kind: 'saves' }
  | { kind: 'settings' }
  | { kind: 'account' }
  | { kind: 'executed'; tx: { side: string; symbol: string; qty: number; price: number; value: number; realized_pnl: number; fee: number } }
  | null

/** Order pad defaults (the pad floats beside the market instead of covering it). */
export type Ticket = Extract<Modal, { kind: 'trade' }> | null

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
  ticket: Ticket
  setTicket: (t: Ticket) => void
  chart: string | null
  openChart: (symbol: string | null) => void
  toasts: Toast[]
  toast: (t: Omit<Toast, 'id'>) => void
  dismissToast: (id: number) => void
  run: <R>(fn: () => Promise<ActionResponse<R>>, opts?: { quiet?: boolean }) => Promise<R | undefined>
  startNewGame: (seed?: number, name?: string) => Promise<void>
  restart: () => Promise<void>
  replaceState: (s: GameState) => void
  refresh: () => Promise<void>
  setSpeed: (speed: number) => void
  connected: boolean
  leaveGame: () => void
}

const GameCtx = createContext<Ctx | null>(null)

function isFullState(x: GameState | TickResponse): x is GameState {
  return (x as GameState).clock !== undefined
}

// ------------------------------------------------------------------ provider
export function GameProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GameState | null>(null)
  const [booting, setBooting] = useState(true)
  const [busy, setBusy] = useState(false)
  const [page, setPage] = useState<Page>('dashboard')
  const [symbol, setSymbol] = useState('AKSH')
  const [modal, setModalRaw] = useState<Modal>(null)
  const [ticket, setTicket] = useState<Ticket>(null)
  const [chart, openChart] = useState<string | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [connected, setConnected] = useState(true)
  const busyRef = useRef(false)
  const stateRef = useRef<GameState | null>(null)
  const nextTickRef = useRef(5)

  const toast = useCallback((t: Omit<Toast, 'id'>) => {
    const id = Date.now() + Math.random()
    setToasts((xs) => [...xs.slice(-3), { ...t, id }])
    setTimeout(() => setToasts((xs) => xs.filter((x) => x.id !== id)), t.kind === 'error' ? 5000 : 3200)
  }, [])
  const dismissToast = useCallback((id: number) => setToasts((xs) => xs.filter((x) => x.id !== id)), [])

  const setModal = useCallback((m: Modal) => {
    if (m?.kind === 'trade') {
      setTicket(m)
      return
    }
    setModalRaw(m)
  }, [])

  const acceptState = useCallback((s: GameState, animate = true) => {
    const prev = stateRef.current
    const spm = s.live?.seconds_per_minute ?? 15
    // Animate a minute or two of trading; jump straight to the result after a skip or a long gap.
    const gap = prev ? (Date.parse(s.clock.iso) - Date.parse(prev.clock.iso)) / 60000 : Infinity
    const ms = animate && prev && prev.game_id === s.game_id && gap >= 0 && gap <= 5 ? Math.min(spm * 1000 * 0.95, 20000) : 0
    liveStore.ingest(s, ms)
    stateRef.current = s
    nextTickRef.current = s.live?.next_tick_in ?? 5
    setState(s)
  }, [])

  const handleError = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError) {
        if (e.code === 'NO_GAME') {
          session.gameId = null
          stateRef.current = null
          setState(null)
        }
        toast({ kind: 'error', title: e.code.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()), body: e.message })
      } else {
        toast({ kind: 'error', title: 'Connection problem', body: 'The game server did not respond.' })
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
          acceptState(await api.state(), false)
        } catch {
          session.gameId = null
        }
      }
      setBooting(false)
    })()
  }, [acceptState])

  // ---------------------------------------------------------------- live market
  // The server owns the clock; we ask it to catch up whenever the next game minute is due.
  const hasGame = !!state
  useEffect(() => {
    if (!hasGame) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    let failures = 0
    const schedule = (sec: number) => {
      if (!stopped) timer = setTimeout(tick, Math.max(300, Math.min(30_000, sec * 1000)))
    }
    const tick = async () => {
      const cur = stateRef.current
      if (!cur) return
      if (busyRef.current) return schedule(0.4)
      try {
        const res = await api.tick(cur.version)
        if (stopped) return
        failures = 0
        setConnected(true)
        if (isFullState(res)) {
          // Ignore a tick that raced an action and came back older than what we already show.
          if (!busyRef.current && res.version >= (stateRef.current?.version ?? 0)) acceptState(res)
          schedule(res.live?.next_tick_in ?? 5)
        } else {
          schedule(res.live?.next_tick_in ?? 5)
        }
      } catch (e) {
        if (stopped) return
        failures++
        setConnected(false)
        if (e instanceof ApiError && e.code === 'NO_GAME') return handleError(e)
        schedule(Math.min(30, 2 * failures))
      }
    }
    schedule(nextTickRef.current)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [hasGame, acceptState, handleError])

  const startNewGame = useCallback(
    async (seed?: number, name?: string) => {
      setBusy(true)
      try {
        const res = await api.newGame(seed, name)
        session.gameId = res.state.game_id
        acceptState(res.state, false)
        setPage('dashboard')
        setSymbol(res.state.stocks[0]?.symbol ?? 'AKSH')
      } catch (e) {
        handleError(e)
      } finally {
        setBusy(false)
      }
    },
    [acceptState, handleError],
  )

  const restart = useCallback(async () => {
    session.gameId = null
    stateRef.current = null
    setState(null)
    setModalRaw(null)
    setTicket(null)
    openChart(null)
  }, [])

  const leaveGame = useCallback(() => {
    stateRef.current = null
    setState(null)
    setModalRaw(null)
    setTicket(null)
    openChart(null)
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

  const setSpeed = useCallback((speed: number) => {
    run(() => api.setSpeed(speed), { quiet: true })
  }, [run])

  const value = useMemo<Ctx>(
    () => ({
      state, booting, busy, page, setPage, symbol, openSymbol, modal, setModal, ticket, setTicket, chart, openChart,
      toasts, toast, dismissToast, run, startNewGame, restart, replaceState, refresh, setSpeed, connected, leaveGame,
    }),
    [state, booting, busy, page, symbol, openSymbol, modal, setModal, ticket, chart, toasts, toast, dismissToast, run,
      startNewGame, restart, replaceState, refresh, setSpeed, connected, leaveGame],
  )

  return <GameCtx.Provider value={value}>{children}</GameCtx.Provider>
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
