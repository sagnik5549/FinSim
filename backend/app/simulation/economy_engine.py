"""
Economy engine — slow-moving macro state and scheduled data releases.

Macro variables drift daily. Scheduled releases (CPI, GDP, policy decisions) are
published in the calendar with a market consensus; the actual print depends on
the hidden economic state plus noise. The *surprise* is what moves markets.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np

from app.simulation.state import GameState, ScheduledEvent
from app.simulation.time_engine import is_business_day


def daily_step(state: GameState, rng: np.random.Generator) -> None:
    e = state.market.economy
    e.inflation = float(np.clip(e.inflation + rng.normal(0.004 * (e.oil - 80) / 10, 0.035), 2.0, 9.5))
    e.gdp_growth = float(np.clip(e.gdp_growth + rng.normal(-0.002 * (e.policy_rate - 6.5), 0.03), 2.0, 9.0))
    e.oil = float(np.clip(e.oil * np.exp(rng.normal(0, 0.012) + 0.25 * e.oil_shock * 0.01), 45, 140))
    # Shocks decay so their market influence fades over roughly two weeks
    e.rate_pressure *= 0.93
    e.oil_shock *= 0.90
    e.global_risk = float(np.clip(e.global_risk * 0.92 + rng.normal(0, 0.04), -1, 1))
    e.inr_shock *= 0.90


def _business_day_on_or_after(d: date) -> date:
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def _at(d: date, hour: int) -> datetime:
    return datetime.combine(d, datetime.min.time()).replace(hour=hour)


def schedule_quarter(state: GameState, rng: np.random.Generator, quarter_start: datetime) -> None:
    """Publish the quarter's calendar: earnings, data releases, policy meeting, CEO meetings."""
    q0 = quarter_start.date()
    e = state.market.economy
    econ_skill = state.team["economist"].skills.get("macro", 60) if "economist" in state.team else 60

    def desk_view(actual_guess: float, spread: float) -> float:
        # Our economist's forecast: noise shrinks with skill.
        return round(actual_guess + rng.normal(0, spread * (1.2 - econ_skill / 100)), 2)

    for offset in (11, 41, 71):
        d = _business_day_on_or_after(q0 + timedelta(days=offset + int(rng.integers(0, 3))))
        consensus = round(e.inflation + rng.normal(0, 0.15), 1)
        state.scheduled.append(ScheduledEvent(
            id=state.next_id("SCH"), time=_at(d, 11), kind="ECON_DATA", title="CPI inflation release",
            payload={"indicator": "CPI", "consensus": consensus, "desk_forecast": desk_view(e.inflation, 0.3)}))

    d = _business_day_on_or_after(q0 + timedelta(days=int(rng.integers(52, 58))))
    consensus = round(e.gdp_growth + rng.normal(0, 0.2), 1)
    state.scheduled.append(ScheduledEvent(
        id=state.next_id("SCH"), time=_at(d, 11), kind="ECON_DATA", title="GDP growth estimate",
        payload={"indicator": "GDP", "consensus": consensus, "desk_forecast": desk_view(e.gdp_growth, 0.35)}))

    d = _business_day_on_or_after(q0 + timedelta(days=int(rng.integers(33, 40))))
    state.scheduled.append(ScheduledEvent(
        id=state.next_id("SCH"), time=_at(d, 11), kind="POLICY", title="Central bank policy decision",
        payload={"consensus": "HOLD"}))

    # Company results season
    symbols = list(state.stocks)
    rng.shuffle(symbols)
    for i, sym in enumerate(symbols):
        day_off = 16 + int(i * 55 / len(symbols)) + int(rng.integers(0, 4))
        d = _business_day_on_or_after(q0 + timedelta(days=day_off))
        hour = int(rng.choice([10, 13, 16]))
        state.scheduled.append(ScheduledEvent(
            id=state.next_id("SCH"), time=_at(d, hour), kind="EARNINGS", symbol=sym,
            title=f"{state.stocks[sym].name} quarterly results"))

    for day_off, topic in ((29, "MONTH1"), (59, "MONTH2"), (84, "FINAL")):
        d = _business_day_on_or_after(q0 + timedelta(days=day_off))
        state.scheduled.append(ScheduledEvent(
            id=state.next_id("SCH"), time=_at(d, 15), kind="CEO_MEETING", title="CEO portfolio check-in",
            payload={"topic": topic}))

    state.scheduled.sort(key=lambda s: s.time)


def release_cpi(state: GameState, rng: np.random.Generator, consensus: float) -> tuple[float, float]:
    e = state.market.economy
    actual = round(e.inflation + rng.normal(0, 0.18), 1)
    surprise = actual - consensus
    e.rate_pressure = float(np.clip(e.rate_pressure + surprise * 0.9, -1, 1))
    return actual, surprise


def release_gdp(state: GameState, rng: np.random.Generator, consensus: float) -> tuple[float, float]:
    e = state.market.economy
    actual = round(e.gdp_growth + rng.normal(0, 0.25), 1)
    surprise = actual - consensus
    e.global_risk = float(np.clip(e.global_risk + surprise * 0.15, -1, 1))
    return actual, surprise


def policy_decision(state: GameState, rng: np.random.Generator) -> str:
    e = state.market.economy
    score = (e.inflation - 5.0) * 0.8 + e.rate_pressure * 1.2 - (6.5 - e.gdp_growth) * 0.4 + rng.normal(0, 0.6)
    if score > 1.0:
        e.policy_rate = round(e.policy_rate + 0.25, 2)
        e.rate_pressure = float(np.clip(e.rate_pressure + 0.6, -1, 1))
        return "HIKE"
    if score < -1.0:
        e.policy_rate = round(e.policy_rate - 0.25, 2)
        e.rate_pressure = float(np.clip(e.rate_pressure - 0.6, -1, 1))
        return "CUT"
    e.rate_pressure *= 0.6
    return "HOLD"
