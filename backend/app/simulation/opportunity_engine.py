"""
Time-limited opportunities (block deals).

A seller offers a block of shares at a discount that expires at a fixed game
time. Some sellers are informed: a negative company event is already scheduled
(hidden). A deep-dive research call before the deadline can expose them — but
it costs three of the few hours you have.
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np

from app.simulation.constants import CRORE, MARKET_CLOSE_HOUR
from app.simulation.event_engine import EventEngine
from app.simulation.state import GameState, Opportunity

SELLERS = ["a promoter group entity", "an exiting private-equity fund", "a foreign portfolio investor",
           "a family office", "an insurance company rebalancing its book"]


def maybe_create(state: GameState, rng: np.random.Generator, events: EventEngine, rate_mult: float = 1.0) -> Opportunity | None:
    if state.now.hour >= MARKET_CLOSE_HOUR - 2:
        return None
    if sum(1 for o in state.opportunities if o.status == "OPEN") >= 2:
        return None
    if rng.random() > 0.045 * rate_mult:
        return None
    sym = str(rng.choice(list(state.stocks)))
    s = state.stocks[sym]
    informed = bool(rng.random() < 0.3)
    discount = float(rng.uniform(0.025, 0.05)) if not informed else float(rng.uniform(0.035, 0.06))
    size = float(rng.uniform(3, 9)) * CRORE
    qty = int(size / s.price)
    hours = int(rng.integers(2, 4))
    expires = min(state.now + timedelta(hours=hours), state.now.replace(hour=MARKET_CLOSE_HOUR - 1))
    if expires <= state.now:
        return None
    opp = Opportunity(
        id=state.next_id("OPP"), kind="BLOCK_DEAL", symbol=sym, qty=qty, price=round(s.price * (1 - discount), 2),
        discount=round(discount, 4), created=state.now, expires_at=expires, seller=str(rng.choice(SELLERS)),
        informed_seller=informed,
    )
    if informed:
        etype = str(rng.choice(["EARNINGS_WARNING", "REGULATORY_INVESTIGATION", "PRODUCT_FAILURE"]))
        events.schedule_hidden(etype, sym, days=int(rng.integers(2, 7)))
    state.opportunities.append(opp)
    state.opportunities = state.opportunities[-40:]
    return opp


def expire(state: GameState) -> list[Opportunity]:
    out = []
    for o in state.opportunities:
        if o.status == "OPEN" and state.now >= o.expires_at:
            o.status = "EXPIRED"
            out.append(o)
    return out
