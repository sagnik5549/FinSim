// Mirrors backend/app/services/serializers.py. The backend is authoritative;
// these are read-only views.

export type MarketStatus = 'OPEN' | 'CLOSED' | 'WEEKEND' | 'PRE_MARKET'

export interface Clock {
  game_date: string
  game_hour: number
  game_minute: number
  day_of_week: string
  market_status: MarketStatus
  career_day: number
  quarter_day: number
  quarter_days: number
  quarter: number
  career_year: number
  working_day: boolean
  is_on_leave: boolean
  hours_to_close: number
  iso: string
  label: string
  time: string
}

export interface CareerSummary {
  firm: string
  level: number
  title: string
  xp: number
  xp_level_start: number
  xp_next: number
  reputation: number
  status: 'ACTIVE' | 'REVIEW' | 'TERMINATED'
  warning_level: number
  risk_profile: string
  quarter_index: number
  quarter_start: string
  quarter_end: string
  target_value: number
  target_return: number
  max_drawdown_limit: number
  risk_violations: number
  ignored_violations: number
  exceptions_granted: number
  compliance_strikes: number
  time_progress: number
  unlocks: string[]
  next_title: string | null
  delegate: string | null
}

export interface PortfolioSummary {
  starting_capital: number
  cash: number
  invested: number
  value: number
  pnl: number
  return_pct: number
  day_pnl: number
  day_pnl_pct: number
  realized_pnl: number
  unrealized_pnl: number
  fees_paid: number
  max_drawdown: number
  drawdown: number
  peak_value: number
  target_value: number
  target_progress: number
  volatility: number
  beta: number
}

export interface HoldingRow {
  symbol: string
  name: string
  sector: string
  qty: number
  avg_cost: number
  price: number
  value: number
  weight: number
  pnl: number
  pnl_pct: number
  day_change_pct: number
  day_pnl: number
  opened_at: string
}

export interface IndexRow {
  key: string
  name: string
  kind: string
  value: number
  prev_close: number
  change_pct: number
  spark: number[]
}

export interface StockRow {
  symbol: string
  name: string
  sector: string
  price: number
  prev_close: number
  change: number
  change_pct: number
  week_change_pct: number
  day_high: number
  day_low: number
  open: number
  volume: number
  prev_volume: number
  volatility: number
  beta: number
  momentum: number
  pe: number | null
  valuation: number
  sentiment: number
  sentiment_label: string
  risk: number
  market_cap_cr: number
  spark: number[]
  held: boolean
}

export interface NewsItem {
  id: string
  time: string
  headline: string
  body: string
  category: 'COMPANY' | 'MACRO' | 'MARKET' | 'FIRM'
  tone: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL'
  severity: number
  symbols: string[]
  sectors?: string[]
  event_id?: string | null
}

export interface Message {
  id: string
  time: string
  sender: string
  subject: string
  lines: string[]
  priority: 'NORMAL' | 'HIGH' | 'CRITICAL'
  read: boolean
}

export interface Notification {
  id: string
  time: string
  kind: string
  title: string
  body: string
  read: boolean
}

export type PopupType =
  | 'DAILY_REPORT'
  | 'WEEKEND_REPORT'
  | 'LEAVE_REPORT'
  | 'RISK_WARNING'
  | 'DIALOGUE'
  | 'REVIEW'

export interface Popup {
  id: string
  type: PopupType
  created: string
  blocking: boolean
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: any
}

export interface Opportunity {
  id: string
  kind: string
  symbol: string
  name: string
  qty: number
  price: number
  market_price: number
  discount: number
  effective_discount: number
  value: number
  created: string
  expires_at: string
  status: 'OPEN' | 'ACCEPTED' | 'EXPIRED' | 'DECLINED'
  seller: string
  minutes_left: number
}

export interface RiskWarning {
  id: string
  rule: string
  subject: string
  value: number
  limit: number
  created: string
  status: string
  during_leave: boolean
}

export interface Breach {
  rule: string
  subject: string
  value: number
  limit: number
  excepted: boolean
}

export interface RiskSummary {
  score: number
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  nav: number
  cash_ratio: number
  invested_ratio: number
  drawdown: number
  max_drawdown: number
  volatility: number
  beta: number
  var_95: number
  largest_position: { symbol: string | null; weight: number }
  stock_weights: Record<string, number>
  sector_weights: Record<string, number>
  limits: { max_single_stock: number; max_sector: number; max_drawdown: number; min_cash: number }
  breaches: Breach[]
  near_limits: Breach[]
  warnings: RiskWarning[]
  exceptions: { rule: string; subject: string; until: string }[]
}

export interface CalendarItem {
  id: string
  time: string
  kind: 'EARNINGS' | 'ECON_DATA' | 'POLICY' | 'CEO_MEETING'
  title: string
  symbol: string | null
  consensus?: number
  desk_forecast?: number
}

export interface LeaveInfo {
  allowance: number
  used: number
  remaining: number
  is_on_leave: boolean
  year: number
  records: { start: string; end: string; business_days: number }[]
}

export interface NavPoint {
  t: string
  nav: number
  bench: number
}

export interface TeamBrief {
  id: string
  name: string
  role: string
  avatar: string
  trust: number
  stress: number
}

export interface ResearchReport {
  id: string
  symbol: string
  time: string
  depth: 'QUICK' | 'DEEP'
  analyst: string
  est_fair_value: number
  price_at: number
  rating: 'BUY' | 'HOLD' | 'SELL'
  confidence: number
  earnings_view: string | null
  red_flags: string[]
  notes: string[]
}

export interface Thesis {
  id: string
  symbol: string
  stance: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  text: string
  time: string
  price_at: number
}

export interface Transaction {
  id: string
  time: string
  side: 'BUY' | 'SELL'
  symbol: string
  qty: number
  price: number
  fee: number
  value: number
  realized_pnl: number
  source: string
}

export interface LastTick {
  t: string | null
  paths: Record<string, number[]>
}

export interface GameState {
  game_id: string
  seed: number
  version: number
  clock: Clock
  career: CareerSummary
  portfolio: PortfolioSummary
  holdings: HoldingRow[]
  indices: IndexRow[]
  stocks: StockRow[]
  news: NewsItem[]
  messages: Message[]
  notifications: Notification[]
  popups: Popup[]
  opportunities: Opportunity[]
  risk: RiskSummary
  calendar: CalendarItem[]
  leave: LeaveInfo
  nav_series: NavPoint[]
  team: TeamBrief[]
  research: ResearchReport[]
  theses: Thesis[]
  transactions: Transaction[]
  stats: { hours_worked: number; hours_skipped: number; trades: number; research_count: number }
  last_tick: LastTick | null
}

export interface Candle {
  t: string
  o: number
  h: number
  l: number
  c: number
  v: number
}

export interface Indicators {
  sma20: (number | null)[]
  sma50: (number | null)[]
  ema20: (number | null)[]
  bb_upper: (number | null)[]
  bb_lower: (number | null)[]
  rsi14: (number | null)[]
  macd: (number | null)[]
  macd_signal: (number | null)[]
  macd_hist: (number | null)[]
  atr14: (number | null)[]
}

export interface Fundamentals {
  growth: number
  profitability: number
  debt: number
  valuation: number
  pe: number | null
  eps: number
  beta: number
  base_volatility: number
  event_sensitivity: number
  about: string
  market_cap_cr: number
  institutional_flow: 'BUYING' | 'SELLING' | 'NEUTRAL'
}

export interface SymbolDetail {
  symbol: string
  tf: '1h' | '1d'
  candles: Candle[]
  indicators: Indicators
  stock?: StockRow
  index?: { key: string; name: string; value: number; change_pct: number }
  fundamentals?: Fundamentals
  news?: NewsItem[]
  events?: { id: string; type: string; title: string; severity: number; started_at: string; active: boolean }[]
  calendar?: CalendarItem[]
  research?: ResearchReport[]
  theses?: Thesis[]
  position?: HoldingRow | null
}

export interface Quote {
  side: 'BUY' | 'SELL'
  symbol: string
  name: string
  qty: number
  market_price: number
  exec_price: number
  impact_pct: number
  value: number
  fee: number
  total: number
  cash_before: number
  cash_after: number
  position_after: number
  weight_after: number
  realized_pnl: number
  warnings: string[]
  sector_after?: number
}

export interface ActionResponse<R = unknown> {
  result: R
  state: GameState
}

export interface SaveSlot {
  id: number
  game_id: string
  name: string
  game_time: string
  created_at: string
  summary: { nav: number; level: number; title: string; reputation: number; date: string; quarter: number }
}

export type Page =
  | 'dashboard'
  | 'markets'
  | 'portfolio'
  | 'research'
  | 'trading'
  | 'news'
  | 'team'
  | 'career'
  | 'performance'
  | 'stock'
