"""
Persistence for GameState: authoritative JSON snapshot + relational projections.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.database import models as m
from app.simulation import portfolio_engine as pe
from app.simulation.state import GameState

_TS_FIELDS = {"t", "start", "end"}


def _parse_ts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for r in rows:
        for k in _TS_FIELDS & r.keys():
            if isinstance(r[k], str):
                r[k] = datetime.fromisoformat(r[k])
    return rows


def save(db: Session, state: GameState, player_id: str) -> None:
    out = state.drain_outbox()
    state.version += 1
    snap = state.model_dump(mode="json")
    row = db.get(m.Game, state.id)
    if row is None:
        row = m.Game(id=state.id, player_id=player_id, seed=state.seed, game_time=state.now, snapshot=snap,
                     status=state.career.status, level=state.career.level, version=state.version)
        db.add(row)
        db.flush()
        db.execute(insert(m.Stock), [
            {"game_id": state.id, "symbol": s.symbol, "name": s.name, "sector": s.sector, "beta": s.beta,
             "volatility": s.volatility, "growth": s.growth, "profitability": s.profitability, "debt": s.debt}
            for s in state.stocks.values()])
    else:
        row.snapshot = snap
        row.game_time = state.now
        row.status = state.career.status
        row.level = state.career.level
        row.version = state.version
        row.updated_at = datetime.utcnow()

    gid = state.id
    if out.get("stock_prices"):
        db.execute(insert(m.StockPrice), [{"game_id": gid, **r} for r in _parse_ts(out["stock_prices"])])
    if out.get("transactions"):
        db.execute(insert(m.TransactionRow), [{"game_id": gid, **r} for r in _parse_ts(out["transactions"])])
    if out.get("events"):
        db.execute(insert(m.EventRow), [{"game_id": gid, **r} for r in _parse_ts(out["events"])])
    if out.get("news"):
        db.execute(insert(m.NewsRow), [{"game_id": gid, **r} for r in _parse_ts(out["news"])])
    if out.get("leave_records"):
        db.execute(insert(m.LeaveRecordRow), [{"game_id": gid, **r} for r in _parse_ts(out["leave_records"])])
    if out.get("game_days"):
        db.execute(insert(m.GameDayRow), [{"game_id": gid, **r} for r in out["game_days"]])
        econ = state.market.economy.model_dump()
        db.execute(insert(m.MarketStateRow), [{"game_id": gid, "date": r["date"], "regime": r["regime"],
                                               "economy": econ} for r in out["game_days"]])
    if out.get("telemetry"):
        db.execute(insert(m.TelemetryRow), [{
            "game_id": gid, "player_id": player_id, "t": datetime.fromisoformat(r["t"]), "trigger": r["trigger"],
            "day": r["day"], "portfolio_value": r["portfolio_value"], "drawdown": r["drawdown"],
            "risk_score": r["risk_score"], "market_regime": r["market_regime"], "payload": r,
        } for r in out["telemetry"]])
    _write_projections(db, state)
    db.commit()


def _write_projections(db: Session, state: GameState) -> None:
    gid = state.id
    p = state.portfolio
    prow = db.get(m.PortfolioRow, gid)
    vals = {"cash": p.cash, "nav": pe.nav(state), "realized_pnl": p.realized_pnl, "max_drawdown": p.max_drawdown,
            "updated_at": datetime.utcnow()}
    if prow is None:
        db.add(m.PortfolioRow(game_id=gid, **vals))
    else:
        for k, v in vals.items():
            setattr(prow, k, v)
    db.execute(delete(m.HoldingRow).where(m.HoldingRow.game_id == gid))
    if p.holdings:
        db.execute(insert(m.HoldingRow), [{"game_id": gid, "symbol": h.symbol, "qty": h.qty, "avg_cost": h.avg_cost}
                                          for h in p.holdings.values()])
    db.execute(delete(m.EmployeeRow).where(m.EmployeeRow.game_id == gid))
    db.execute(insert(m.EmployeeRow), [{
        "game_id": gid, "char_id": c.id, "name": c.name, "role": c.role, "skills": c.skills, "trust": c.trust,
        "loyalty": c.loyalty, "stress": c.stress, "performance": c.performance, "core": c.core,
    } for c in state.team.values()])
    db.execute(delete(m.CareerProgressRow).where(m.CareerProgressRow.game_id == gid))
    if state.career.history:
        db.execute(insert(m.CareerProgressRow), [{
            "game_id": gid, "quarter": h.quarter, "level": h.level, "title": h.title, "outcome": h.outcome,
            "return_pct": h.return_pct, "max_drawdown": h.max_drawdown, "date": h.date,
        } for h in state.career.history])


def load(db: Session, game_id: str) -> Optional[tuple[GameState, str]]:
    row = db.get(m.Game, game_id)
    if row is None:
        return None
    return GameState.model_validate(row.snapshot), row.player_id


def rollback_to(db: Session, state: GameState) -> None:
    """Discard history rows that lie in the future of `state` (used when loading a save)."""
    gid, now = state.id, state.now
    db.execute(delete(m.StockPrice).where(m.StockPrice.game_id == gid, m.StockPrice.t >= now))
    keep_tx = {t.id for t in state.transactions}
    rows = db.execute(select(m.TransactionRow.id, m.TransactionRow.tx_id).where(m.TransactionRow.game_id == gid)).all()
    stale = [r.id for r in rows if r.tx_id not in keep_tx]
    if stale:
        db.execute(delete(m.TransactionRow).where(m.TransactionRow.id.in_(stale)))
    for model, col, prefix in ((m.NewsRow, "news_id", "NEWS"), (m.EventRow, "event_id", "EVT")):
        limit = state.counters.get(prefix, 0)
        rows = db.execute(select(model.id, getattr(model, col)).where(model.game_id == gid)).all()
        stale = [r[0] for r in rows if int(r[1].split("-")[1]) > limit]
        if stale:
            db.execute(delete(model).where(model.id.in_(stale)))
    db.execute(delete(m.TelemetryRow).where(m.TelemetryRow.game_id == gid, m.TelemetryRow.t > now))
    db.execute(delete(m.GameDayRow).where(m.GameDayRow.game_id == gid, m.GameDayRow.date >= now.date().isoformat()))
    db.execute(delete(m.MarketStateRow).where(m.MarketStateRow.game_id == gid,
                                              m.MarketStateRow.date >= now.date().isoformat()))
    db.execute(delete(m.LeaveRecordRow).where(m.LeaveRecordRow.game_id == gid, m.LeaveRecordRow.end > now))


def candles(db: Session, game_id: str, symbol: str, limit: int = 2000) -> list[m.StockPrice]:
    q = (select(m.StockPrice).where(m.StockPrice.game_id == game_id, m.StockPrice.symbol == symbol)
         .order_by(m.StockPrice.t.desc()).limit(limit))
    return list(reversed(db.execute(q).scalars().all()))


def news(db: Session, game_id: str, limit: int, symbol: Optional[str] = None) -> list[m.NewsRow]:
    q = select(m.NewsRow).where(m.NewsRow.game_id == game_id)
    if symbol:
        q = q.where(m.NewsRow.symbols.contains(symbol))
    return db.execute(q.order_by(m.NewsRow.t.desc(), m.NewsRow.id.desc()).limit(limit)).scalars().all()
