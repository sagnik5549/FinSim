"""
Pydantic schemas for all API request/response models.
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Requests ────────────────────────────────────────────────────────────────

class NewGameRequest(BaseModel):
    player_name: str = Field(default="Player", max_length=100)


class AdvanceHoursRequest(BaseModel):
    game_id: str
    hours: int = Field(default=1, ge=1, le=8)


class BuyRequest(BaseModel):
    game_id: str
    symbol: str
    quantity: int = Field(ge=1)


class SellRequest(BaseModel):
    game_id: str
    symbol: str
    quantity: int = Field(ge=1)


class LeaveRequest(BaseModel):
    game_id: str
    days: int = Field(ge=1, le=60)


class LoadGameRequest(BaseModel):
    game_id: str


# ─── Responses ───────────────────────────────────────────────────────────────

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
    on_leave: bool


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
    body: Optional[str]
    affected_symbol: Optional[str]
    affected_sector: Optional[str]
    market_impact: float
    career_day: int
    game_hour: int
    is_read: bool


class NotificationInfo(BaseModel):
    id: str
    level: str          # INFO, WARNING, CRITICAL
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
    time: str          # YYYY-MM-DD or tick index as date string
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
    realized_pnl: Optional[float]
    created_at: str


class PerformanceData(BaseModel):
    total_return_pct: float
    benchmark_return_pct: float      # NIFTY return over same period
    max_drawdown: float
    portfolio_volatility: float
    win_rate: float                  # % of profitable trades
    avg_trade_pnl: float
    best_trade_pnl: float
    worst_trade_pnl: float
    trade_count: int
    sector_attribution: dict[str, float]
    transactions: list[TransactionInfo]
    daily_portfolio_values: list[dict]  # [{day, value}]


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


class NewGameResponse(BaseModel):
    game_id: str
    message: str
