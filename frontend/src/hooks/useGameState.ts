import { useState, useCallback, useRef } from 'react';
import type { GameState } from '../types/game';
import { gameApi } from '../services/api';

export function useGameState(gameId: string | null) {
  const [state, setState] = useState<GameState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [advancing, setAdvancing] = useState(false);
  const refreshRef = useRef<() => void>(() => {});

  const refresh = useCallback(async () => {
    if (!gameId) return;
    try {
      const s = await gameApi.getState(gameId);
      setState(s);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch game state');
    }
  }, [gameId]);

  refreshRef.current = refresh;

  const advanceHour = useCallback(async () => {
    if (!gameId || advancing) return;
    setAdvancing(true);
    try {
      const s = await gameApi.advanceHour(gameId);
      setState(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to advance time');
    } finally {
      setAdvancing(false);
    }
  }, [gameId, advancing]);

  const advanceHours = useCallback(async (hours: number) => {
    if (!gameId || advancing) return;
    setAdvancing(true);
    try {
      const s = await gameApi.advanceHours(gameId, hours);
      setState(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to advance time');
    } finally {
      setAdvancing(false);
    }
  }, [gameId, advancing]);

  const advanceToClose = useCallback(async () => {
    if (!gameId || advancing) return;
    setAdvancing(true);
    try {
      const s = await gameApi.advanceToClose(gameId);
      setState(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to advance to close');
    } finally {
      setAdvancing(false);
    }
  }, [gameId, advancing]);

  const advanceToNextDay = useCallback(async () => {
    if (!gameId || advancing) return;
    setAdvancing(true);
    try {
      const s = await gameApi.advanceToNextDay(gameId);
      setState(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to advance to next day');
    } finally {
      setAdvancing(false);
    }
  }, [gameId, advancing]);

  const skipWeekend = useCallback(async () => {
    if (!gameId || advancing) return;
    setAdvancing(true);
    try {
      const s = await gameApi.skipWeekend(gameId);
      setState(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to skip weekend');
    } finally {
      setAdvancing(false);
    }
  }, [gameId, advancing]);

  return {
    state,
    setState,
    loading,
    setLoading,
    error,
    advancing,
    refresh,
    advanceHour,
    advanceHours,
    advanceToClose,
    advanceToNextDay,
    skipWeekend,
  };
}
