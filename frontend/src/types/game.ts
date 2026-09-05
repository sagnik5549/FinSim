/* All game types mirroring backend Pydantic schemas */

export interface TimeInfo {
  game_date: string;
  game_hour: number;
  day_of_week: string;
  career_day: number;
  quarter: number;
  career_year: number;
  market_status: 'PRE_MARKET' | 'OPEN' | 'CLOSED' | 'WEEKEND';
  working_hours_left: number;
}

export interface FinancialsInfo {
  cash: number;
  cash_cr: number;
  invested_value: number;
  invested_value_cr: number;
  total_value: number;
  total_value_cr: number;
  starting_capital: number;
  starting_capital_cr: number;
  quarterly_target: number;
  quarterly_target_cr: number;
  total_pnl: number;
  total_pnl_cr: number;
  total_return_pct: number;
  realized_pnl: number;
  unrealized_pnl: number;
  daily_pnl: number;
  daily_pnl_cr: number;
  max_drawdown: number;
  target_progress: number;
  to_target: number;
  to_target_cr: number;
  target_met: boolean;
  portfolio_volatility: number;
}

export interface CareerInfo {
  level: number;
  role: string;
  xp: number;
  xp_to_next_level: number;
  reputation: number;
  leave_balance: number;
  leave_used: number;
  on_leave: boolean;
}

export interface IndexInfo {
  symbol: string;
  name: string;
  value: number;
  prev_value: number;
  change_pct: number;
}

export interface StockInfo {
  symbol: string;
  name: string;
  sector: string;
  current_price: number;
  previous_price: number;
  daily_open: number;
  daily_high: number;
  daily_low: number;
  daily_return: number;
  volume: number;
  volatility: number;
  beta: number;
  sentiment: number;
  momentum: number;
  growth: number;
  profitability: number;
  debt: number;
  valuation: number;
}

export interface MarketInfo {
  regime: 'BULL' | 'STABLE' | 'VOLATILE' | 'BEAR' | 'CRISIS';
  indices: IndexInfo[];
  stocks: StockInfo[];
}

export interface HoldingInfo {
  symbol: string;
  name: string;
  sector: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  current_value: number;
  current_value_cr: number;
  cost_basis: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  daily_return: number;
}

export interface RiskWarningInfo {
  code: string;
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  message: string;
  value: number;
  limit: number;
  symbol?: string;
  sector?: string;
}

export interface RiskInfo {
  overall_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_score: number;
  warnings: RiskWarningInfo[];
  drawdown_pct: number;
  cash_ratio: number;
  largest_position_pct: number;
  sector_concentration: Record<string, number>;
  portfolio_volatility: number;
}

export interface NewsItemInfo {
  id: string;
  category: 'COMPANY' | 'MACRO' | 'MARKET' | 'CEO';
  priority: 'BREAKING' | 'HIGH' | 'NORMAL' | 'LOW';
  headline: string;
  body?: string;
  affected_symbol?: string;
  affected_sector?: string;
  market_impact: number;
  career_day: number;
  game_hour: number;
  is_read: boolean;
}

export interface NotificationInfo {
  id: string;
  level: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;
  category: string;
}

export interface GameState {
  game_id: string;
  player_name: string;
  status: 'ACTIVE' | 'COMPLETED' | 'FAILED';
  time: TimeInfo;
  financials: FinancialsInfo;
  career: CareerInfo;
  market: MarketInfo;
  holdings: HoldingInfo[];
  risk: RiskInfo;
  recent_news: NewsItemInfo[];
  notifications: NotificationInfo[];
  trade_count_today: number;
}

export interface TradeResult {
  success: boolean;
  message: string;
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  total_value: number;
  fee: number;
  cash_after: number;
  cash_after_cr: number;
  realized_pnl?: number;
}

export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface QuarterlyReview {
  outcome: 'PROMOTED' | 'TARGET_ACHIEVED' | 'WARNING' | 'FAILED' | 'TERMINATED';
  final_return: number;
  target_return: number;
  max_drawdown: number;
  reputation: number;
  xp: number;
  summary: string;
  ceo_message: string;
  xp_awarded: number;
  reputation_change: number;
}

export type ActiveScreen =
  | 'dashboard'
  | 'markets'
  | 'portfolio'
  | 'research'
  | 'trading'
  | 'news'
  | 'team'
  | 'career'
  | 'performance';
