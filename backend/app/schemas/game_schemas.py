from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NewGameRequest(BaseModel):
    player_name: str = Field(default="Player", max_length=100)


class AdvanceHoursRequest(BaseModel):
    game_id: UUID
    hours: int = Field(default=1, ge=1, le=8)


class BuyRequest(BaseModel):
    game_id: UUID
    symbol: str = Field(min_length=1, max_length=10)
    quantity: int = Field(ge=1)


class SellRequest(BaseModel):
    game_id: UUID
    symbol: str = Field(min_length=1, max_length=10)
    quantity: int = Field(ge=1)


class LeaveRequest(BaseModel):
    game_id: UUID
    days: int = Field(ge=1, le=60)


class LoadGameRequest(BaseModel):
    game_id: UUID


class TimeInfo(BaseModel):
    game_date: str
    game_hour: int
    day_of_week: str
    career_day: int
    quarter: int
    career_year: int
    market_status: str
    working_hours_left: int


class FinancialsInfo(BaseModel):
    cash: float
    cash_cr: float
    invested_value: float
    invested_value_cr: float
    total_value: float
    total_value_cr: float
    starting_capital: float
    starting_capital_cr: float
    quarterly_target: float
    quarterly_target_cr: float
    total_pnl: float
    total_pnl_cr: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    daily_pnl: float
    daily_pnl_cr: float
    max_drawdown: float
    target_progress: float
    to_target: float
    to_target_cr: float
    target_met: bool
    portfolio_volatility: float


class CareerInfo(BaseModel):
    level: int
    role: str
    xp: int
    xp_to_next_level: int
    reputation: float
    leave_balance: int
    leave_used: int
    leave_year: int
    on_leave: bool
    career_status: str
    career_review_count: int
    career_failure_count: int
    last_review_result: Optional[str] = None


class IndexInfo(BaseModel):
    symbol: str
    name: str
    value: float
    prev_value: float
    change_pct: float


class StockInfo(BaseModel):
    symbol: str
    name: str
    sector: str
    current_price: float
    previous_price: float
    daily_open: float
    daily_high: float
    daily_low: float
    daily_return: float
    volume: int
    volatility: float
    beta: float
    sentiment: float
    momentum: float
    growth: float
    profitability: float
    debt: float
    valuation: float


class HoldingInfo(BaseModel):
    symbol: str
    name: str
    sector: str
    quantity: int
    avg_buy_price: float
    current_price: float
    current_value: float
    current_value_cr: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    daily_return: float


class RiskWarningInfo(BaseModel):
    code: str
    level: str
    message: str
    value: float
    limit: float
    symbol: Optional[str] = None
    sector: Optional[str] = None


class RiskInfo(BaseModel):
    overall_level: str
    risk_score: float
    warnings: list[RiskWarningInfo]
    drawdown_pct: float
    cash_ratio: float
    largest_position_pct: float
    sector_concentration: dict[str, float]
    portfolio_volatility: float


class NewsItemInfo(BaseModel):
    id: str
    category: str
    priority: str
    headline: str
    body: Optional[str] = None
    affected_symbol: Optional[str] = None
    affected_sector: Optional[str] = None
    market_impact: float
    career_day: int
    game_hour: int
    is_read: bool


class NotificationInfo(BaseModel):
    id: str
    level: str
    message: str
    category: str


class MarketInfo(BaseModel):
    regime: str
    indices: list[IndexInfo]
    stocks: list[StockInfo]


class GameStateResponse(BaseModel):
    game_id: str
    player_name: str
    status: str
    time: TimeInfo
    financials: FinancialsInfo
    career: CareerInfo
    market: MarketInfo
    holdings: list[HoldingInfo]
    risk: RiskInfo
    recent_news: list[NewsItemInfo]
    notifications: list[NotificationInfo]
    trade_count_today: int


class TradeResult(BaseModel):
    success: bool
    message: str
    symbol: str
    action: str
    quantity: int
    price: float
    total_value: float
    fee: float
    cash_after: float
    cash_after_cr: float
    realized_pnl: Optional[float] = None


class CandleData(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockCandlesResponse(BaseModel):
    symbol: str
    name: str
    candles: list[CandleData]


class TransactionInfo(BaseModel):
    id: str
    career_day: int
    game_date: str
    game_hour: int
    symbol: str
    name: str
    action: str
    quantity: int
    price: float
    total_value: float
    fee: float
    realized_pnl: Optional[float] = None
    created_at: str


class PerformanceData(BaseModel):
    total_return_pct: float
    benchmark_return_pct: float
    max_drawdown: float
    portfolio_volatility: float
    win_rate: float
    avg_trade_pnl: float
    best_trade_pnl: float
    worst_trade_pnl: float
    trade_count: int
    sector_attribution: dict[str, float]
    transactions: list[TransactionInfo]
    daily_portfolio_values: list[dict[str, Any]]


class QuarterlyReviewResponse(BaseModel):
    outcome: str
    final_return: float
    target_return: float
    max_drawdown: float
    reputation: float
    xp: int
    summary: str
    ceo_message: str
    xp_awarded: int
    reputation_change: float
    can_advance: bool = False
    next_level: Optional[int] = None
    next_role_title: Optional[str] = None
    capital_injection: Optional[float] = None
    capital_injection_cr: Optional[float] = None
    next_target_return: Optional[float] = None
    next_drawdown_limit: Optional[float] = None
    next_perks: list[str] = Field(default_factory=list)


class AdvanceLevelRequest(BaseModel):
    game_id: UUID


class AdvanceLevelResponse(BaseModel):
    success: bool
    message: str
    career_level: int
    role: str
    quarter: int
    starting_capital: float
    starting_capital_cr: float
    quarterly_target: float
    quarterly_target_cr: float
    cash_injected: float
    cash_injected_cr: float
    max_drawdown_limit: float
    state: GameStateResponse


class MLPredictionInfo(BaseModel):
    symbol: str
    name: str
    sector: str
    current_price: float
    predicted_price_1d: float
    predicted_return_pct_1d: float
    signal: str
    confidence_pct: float
    var_95_pct: float
    sharpe_alpha: float
    rsi_14: float
    macd_signal: str
    trend: str
    top_factors: list[dict[str, Any]]


class MLUniverseResponse(BaseModel):
    regime: str
    predictions: list[MLPredictionInfo]
    top_picks: list[str]
    market_sentiment_score: float
    model_timestamp: str


class MLForecastPoint(BaseModel):
    tick: int
    label: str
    predicted_price: float
    lower_bound: float
    upper_bound: float


class MLForecastResponse(BaseModel):
    symbol: str
    name: str
    current_price: float
    target_price: float
    predicted_return_pct: float
    signal: str
    confidence_pct: float
    var_95_pct: float
    sharpe_alpha: float
    indicators: dict[str, Any]
    forecast_path: list[MLForecastPoint]
    feature_importances: list[dict[str, Any]]
    rationale: str


class NewGameResponse(BaseModel):
    game_id: str
    message: str