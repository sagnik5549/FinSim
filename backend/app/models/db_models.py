import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    BigInteger,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Game(Base):
    __tablename__ = "games"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_name = Column(String(100), nullable=False, default="Player")
    seed = Column(BigInteger, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")

    # Time state
    game_date = Column(Date, nullable=False)
    game_hour = Column(Integer, nullable=False, default=9)
    career_day = Column(Integer, nullable=False, default=1)
    quarter = Column(Integer, nullable=False, default=1)
    career_year = Column(Integer, nullable=False, default=1)
    market_status = Column(String(20), nullable=False, default="OPEN")

    # Financial state
    cash = Column(Float, nullable=False, default=1_00_00_00_000.0)
    starting_capital = Column(Float, nullable=False, default=1_00_00_00_000.0)
    quarterly_target = Column(Float, nullable=False, default=1_12_00_00_000.0)
    max_drawdown_limit = Column(Float, nullable=False, default=0.10)
    peak_portfolio_value = Column(
        Float,
        nullable=False,
        default=1_00_00_00_000.0,
    )

    # Career state
    career_level = Column(Integer, nullable=False, default=1)
    xp = Column(Integer, nullable=False, default=0)
    reputation = Column(Float, nullable=False, default=50.0)

    career_review_count = Column(Integer, nullable=False, default=0)
    career_failure_count = Column(Integer, nullable=False, default=0)
    last_review_result = Column(String(20), nullable=True)
    career_status = Column(
        String(20),
        nullable=False,
        default="ACTIVE",
    )

    # Leave state
    leave_balance = Column(Integer, nullable=False, default=60)
    leave_used = Column(Integer, nullable=False, default=0)
    leave_year = Column(Integer, nullable=False, default=1)
    on_leave = Column(Boolean, nullable=False, default=False)

    # Market state
    market_regime = Column(String(20), nullable=False, default="STABLE")
    regime_days_remaining = Column(Integer, nullable=False, default=15)

    nifty_value = Column(Float, nullable=False, default=24500.0)
    sensex_value = Column(Float, nullable=False, default=80500.0)
    bank_nifty_value = Column(Float, nullable=False, default=51000.0)
    india_vix_value = Column(Float, nullable=False, default=14.5)
    usdinr_value = Column(Float, nullable=False, default=83.5)
    gold_value = Column(Float, nullable=False, default=72000.0)
    nasdaq_value = Column(Float, nullable=False, default=17500.0)
    sp500_value = Column(Float, nullable=False, default=5450.0)

    # Risk state
    risk_warnings = Column(JSON, nullable=False, default=list)
    active_risk_level = Column(String(10), nullable=False, default="LOW")

    # Daily tracking
    daily_pnl = Column(Float, nullable=False, default=0.0)
    daily_open_portfolio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=False, default=0.0)

    # Notifications
    pending_notifications = Column(JSON, nullable=False, default=list)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    holdings = relationship(
        "Holding",
        back_populates="game",
        cascade="all, delete-orphan",
    )
    transactions = relationship(
        "Transaction",
        back_populates="game",
        cascade="all, delete-orphan",
    )
    stock_ticks = relationship(
        "StockTick",
        back_populates="game",
        cascade="all, delete-orphan",
    )
    market_ticks = relationship(
        "MarketTick",
        back_populates="game",
        cascade="all, delete-orphan",
    )
    news_items = relationship(
        "NewsItem",
        back_populates="game",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "GameEvent",
        back_populates="game",
        cascade="all, delete-orphan",
    )
    telemetry = relationship(
        "Telemetry",
        back_populates="game",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_games_status", "status"),
        Index("ix_games_game_date", "game_date"),
        Index("ix_games_career_day", "career_day"),
    )


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol = Column(String(10), nullable=False)
    name = Column(String(100), nullable=False)
    sector = Column(String(50), nullable=False)

    base_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    previous_price = Column(Float, nullable=False)

    daily_open = Column(Float, nullable=False)
    daily_high = Column(Float, nullable=False)
    daily_low = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False, default=0)

    # Fundamentals
    volatility = Column(Float, nullable=False)
    beta = Column(Float, nullable=False)
    growth = Column(Float, nullable=False)
    profitability = Column(Float, nullable=False)
    debt = Column(Float, nullable=False)
    valuation = Column(Float, nullable=False)

    # Dynamic simulation state
    sentiment = Column(Float, nullable=False, default=0.5)
    momentum = Column(Float, nullable=False, default=0.0)
    market_sensitivity = Column(Float, nullable=False, default=1.0)
    event_sensitivity = Column(Float, nullable=False, default=0.5)
    institutional_pressure = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "symbol",
            name="uq_game_stock",
        ),
        Index(
            "ix_stocks_game_symbol",
            "game_id",
            "symbol",
        ),
        Index(
            "ix_stocks_game_sector",
            "game_id",
            "sector",
        ),
    )


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    avg_buy_price = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, default=0.0)

    game = relationship(
        "Game",
        back_populates="holdings",
    )

    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "symbol",
            name="uq_holding",
        ),
        Index(
            "ix_holdings_game_symbol",
            "game_id",
            "symbol",
        ),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )

    career_day = Column(Integer, nullable=False)
    game_date = Column(Date, nullable=False)
    game_hour = Column(Integer, nullable=False)

    symbol = Column(String(10), nullable=False)
    name = Column(String(100), nullable=False)
    action = Column(String(4), nullable=False)

    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    fee = Column(Float, nullable=False, default=0.0)

    cash_before = Column(Float, nullable=False)
    cash_after = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    game = relationship(
        "Game",
        back_populates="transactions",
    )

    __table_args__ = (
        Index(
            "ix_transactions_game_day",
            "game_id",
            "career_day",
        ),
        Index(
            "ix_transactions_game_symbol",
            "game_id",
            "symbol",
        ),
        Index(
            "ix_transactions_game_action",
            "game_id",
            "action",
        ),
    )


class StockTick(Base):
    __tablename__ = "stock_ticks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )

    tick_index = Column(Integer, nullable=False)
    career_day = Column(Integer, nullable=False)
    game_hour = Column(Integer, nullable=False)
    symbol = Column(String(10), nullable=False)

    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    game = relationship(
        "Game",
        back_populates="stock_ticks",
    )

    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "tick_index",
            "symbol",
            name="uq_stock_tick",
        ),
        Index(
            "ix_stock_ticks_chart",
            "game_id",
            "symbol",
            "career_day",
            "game_hour",
        ),
        Index(
            "ix_stock_ticks_game_tick",
            "game_id",
            "tick_index",
        ),
    )


class MarketTick(Base):
    __tablename__ = "market_ticks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )

    tick_index = Column(Integer, nullable=False)
    career_day = Column(Integer, nullable=False)
    game_hour = Column(Integer, nullable=False)

    nifty = Column(Float, nullable=False)
    sensex = Column(Float, nullable=False)
    bank_nifty = Column(Float, nullable=False)
    india_vix = Column(Float, nullable=False)
    usdinr = Column(Float, nullable=False)
    gold = Column(Float, nullable=False)
    nasdaq = Column(Float, nullable=False)
    sp500 = Column(Float, nullable=False)

    market_regime = Column(String(20), nullable=False)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    game = relationship(
        "Game",
        back_populates="market_ticks",
    )

    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "tick_index",
            name="uq_market_tick",
        ),
        Index(
            "ix_market_ticks_game_day",
            "game_id",
            "career_day",
        ),
    )


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )

    career_day = Column(Integer, nullable=False)
    game_hour = Column(Integer, nullable=False)

    category = Column(String(30), nullable=False)
    priority = Column(String(10), nullable=False, default="NORMAL")

    headline = Column(String(300), nullable=False)
    body = Column(Text, nullable=True)

    affected_symbol = Column(String(10), nullable=True)
    affected_sector = Column(String(50), nullable=True)
    market_impact = Column(Float, nullable=False, default=0.0)

    is_read = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    game = relationship(
        "Game",
        back_populates="news_items",
    )

    __table_args__ = (
        Index(
            "ix_news_game_time",
            "game_id",
            "career_day",
            "game_hour",
        ),
        Index(
            "ix_news_game_priority",
            "game_id",
            "priority",
        ),
    )


class GameEvent(Base):
    __tablename__ = "game_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False, default="MEDIUM")

    affected_symbol = Column(String(10), nullable=True)
    affected_sector = Column(String(50), nullable=True)

    trigger_day = Column(Integer, nullable=False)
    trigger_hour = Column(Integer, nullable=False)

    duration_hours = Column(Integer, nullable=False, default=8)
    price_impact = Column(Float, nullable=False, default=0.0)

    narrative = Column(String(500), nullable=False)

    is_processed = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    follow_up_event_type = Column(String(50), nullable=True)
    follow_up_day = Column(Integer, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    game = relationship(
        "Game",
        back_populates="events",
    )

    __table_args__ = (
        Index(
            "ix_events_game_trigger",
            "game_id",
            "trigger_day",
            "trigger_hour",
        ),
        Index(
            "ix_events_game_active",
            "game_id",
            "is_active",
            "is_processed",
        ),
    )


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )

    tick_index = Column(Integer, nullable=False)
    career_day = Column(Integer, nullable=False)
    game_hour = Column(Integer, nullable=False)

    cash = Column(Float, nullable=False)
    portfolio_value = Column(Float, nullable=False)
    total_return_pct = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)

    holding_count = Column(Integer, nullable=False)
    trade_count_today = Column(Integer, nullable=False, default=0)
    largest_position_pct = Column(Float, nullable=False, default=0.0)

    market_regime = Column(String(20), nullable=False)
    reputation = Column(Float, nullable=False)
    target_progress = Column(Float, nullable=False)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    game = relationship(
        "Game",
        back_populates="telemetry",
    )

    __table_args__ = (
        Index(
            "ix_telemetry_game_day",
            "game_id",
            "career_day",
        ),
        Index(
            "ix_telemetry_game_tick",
            "game_id",
            "tick_index",
        ),
    )