"""
Risk engine — exposure measurement, firm-policy limits and violations.

Risk is a gameplay mechanic, not decoration:
  * breaching a limit raises a blocking RISK WARNING the player must answer
    (REDUCE EXPOSURE / REQUEST EXCEPTION / IGNORE)
  * ignored breaches cost reputation daily, erode the Risk Manager's trust and
    count against the quarterly review
  * drawdown beyond the mandate triggers a formal CEO warning; beyond the
    termination threshold the board ends the career.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from app.simulation import portfolio_engine as pe
from app.simulation.constants import RISK_POLICY
from app.simulation.state import GameState, RiskException, RiskWarning


@dataclass
class RiskReport:
    score: float
    level: str
    nav: float
    cash_ratio: float
    invested_ratio: float
    drawdown: float
    max_drawdown: float
    volatility: float
    beta: float
    var_95: float  # 1-day 95% value-at-risk in rupees
    largest_position: dict
    stock_weights: dict[str, float]
    sector_weights: dict[str, float]
    limits: dict[str, float]
    breaches: list[dict] = field(default_factory=list)
    near_limits: list[dict] = field(default_factory=list)


def policy(state: GameState) -> dict[str, float]:
    base = dict(RISK_POLICY[state.career.risk_profile])
    base["max_drawdown"] = state.career.max_drawdown_limit
    return base


def exposures(state: GameState) -> tuple[dict[str, float], dict[str, float]]:
    total = pe.nav(state)
    stock_w: dict[str, float] = {}
    sector_w: dict[str, float] = {}
    for h in state.portfolio.holdings.values():
        s = state.stocks[h.symbol]
        w = h.qty * s.price / total if total else 0.0
        stock_w[h.symbol] = w
        sector_w[s.sector] = sector_w.get(s.sector, 0.0) + w
    return stock_w, sector_w


def _excepted(state: GameState, rule: str, subject: str) -> bool:
    return any(e.rule == rule and e.subject == subject and e.until > state.now for e in state.risk_exceptions)


def assess(state: GameState) -> RiskReport:
    lim = policy(state)
    total = pe.nav(state)
    stock_w, sector_w = exposures(state)
    cash_ratio = state.portfolio.cash / total if total else 1.0
    dd = pe.current_drawdown(state)
    vol = pe.portfolio_volatility(state)
    beta = pe.portfolio_beta(state)
    var95 = 1.65 * vol / math.sqrt(252) * total
    largest = max(stock_w.items(), key=lambda kv: kv[1], default=(None, 0.0))

    breaches, near = [], []
    for sym, w in stock_w.items():
        item = {"rule": "SINGLE_STOCK", "subject": sym, "value": w, "limit": lim["max_single_stock"],
                "excepted": _excepted(state, "SINGLE_STOCK", sym)}
        if w > lim["max_single_stock"] + 1e-9:
            breaches.append(item)
        elif w > lim["max_single_stock"] * 0.85:
            near.append(item)
    for sec, w in sector_w.items():
        item = {"rule": "SECTOR", "subject": sec, "value": w, "limit": lim["max_sector"],
                "excepted": _excepted(state, "SECTOR", sec)}
        if w > lim["max_sector"] + 1e-9:
            breaches.append(item)
        elif w > lim["max_sector"] * 0.85:
            near.append(item)
    if dd > lim["max_drawdown"]:
        breaches.append({"rule": "DRAWDOWN", "subject": "PORTFOLIO", "value": dd, "limit": lim["max_drawdown"],
                         "excepted": False})
    elif dd > lim["max_drawdown"] * 0.7:
        near.append({"rule": "DRAWDOWN", "subject": "PORTFOLIO", "value": dd, "limit": lim["max_drawdown"],
                     "excepted": False})

    # Composite 0-100 risk score
    conc = min(1.0, largest[1] / lim["max_single_stock"]) if largest[0] else 0.0
    sec_conc = min(1.0, max(sector_w.values(), default=0.0) / lim["max_sector"])
    dd_part = min(1.0, dd / lim["max_drawdown"])
    vol_part = min(1.0, vol / 0.35)
    score = 100 * (0.25 * conc + 0.25 * sec_conc + 0.30 * dd_part + 0.20 * vol_part)
    score += 10 * sum(1 for b in breaches if not b["excepted"])
    score = float(np.clip(score, 0, 100))
    level = "LOW" if score < 30 else "MEDIUM" if score < 55 else "HIGH" if score < 75 else "CRITICAL"
    return RiskReport(
        score=round(score, 1), level=level, nav=total, cash_ratio=cash_ratio, invested_ratio=1 - cash_ratio,
        drawdown=dd, max_drawdown=state.portfolio.max_drawdown, volatility=vol, beta=beta, var_95=var95,
        largest_position={"symbol": largest[0], "weight": largest[1]},
        stock_weights=stock_w, sector_weights=sector_w, limits=lim, breaches=breaches, near_limits=near,
    )


def open_warnings(state: GameState) -> list[RiskWarning]:
    return [w for w in state.risk_warnings if w.status == "OPEN"]


def detect_new_breaches(state: GameState, report: RiskReport) -> list[RiskWarning]:
    """Create warnings for new, non-excepted breaches; clear warnings that are no longer breached."""
    active_keys = {(b["rule"], b["subject"]) for b in report.breaches}

    def live(w: RiskWarning) -> bool:
        # A reduced drawdown warning stays live: selling can't undo losses already taken.
        return w.status in ("OPEN", "IGNORED", "EXCEPTION_GRANTED") or (w.status == "REDUCED" and w.rule == "DRAWDOWN")

    for w in state.risk_warnings:
        if live(w) and (w.rule, w.subject) not in active_keys:
            w.status = "CLEARED"
            w.resolved_at = w.resolved_at or state.now
        elif w.status == "EXCEPTION_GRANTED" and not _excepted(state, w.rule, w.subject):
            w.status = "EXPIRED"
    tracked = {(w.rule, w.subject) for w in state.risk_warnings if live(w)}
    new = []
    for b in report.breaches:
        key = (b["rule"], b["subject"])
        if key in tracked or b["excepted"]:
            continue
        w = RiskWarning(id=state.next_id("RSK"), rule=b["rule"], subject=b["subject"], value=round(b["value"], 4),
                        limit=b["limit"], created=state.now, during_leave=state.leave.is_on_leave)
        state.risk_warnings.append(w)
        state.career.risk_violations += 1
        new.append(w)
    state.risk_warnings = state.risk_warnings[-100:]
    return new


def reduction_orders(state: GameState, w: RiskWarning) -> list[tuple[str, int]]:
    """Sell orders that bring the exposure back inside policy (with a small buffer)."""
    total = pe.nav(state)
    lim = policy(state)
    orders: list[tuple[str, int]] = []
    if w.rule == "SINGLE_STOCK":
        h = state.portfolio.holdings.get(w.subject)
        if h:
            target_val = total * lim["max_single_stock"] * 0.95
            excess = h.qty * state.stocks[w.subject].price - target_val
            qty = min(h.qty, math.ceil(excess / state.stocks[w.subject].price))
            if qty > 0:
                orders.append((w.subject, qty))
    elif w.rule == "SECTOR":
        members = [h for h in state.portfolio.holdings.values() if state.stocks[h.symbol].sector == w.subject]
        sec_val = sum(h.qty * state.stocks[h.symbol].price for h in members)
        target = total * lim["max_sector"] * 0.95
        frac = max(0.0, (sec_val - target) / sec_val) if sec_val else 0.0
        for h in members:
            qty = min(h.qty, math.ceil(h.qty * frac))
            if qty > 0:
                orders.append((h.symbol, qty))
    elif w.rule == "DRAWDOWN":
        # De-risk: cut every position by a quarter
        for h in state.portfolio.holdings.values():
            qty = math.ceil(h.qty * 0.25)
            if qty > 0:
                orders.append((h.symbol, min(qty, h.qty)))
    return orders


def exception_probability(state: GameState, w: RiskWarning) -> float:
    if w.rule == "DRAWDOWN":
        return 0.0
    rm = state.team.get("risk_manager")
    trust = rm.trust if rm else 50.0
    excess = w.value / w.limit - 1
    p = 0.25 + 0.5 * (state.career.reputation / 100) + 0.25 * (trust / 100) - 1.2 * excess
    p -= 0.12 * state.career.exceptions_granted
    return float(np.clip(p, 0.05, 0.9))


def grant_exception(state: GameState, w: RiskWarning, days: int = 7) -> None:
    state.risk_exceptions.append(RiskException(rule=w.rule, subject=w.subject, until=state.now + timedelta(days=days)))
    state.risk_exceptions = [e for e in state.risk_exceptions if e.until > state.now]
