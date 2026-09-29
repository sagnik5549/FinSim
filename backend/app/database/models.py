"""
Relational schema.

`games.snapshot` holds the authoritative engine state (JSON). The other tables
are normalised projections and append-only histories used for charts,
analytics and ML training; they are rewritten/rolled back consistently on
save/load.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _fk():
    return ForeignKey("games.id", ondelete="CASCADE")


class Player(Base):
    __tablename__ = "players"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Player")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Game(Base):
    __tablename__ = "games"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True)
    seed: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    level: Mapped[int] = mapped_column(Integer, default=1)
    game_time: Mapped[datetime] = mapped_column(DateTime)
    version: Mapped[int] = mapped_column(Integer, default=0)
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Stock(Base):
    __tablename__ = "stocks"
    __table_args__ = (UniqueConstraint("game_id", "symbol"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk(), index=True)
    symbol: Mapped[str] = mapped_column(String(12))
    name: Mapped[str] = mapped_column(String(80))
    sector: Mapped[str] = mapped_column(String(40))
    beta: Mapped[float] = mapped_column(Float)
    volatility: Mapped[float] = mapped_column(Float)
    growth: Mapped[float] = mapped_column(Float)
    profitability: Mapped[float] = mapped_column(Float)
    debt: Mapped[float] = mapped_column(Float)


class StockPrice(Base):
    """Hourly OHLCV candles for stocks and indices (symbol = ticker or index key)."""
    __tablename__ = "stock_prices"
    __table_args__ = (Index("ix_prices_game_symbol_t", "game_id", "symbol", "t"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk())
    symbol: Mapped[str] = mapped_column(String(12))
    t: Mapped[datetime] = mapped_column(DateTime)
    o: Mapped[float] = mapped_column(Float)
    h: Mapped[float] = mapped_column(Float)
    l: Mapped[float] = mapped_column(Float)
    c: Mapped[float] = mapped_column(Float)
    v: Mapped[int] = mapped_column(BigInteger, default=0)


class MarketStateRow(Base):
    __tablename__ = "market_states"
    __table_args__ = (Index("ix_market_states_game_date", "game_id", "date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk())
    date: Mapped[str] = mapped_column(String(10))
    regime: Mapped[str] = mapped_column(String(12))
    economy: Mapped[dict] = mapped_column(JSON)


class PortfolioRow(Base):
    __tablename__ = "portfolios"
    game_id: Mapped[str] = mapped_column(_fk(), primary_key=True)
    cash: Mapped[float] = mapped_column(Float)
    nav: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[float] = mapped_column(Float)
    max_drawdown: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class HoldingRow(Base):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("game_id", "symbol"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk(), index=True)
    symbol: Mapped[str] = mapped_column(String(12))
    qty: Mapped[int] = mapped_column(BigInteger)
    avg_cost: Mapped[float] = mapped_column(Float)


class TransactionRow(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_tx_game_t", "game_id", "t"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk())
    tx_id: Mapped[str] = mapped_column(String(20))
    t: Mapped[datetime] = mapped_column(DateTime)
    side: Mapped[str] = mapped_column(String(4))
    symbol: Mapped[str] = mapped_column(String(12))
    qty: Mapped[int] = mapped_column(BigInteger)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float)
    value: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(20))


class EventRow(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_game_t", "game_id", "t"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk())
    event_id: Mapped[str] = mapped_column(String(20))
    t: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(12))
    severity: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    impact: Mapped[float] = mapped_column(Float)
    symbols: Mapped[str] = mapped_column(Text, default="")
    sectors: Mapped[str] = mapped_column(Text, default="")


class NewsRow(Base):
    __tablename__ = "news"
    __table_args__ = (Index("ix_news_game_t", "game_id", "t"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk())
    news_id: Mapped[str] = mapped_column(String(20))
    t: Mapped[datetime] = mapped_column(DateTime)
    headline: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(12))
    tone: Mapped[str] = mapped_column(String(10))
    severity: Mapped[int] = mapped_column(Integer)
    symbols: Mapped[str] = mapped_column(Text, default="")


class EmployeeRow(Base):
    __tablename__ = "employees"
    __table_args__ = (UniqueConstraint("game_id", "char_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk(), index=True)
    char_id: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(60))
    skills: Mapped[dict] = mapped_column(JSON)
    trust: Mapped[float] = mapped_column(Float)
    loyalty: Mapped[float] = mapped_column(Float)
    stress: Mapped[float] = mapped_column(Float)
    performance: Mapped[float] = mapped_column(Float)
    core: Mapped[bool] = mapped_column(Boolean, default=True)


class CareerProgressRow(Base):
    __tablename__ = "career_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk(), index=True)
    quarter: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(60))
    outcome: Mapped[str] = mapped_column(String(20))
    return_pct: Mapped[float] = mapped_column(Float)
    max_drawdown: Mapped[float] = mapped_column(Float)
    date: Mapped[str] = mapped_column(String(10))


class CareerLevelRow(Base):
    __tablename__ = "career_levels"
    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(60))
    target_return: Mapped[float] = mapped_column(Float)
    max_drawdown: Mapped[float] = mapped_column(Float)
    unlocks: Mapped[list] = mapped_column(JSON)


class ClientRow(Base):
    """Institutional client mandates (introduced from level 4)."""
    __tablename__ = "clients"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    capital: Mapped[float] = mapped_column(Float)
    risk_tolerance: Mapped[str] = mapped_column(String(10))
    target_return: Mapped[float] = mapped_column(Float)
    horizon_years: Mapped[int] = mapped_column(Integer)
    sector_restrictions: Mapped[list] = mapped_column(JSON)
    preferences: Mapped[list] = mapped_column(JSON)
    min_level: Mapped[int] = mapped_column(Integer)


class GameDayRow(Base):
    __tablename__ = "game_days"
    __table_args__ = (Index("ix_game_days_game_date", "game_id", "date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk())
    date: Mapped[str] = mapped_column(String(10))
    open_nav: Mapped[float] = mapped_column(Float)
    close_nav: Mapped[float] = mapped_column(Float)
    bench_close: Mapped[float] = mapped_column(Float)
    regime: Mapped[str] = mapped_column(String(12))
    events: Mapped[int] = mapped_column(Integer)
    reputation: Mapped[float] = mapped_column(Float)


class TelemetryRow(Base):
    __tablename__ = "telemetry"
    __table_args__ = (Index("ix_telemetry_game_t", "game_id", "t"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk())
    player_id: Mapped[str] = mapped_column(String(40))
    t: Mapped[datetime] = mapped_column(DateTime)
    trigger: Mapped[str] = mapped_column(String(30))
    day: Mapped[int] = mapped_column(Integer)
    portfolio_value: Mapped[float] = mapped_column(Float)
    drawdown: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    market_regime: Mapped[str] = mapped_column(String(12))
    payload: Mapped[dict] = mapped_column(JSON)


class LeaveRecordRow(Base):
    __tablename__ = "leave_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk(), index=True)
    start: Mapped[datetime] = mapped_column(DateTime)
    end: Mapped[datetime] = mapped_column(DateTime)
    days: Mapped[int] = mapped_column(Integer)


class SaveSlot(Base):
    __tablename__ = "save_slots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(_fk(), index=True)
    player_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(80))
    game_time: Mapped[datetime] = mapped_column(DateTime)
    summary: Mapped[dict] = mapped_column(JSON)
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


CLIENTS = [
    {"id": "apex-pension", "name": "Apex Pension Fund", "capital": 500e7, "risk_tolerance": "LOW",
     "target_return": 0.08, "horizon_years": 5, "sector_restrictions": ["Defence"], "preferences": ["Dividends"],
     "min_level": 4},
    {"id": "saraswati-endowment", "name": "Saraswati University Endowment", "capital": 300e7,
     "risk_tolerance": "MEDIUM", "target_return": 0.10, "horizon_years": 10, "sector_restrictions": [],
     "preferences": ["ESG"], "min_level": 4},
    {"id": "meghna-family", "name": "Meghna Family Office", "capital": 200e7, "risk_tolerance": "HIGH",
     "target_return": 0.18, "horizon_years": 3, "sector_restrictions": [], "preferences": ["Growth"],
     "min_level": 5},
]


def seed_static(session_factory) -> None:
    from app.simulation.constants import CAREER_LEVELS

    with session_factory() as db:
        if db.get(CareerLevelRow, 1) is None:
            for lvl, cfg in CAREER_LEVELS.items():
                db.add(CareerLevelRow(level=lvl, title=cfg["title"], target_return=cfg["target_return"],
                                      max_drawdown=cfg["max_drawdown"], unlocks=cfg["unlocks"]))
        for c in CLIENTS:
            if db.get(ClientRow, c["id"]) is None:
                db.add(ClientRow(**c))
        db.commit()
