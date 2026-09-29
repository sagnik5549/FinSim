"""
Authoritative game state.

The whole simulation operates on a single `GameState` tree. It is serialised to
JSON and persisted after every mutating action, so a browser refresh or server
restart resumes exactly where the game left off. High-volume append-only data
(price candles, telemetry, the full news archive) is flushed to relational
tables through `outbox` instead of living in the snapshot.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, PrivateAttr


class StockState(BaseModel):
    symbol: str
    name: str
    sector: str
    about: str = ""
    price: float
    prev_close: float
    day_open: float
    day_high: float
    day_low: float
    volume_today: float = 0.0
    prev_volume: float = 0.0
    avg_hourly_volume: float
    shares_cr: float
    volatility: float  # base daily volatility
    beta: float
    growth: float
    profitability: float
    debt: float
    valuation: float  # 0 cheap .. 1 expensive (derived from P/E vs sector)
    eps: float
    fair_value: float  # HIDDEN: intrinsic value the market slowly gravitates to
    earnings_quality: float  # HIDDEN: drives next earnings surprise (-1..1)
    sentiment: float = 0.0  # -1..1
    momentum: float = 0.0  # EMA of recent returns
    institutional_pressure: float = 0.0  # -1..1 persistent flow
    event_sensitivity: float = 0.6
    realized_vol: float = 0.0  # rolling daily realised volatility estimate
    pending_gap: float = 0.0  # log-return applied at next open (overnight/weekend news)
    spark: list[float] = Field(default_factory=list)  # last ~40 hourly closes
    week_ago_price: float = 0.0


class IndexState(BaseModel):
    key: str
    name: str
    kind: str
    value: float
    prev_close: float
    day_open: float
    spark: list[float] = Field(default_factory=list)


class EconomyState(BaseModel):
    inflation: float = 5.1  # CPI %, y/y
    gdp_growth: float = 6.8
    policy_rate: float = 6.50
    oil: float = 82.0  # USD/bbl
    rate_pressure: float = 0.0  # -1 dovish .. +1 hawkish
    oil_shock: float = 0.0  # decaying shock factor
    global_risk: float = 0.0  # decaying global risk-on (+) / risk-off (-) factor
    inr_shock: float = 0.0


class MarketState(BaseModel):
    regime: str = "STABLE"  # HIDDEN
    regime_days: int = 0
    regime_len: int = 10
    market_level: float = 0.0  # cumulative log market factor
    global_level: float = 0.0
    sector_sentiment: dict[str, float] = Field(default_factory=dict)
    sector_level: dict[str, float] = Field(default_factory=dict)
    economy: EconomyState = Field(default_factory=EconomyState)
    event_intensity: float = 1.0  # director-controlled multiplier (bounded)


class Holding(BaseModel):
    symbol: str
    qty: int
    avg_cost: float
    opened_at: datetime
    realized_pnl: float = 0.0


class Transaction(BaseModel):
    id: str
    time: datetime
    side: str  # BUY / SELL
    symbol: str
    qty: int
    price: float
    fee: float
    value: float
    realized_pnl: float = 0.0
    source: str = "PLAYER"  # PLAYER / BLOCK_DEAL / RISK_REDUCTION / DELEGATE


class NavPoint(BaseModel):
    t: datetime
    nav: float
    bench: float  # BHARAT 50 value


class DailyRecord(BaseModel):
    date: str
    open_nav: float
    close_nav: float
    bench_open: float
    bench_close: float
    events: int = 0


class Portfolio(BaseModel):
    cash: float
    holdings: dict[str, Holding] = Field(default_factory=dict)
    realized_pnl: float = 0.0
    fees_paid: float = 0.0
    quarter_start_value: float
    quarter_start_bench: float
    peak_value: float
    max_drawdown: float = 0.0
    day_start_value: float
    hourly_nav: list[NavPoint] = Field(default_factory=list)
    daily: list[DailyRecord] = Field(default_factory=list)


class MarketEvent(BaseModel):
    id: str
    type: str
    category: str  # company / macro / market
    severity: int  # 1..5
    title: str
    narrative: str
    affected_symbols: list[str] = Field(default_factory=list)
    affected_sectors: list[str] = Field(default_factory=list)
    probability: float = 0.0
    market_impact: float = 0.0  # headline expected log-return impact
    impacts: dict[str, float] = Field(default_factory=dict)  # per-symbol total log-return impact
    vol_boost: float = 0.0  # extra volatility multiplier while active
    jump_fraction: float = 0.5
    duration_hours: int = 8
    remaining_hours: int = 8
    started_at: datetime
    chain_id: Optional[str] = None
    chain_stage: int = 0
    follow_up_events: list[str] = Field(default_factory=list)
    active: bool = True


class ScheduledEvent(BaseModel):
    id: str
    time: datetime
    kind: str  # EARNINGS / ECON_DATA / POLICY / CEO_MEETING / CHAIN
    title: str
    symbol: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    public: bool = True
    processed: bool = False


class NewsItem(BaseModel):
    id: str
    time: datetime
    headline: str
    body: str
    category: str  # COMPANY / MACRO / MARKET / FIRM
    tone: str  # POSITIVE / NEGATIVE / NEUTRAL
    severity: int = 1
    symbols: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    event_id: Optional[str] = None


class Message(BaseModel):
    id: str
    time: datetime
    sender: str  # character id
    subject: str
    lines: list[str]
    priority: str = "NORMAL"  # NORMAL / HIGH / CRITICAL
    read: bool = False


class Notification(BaseModel):
    id: str
    time: datetime
    kind: str  # MARKET_ALERT / RISK_WARNING / TARGET_UPDATE / BREAKING / CEO_MESSAGE / TRADE / OPPORTUNITY
    title: str
    body: str
    read: bool = False


class Popup(BaseModel):
    id: str
    type: str  # DAILY_REPORT / WEEKEND_REPORT / LEAVE_REPORT / RISK_WARNING / DIALOGUE / REVIEW / TERMINATED
    created: datetime
    blocking: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class Opportunity(BaseModel):
    id: str
    kind: str  # BLOCK_DEAL
    symbol: str
    qty: int
    price: float
    discount: float
    created: datetime
    expires_at: datetime
    status: str = "OPEN"  # OPEN / ACCEPTED / EXPIRED / DECLINED
    seller: str = ""
    informed_seller: bool = False  # HIDDEN: seller knows about upcoming bad news


class RiskWarning(BaseModel):
    id: str
    rule: str  # SINGLE_STOCK / SECTOR / DRAWDOWN / CASH
    subject: str  # symbol / sector / "PORTFOLIO"
    value: float
    limit: float
    created: datetime
    status: str = "OPEN"  # OPEN / REDUCED / EXCEPTION_GRANTED / IGNORED / CLEARED / EXPIRED
    exception_requested: bool = False
    resolved_at: Optional[datetime] = None
    during_leave: bool = False


class RiskException(BaseModel):
    rule: str
    subject: str
    until: datetime


class ResearchReport(BaseModel):
    id: str
    symbol: str
    time: datetime
    depth: str  # QUICK / DEEP
    analyst: str
    est_fair_value: float
    price_at: float
    rating: str  # BUY / HOLD / SELL
    confidence: float
    earnings_view: Optional[str] = None
    red_flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Thesis(BaseModel):
    id: str
    symbol: str
    stance: str  # BULLISH / BEARISH / NEUTRAL
    text: str
    time: datetime
    price_at: float


class Character(BaseModel):
    id: str
    name: str
    role: str
    avatar: str
    skills: dict[str, int]  # 0..100
    trust: float = 60.0
    loyalty: float = 60.0
    stress: float = 20.0
    performance: float = 60.0
    personality: str = ""
    salary_lakh: float = 0.0
    core: bool = True  # firm executive vs hired team member


class ReviewRecord(BaseModel):
    quarter: int
    level: int
    title: str
    outcome: str
    start_value: float
    end_value: float
    return_pct: float
    target_pct: float
    max_drawdown: float
    reputation_change: float
    date: str


class Career(BaseModel):
    level: int = 1
    title: str = "Head of Investments"
    xp: int = 0
    reputation: float = 60.0
    risk_profile: str = "MEDIUM"
    status: str = "ACTIVE"  # ACTIVE / REVIEW / TERMINATED
    warning_level: int = 0  # 0 none, 1 warning, 2 final warning
    quarter_index: int = 1
    quarter_start: datetime
    quarter_end: datetime  # after this moment the quarterly review fires
    quarter_start_day: int = 1
    target_value: float
    target_return: float
    max_drawdown_limit: float
    risk_violations: int = 0
    ignored_violations: int = 0
    exceptions_granted: int = 0
    compliance_strikes: int = 0
    dd_breach_warned: bool = False
    reputation_at_quarter_start: float = 60.0
    history: list[ReviewRecord] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)  # major decisions log
    milestones_hit: list[str] = Field(default_factory=list)
    last_review: Optional[dict[str, Any]] = None


class LeaveRecord(BaseModel):
    start: datetime
    end: datetime
    business_days: int


class LeaveState(BaseModel):
    allowance: int = 60
    used: int = 0
    year: int = 1
    is_on_leave: bool = False
    current_streak: int = 0
    records: list[LeaveRecord] = Field(default_factory=list)


class PlayerStats(BaseModel):
    hours_worked: int = 0
    hours_skipped: int = 0
    trades: int = 0
    buys: int = 0
    sells: int = 0
    research_count: int = 0
    trades_after_loss: int = 0
    trades_after_news: int = 0
    block_deals: int = 0
    wins: int = 0
    losses: int = 0
    closed_trades: list[dict[str, Any]] = Field(default_factory=list)  # {symbol, pnl, pct}
    behavior_profile: str = "BALANCED"  # HIDDEN classification
    behavior_scores: dict[str, float] = Field(default_factory=dict)


class DirectorState(BaseModel):
    difficulty: float = 1.0  # 0.8 .. 1.2
    tension: float = 0.0
    last_decision: dict[str, Any] = Field(default_factory=dict)
    model_source: str = "rules"


class TickPaths(BaseModel):
    """Intra-hour 5-minute path of the most recent simulated hour (for live chart replay)."""
    t: Optional[datetime] = None
    paths: dict[str, list[float]] = Field(default_factory=dict)


class GameState(BaseModel):
    id: str
    seed: int
    version: int = 0
    rng_state: dict[str, Any]
    created_at: datetime
    start_time: datetime
    now: datetime
    market: MarketState
    stocks: dict[str, StockState]
    indices: dict[str, IndexState]
    portfolio: Portfolio
    transactions: list[Transaction] = Field(default_factory=list)
    events: list[MarketEvent] = Field(default_factory=list)
    scheduled: list[ScheduledEvent] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)
    messages: list[Message] = Field(default_factory=list)
    notifications: list[Notification] = Field(default_factory=list)
    popups: list[Popup] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    risk_warnings: list[RiskWarning] = Field(default_factory=list)
    risk_exceptions: list[RiskException] = Field(default_factory=list)
    research: list[ResearchReport] = Field(default_factory=list)
    theses: list[Thesis] = Field(default_factory=list)
    team: dict[str, Character] = Field(default_factory=dict)
    career: Career
    leave: LeaveState = Field(default_factory=LeaveState)
    stats: PlayerStats = Field(default_factory=PlayerStats)
    director: DirectorState = Field(default_factory=DirectorState)
    last_tick: TickPaths = Field(default_factory=TickPaths)
    counters: dict[str, int] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)

    # Not persisted in the snapshot: rows waiting to be appended to DB tables.
    _outbox: dict[str, list[dict[str, Any]]] = PrivateAttr(default_factory=dict)

    def outbox(self, table: str) -> list[dict[str, Any]]:
        return self._outbox.setdefault(table, [])

    def drain_outbox(self) -> dict[str, list[dict[str, Any]]]:
        out, self._outbox = self._outbox, {}
        return out

    def next_id(self, prefix: str) -> str:
        n = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = n
        return f"{prefix}-{n:05d}"
