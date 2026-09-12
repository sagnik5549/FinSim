import { useState, useEffect, useRef, useCallback } from 'react';
import type { GameState } from '../types/game';

export type SimulationSpeed = '1x' | '2x' | '5x';

const SPEED_INTERVALS: Record<SimulationSpeed, number> = {
  '1x': 2800,
  '2x': 1400,
  '5x': 700,
};

export interface FlashInfo {
  direction: 'UP' | 'DOWN';
  timestamp: number;
}

export function useLiveTicker({
  state,
  advancing,
  advanceHour,
  advanceToNextDay,
  skipWeekend,
}: {
  state: GameState | null;
  advancing: boolean;
  advanceHour: () => Promise<void>;
  advanceToNextDay: () => Promise<void>;
  skipWeekend: () => Promise<void>;
}) {
  const [isLive, setIsLive] = useState(false);
  const [speed, setSpeed] = useState<SimulationSpeed>('1x');
  const [autoNextDay, setAutoNextDay] = useState(true);
  const [flashMap, setFlashMap] = useState<Record<string, FlashInfo>>({});

  const previousPricesRef = useRef<Record<string, number>>({});
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const isAdvancingRef = useRef(advancing);
  isAdvancingRef.current = advancing;

  // Track price differences whenever state changes
  useEffect(() => {
    if (!state) return;

    const newFlashes: Record<string, FlashInfo> = {};
    const now = Date.now();

    // Check stocks
    if (state.market?.stocks) {
      for (const stock of state.market.stocks) {
        const prev = previousPricesRef.current[stock.symbol];
        if (prev !== undefined && prev !== null) {
          if (stock.current_price > prev) {
            newFlashes[stock.symbol] = { direction: 'UP', timestamp: now };
          } else if (stock.current_price < prev) {
            newFlashes[stock.symbol] = { direction: 'DOWN', timestamp: now };
          }
        }
        previousPricesRef.current[stock.symbol] = stock.current_price;
      }
    }

    // Check indices
    if (state.market?.indices) {
      for (const idx of state.market.indices) {
        const prev = previousPricesRef.current[idx.symbol];
        if (prev !== undefined && prev !== null) {
          if (idx.value > prev) {
            newFlashes[idx.symbol] = { direction: 'UP', timestamp: now };
          } else if (idx.value < prev) {
            newFlashes[idx.symbol] = { direction: 'DOWN', timestamp: now };
          }
        }
        previousPricesRef.current[idx.symbol] = idx.value;
      }
    }

    if (Object.keys(newFlashes).length > 0) {
      setFlashMap((existing) => ({
        ...existing,
        ...newFlashes,
      }));

      // Automatically clear these specific flashes after animation finishes (950ms)
      const clearTimer = setTimeout(() => {
        setFlashMap((curr) => {
          const updated = { ...curr };
          for (const key of Object.keys(newFlashes)) {
            if (updated[key]?.timestamp === now) {
              delete updated[key];
            }
          }
          return updated;
        });
      }, 950);

      return () => clearTimeout(clearTimer);
    }
  }, [state]);

  // Live Auto-Tick Simulation Loop
  useEffect(() => {
    if (!isLive || !state || state.status !== 'ACTIVE') {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    const interval = SPEED_INTERVALS[speed];

    const runTick = async () => {
      if (isAdvancingRef.current) return;

      const marketStatus = state.time.market_status;

      try {
        if (marketStatus === 'WEEKEND') {
          if (autoNextDay) {
            await skipWeekend();
          } else {
            setIsLive(false);
          }
        } else if (marketStatus === 'CLOSED') {
          if (autoNextDay) {
            await advanceToNextDay();
          } else {
            setIsLive(false);
          }
        } else {
          await advanceHour();
        }
      } catch (err) {
        console.error('Live tick advance failed:', err);
        // Pause to avoid infinite rapid errors
        setIsLive(false);
      }
    };

    timerRef.current = setTimeout(runTick, interval);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isLive, speed, state, autoNextDay, advanceHour, advanceToNextDay, skipWeekend]);

  const getFlashDirection = useCallback(
    (symbol: string): 'UP' | 'DOWN' | null => {
      return flashMap[symbol]?.direction || null;
    },
    [flashMap]
  );

  const toggleLive = useCallback(() => {
    setIsLive((prev) => !prev);
  }, []);

  return {
    isLive,
    setIsLive,
    toggleLive,
    speed,
    setSpeed,
    autoNextDay,
    setAutoNextDay,
    flashMap,
    getFlashDirection,
  };
}
