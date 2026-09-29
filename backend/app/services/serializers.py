"""
State -> API DTOs. Hidden simulation variables (market regime, fair values,
earnings quality, informed sellers, hidden/chain events, behaviour profile)
are never serialised.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import Any

from app.simulation import career_engine as ce
from app.simulation import portfolio_engine as pe
from app.simulation import risk_engine as re_
from app.simulation.constants import CAREER_LEVELS, CRORE, FIRM_NAME, SECTORS
from app.simulation.state import GameState, StockState
from app.simulation.time_engine import clock_view


def sentiment_label(v: float) -> str:
    return "BULLISH" if v > 0.25 else "POSITIVE" if v > 0.08 else "BEARISH" if v < -0.25 else "NEGATIVE" if v < -0.08 else "NEUTRAL"


def stock_risk(s: StockState) -> float:
    """0-100 risk rating shown in the screener (volatility, beta, leverage)."""
    return round(min(100.0, s.realized_vol / 0.035 * 45 + (s.beta - 0.5) * 25 + s.debt * 25), 1)


def stock_row(state: GameState, s: StockState) -> dict[str, Any]:
    return {
        "symbol": s.symbol, "name": s.name, "sector": s.sector, "price": s.price, "prev_close": s.prev_close,
        "change": s.price - s.prev_close, "change_pct": s.price / s.prev_close - 1 if s.prev_close else 0.0,
        "week_change_pct": s.price / s.week_ago_price - 1 if s.week_ago_price else 0.0,
        "day_high": round(s.day_high, 2), "day_low": round(s.day_low, 2), "open": s.day_open,
        "volume": int(s.volume_today), "prev_volume": int(s.prev_volume), "volatility": round(s.realized_vol, 4), "beta": round(s.beta, 2),
        "momentum": round(s.momentum * 100, 3), "pe": round(s.price / s.eps, 1) if s.eps > 0 else None,
        "valuation": round(s.valuation, 3), "sentiment": round(s.sentiment, 3),
        "sentiment_label": sentiment_label(s.sentiment), "risk": stock_risk(s),
        "market_cap_cr": round(s.price * s.shares_cr * 1e7 / CRORE, 0), "spark": s.spark,
        "held": s.symbol in state.portfolio.holdings,
    }


def fundamentals(s: StockState) -> dict[str, Any]:
    return {"growth": s.growth, "profitability": s.profitability, "debt": s.debt, "valuation": s.valuation,
            "pe": round(s.price / s.eps, 1) if s.eps > 0 else None, "eps": round(s.eps, 2), "beta": s.beta,
            "base_volatility": s.volatility, "event_sensitivity": s.event_sensitivity, "about": s.about,
            "market_cap_cr": round(s.price * s.shares_cr * 1e7 / CRORE, 0),
            "institutional_flow": "BUYING" if s.institutional_pressure > 0.15 else
            "SELLING" if s.institutional_pressure < -0.15 else "NEUTRAL"}


def holdings(state: GameState) -> list[dict[str, Any]]:
    total = pe.nav(state)
    out = []
    for h in state.portfolio.holdings.values():
        s = state.stocks[h.symbol]
        value = h.qty * s.price
        out.append({
            "symbol": h.symbol, "name": s.name, "sector": s.sector, "qty": h.qty, "avg_cost": round(h.avg_cost, 2),
            "price": s.price, "value": value, "weight": value / total if total else 0.0,
            "pnl": value - h.qty * h.avg_cost, "pnl_pct": s.price / h.avg_cost - 1 if h.avg_cost else 0.0,
            "day_change_pct": s.price / s.prev_close - 1 if s.prev_close else 0.0,
            "day_pnl": h.qty * (s.price - s.prev_close), "opened_at": h.opened_at.isoformat(),
        })
    out.sort(key=lambda x: -x["value"])
    return out


def portfolio_summary(state: GameState) -> dict[str, Any]:
    p = state.portfolio
    total = pe.nav(state)
    return {
        "starting_capital": p.quarter_start_value, "cash": p.cash, "invested": pe.invested_value(state),
        "value": total, "pnl": total - p.quarter_start_value, "return_pct": total / p.quarter_start_value - 1,
        "day_pnl": total - p.day_start_value, "day_pnl_pct": total / p.day_start_value - 1 if p.day_start_value else 0,
        "realized_pnl": p.realized_pnl, "unrealized_pnl": pe.unrealized_pnl(state), "fees_paid": p.fees_paid,
        "max_drawdown": p.max_drawdown, "drawdown": pe.current_drawdown(state), "peak_value": p.peak_value,
        "target_value": state.career.target_value, "target_progress": ce.target_progress(state),
        "volatility": pe.portfolio_volatility(state), "beta": pe.portfolio_beta(state),
    }


def risk_summary(state: GameState) -> dict[str, Any]:
    r = re_.assess(state)
    d = asdict(r)
    d["warnings"] = [w.model_dump(mode="json") for w in state.risk_warnings[-15:]]
    d["exceptions"] = [e.model_dump(mode="json") for e in state.risk_exceptions if e.until > state.now]
    d["sector_weights"] = {sec: r.sector_weights.get(sec, 0.0) for sec in SECTORS}
    return d


def clock(state: GameState) -> dict[str, Any]:
    cv = asdict(clock_view(state))
    cv["iso"] = state.now.isoformat()
    cv["label"] = state.now.strftime("%a %d %b %Y").upper()
    cv["time"] = state.now.strftime("%H:%M")
    return cv


def career(state: GameState) -> dict[str, Any]:
    c = state.career
    lo, hi = ce.xp_bounds(c.level)
    lvl = CAREER_LEVELS[c.level]
    return {
        "firm": FIRM_NAME, "level": c.level, "title": c.title, "xp": c.xp, "xp_level_start": lo, "xp_next": hi,
        "reputation": round(c.reputation, 1), "status": c.status, "warning_level": c.warning_level,
        "risk_profile": c.risk_profile, "quarter_index": c.quarter_index,
        "quarter_start": c.quarter_start.isoformat(), "quarter_end": c.quarter_end.isoformat(),
        "target_value": c.target_value, "target_return": c.target_return, "max_drawdown_limit": c.max_drawdown_limit,
        "risk_violations": c.risk_violations, "ignored_violations": c.ignored_violations,
        "exceptions_granted": c.exceptions_granted, "compliance_strikes": c.compliance_strikes,
        "time_progress": ce.time_progress(state), "unlocks": lvl["unlocks"],
        "next_title": CAREER_LEVELS[c.level + 1]["title"] if c.level + 1 in CAREER_LEVELS else None,
        "delegate": lvl["delegate"],
    }


def team(state: GameState) -> list[dict[str, Any]]:
    return [c.model_dump() for c in state.team.values()]


def calendar(state: GameState, limit: int = 20) -> list[dict[str, Any]]:
    horizon = state.now + timedelta(days=21)
    out = []
    for x in state.scheduled:
        if x.public and not x.processed and x.time >= state.now and x.time <= horizon:
            d = {"id": x.id, "time": x.time.isoformat(), "kind": x.kind, "title": x.title, "symbol": x.symbol}
            if x.kind == "ECON_DATA":
                d["consensus"] = x.payload.get("consensus")
                d["desk_forecast"] = x.payload.get("desk_forecast")
            out.append(d)
            if len(out) >= limit:
                break
    return out


def opportunity(state: GameState, o) -> dict[str, Any]:
    s = state.stocks[o.symbol]
    return {"id": o.id, "kind": o.kind, "symbol": o.symbol, "name": s.name, "qty": o.qty, "price": o.price,
            "market_price": s.price, "discount": o.discount, "effective_discount": 1 - o.price / s.price,
            "value": o.qty * o.price, "created": o.created.isoformat(), "expires_at": o.expires_at.isoformat(),
            "status": o.status, "seller": o.seller,
            "minutes_left": max(0, int((o.expires_at - state.now).total_seconds() // 60))}


def full_state(state: GameState, include_paths: bool = True) -> dict[str, Any]:
    s = state
    return {
        "game_id": s.id, "seed": s.seed, "version": s.version,
        "clock": clock(s),
        "career": career(s),
        "portfolio": portfolio_summary(s),
        "holdings": holdings(s),
        "indices": [{"key": i.key, "name": i.name, "kind": i.kind, "value": i.value, "prev_close": i.prev_close,
                     "change_pct": i.value / i.prev_close - 1 if i.prev_close else 0.0, "spark": i.spark}
                    for i in s.indices.values()],
        "stocks": [stock_row(s, st) for st in s.stocks.values()],
        "news": [n.model_dump(mode="json") for n in reversed(s.news[-40:])],
        "messages": [m.model_dump(mode="json") for m in reversed(s.messages[-30:])],
        "notifications": [n.model_dump(mode="json") for n in reversed(s.notifications[-30:])],
        "popups": [p.model_dump(mode="json") for p in s.popups],
        "opportunities": [opportunity(s, o) for o in reversed(s.opportunities[-8:])],
        "risk": risk_summary(s),
        "calendar": calendar(s),
        "leave": {"allowance": s.leave.allowance, "used": s.leave.used, "remaining": s.leave.allowance - s.leave.used,
                  "is_on_leave": s.leave.is_on_leave, "year": s.leave.year,
                  "records": [r.model_dump(mode="json") for r in s.leave.records[-10:]]},
        "nav_series": [{"t": p.t.isoformat(), "nav": p.nav, "bench": p.bench} for p in s.portfolio.hourly_nav[-400:]],
        "team": [{"id": c.id, "name": c.name, "role": c.role, "avatar": c.avatar, "trust": round(c.trust),
                  "stress": round(c.stress)} for c in s.team.values()],
        "research": [r.model_dump(mode="json") for r in reversed(s.research[-12:])],
        "theses": [t.model_dump(mode="json") for t in reversed(s.theses[-12:])],
        "transactions": [t.model_dump(mode="json") for t in reversed(s.transactions[-25:])],
        "stats": {"hours_worked": s.stats.hours_worked, "hours_skipped": s.stats.hours_skipped,
                  "trades": s.stats.trades, "research_count": s.stats.research_count},
        "last_tick": ({"t": s.last_tick.t.isoformat() if s.last_tick.t else None, "paths": s.last_tick.paths}
                      if include_paths else None),
    }
