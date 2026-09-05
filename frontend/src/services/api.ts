import axios from 'axios';
import type { GameState, TradeResult, CandleData, QuarterlyReview } from '../types/game';

const API = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const gameApi = {
  newGame: async (playerName: string): Promise<{ game_id: string; message: string }> => {
    const { data } = await API.post('/game/new', { player_name: playerName });
    return data;
  },

  getState: async (gameId: string): Promise<GameState> => {
    const { data } = await API.get(`/game/state/${gameId}`);
    return data;
  },

  advanceHour: async (gameId: string): Promise<GameState> => {
    const { data } = await API.post('/game/advance-hour', { game_id: gameId, hours: 1 });
    return data;
  },

  advanceHours: async (gameId: string, hours: number): Promise<GameState> => {
    const { data } = await API.post('/game/advance-hours', { game_id: gameId, hours });
    return data;
  },

  advanceToClose: async (gameId: string): Promise<GameState> => {
    const { data } = await API.post('/game/advance-to-close', { game_id: gameId, hours: 1 });
    return data;
  },

  advanceToNextDay: async (gameId: string): Promise<GameState> => {
    const { data } = await API.post('/game/advance-next-business-day', { game_id: gameId, hours: 1 });
    return data;
  },

  skipWeekend: async (gameId: string): Promise<GameState> => {
    const { data } = await API.post('/game/skip-weekend', { game_id: gameId, hours: 1 });
    return data;
  },

  quarterlyReview: async (gameId: string): Promise<QuarterlyReview> => {
    const { data } = await API.post('/game/quarterly-review', { game_id: gameId, hours: 1 });
    return data;
  },

  listGames: async (): Promise<Array<{ id: string; player_name: string; status: string; career_day: number; created_at: string }>> => {
    const { data } = await API.get('/game/list');
    return data;
  },

  buy: async (gameId: string, symbol: string, quantity: number): Promise<TradeResult> => {
    const { data } = await API.post('/trade/buy', { game_id: gameId, symbol, quantity });
    return data;
  },

  sell: async (gameId: string, symbol: string, quantity: number): Promise<TradeResult> => {
    const { data } = await API.post('/trade/sell', { game_id: gameId, symbol, quantity });
    return data;
  },

  getCandles: async (gameId: string, symbol: string, days = 30): Promise<{ symbol: string; name: string; candles: CandleData[] }> => {
    const { data } = await API.get(`/market/${gameId}/${symbol}/candles`, { params: { days } });
    return data;
  },

  getPerformance: async (gameId: string) => {
    const { data } = await API.get(`/performance/${gameId}`);
    return data;
  },
};

export default gameApi;
