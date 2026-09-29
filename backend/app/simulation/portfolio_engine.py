"""
Portfolio engine — valuation, order quoting/execution, P&L and drawdown.

All validation happens here: the frontend only ever sends (symbol, quantity).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Optional

from app.simulation.constants import FEE_RATE, IMPACT_COEFF, MAX_IMPACT, MIN_FEE, STT_RATE
from app.simulation.state import GameState, Holding, NavPoint, Transaction


class TradeError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Quote:
    side: str
    symbol: str
    name: str
    qty: int
    market_price: float
    exec_price: float
    impact_pct: float
    value: float
    fee: float
    total: float  # cash out (buy) or cash in (sell)
    cash_before: float
    cash_after: float
    position_after: int
    weight_after: float
    realized_pnl: float
    warnings: list[str]

    def dict(self):
        return asdict(self)


def nav(state: GameState) -> float:
    p = state.portfolio
    return p.cash + sum(h.qty * state.stocks[h.symbol].price for h in p.holdings.values())


def invested_value(state: GameState) -> float:
    return sum(h.qty * state.stocks[h.symbol].price for h in state.portfolio.holdings.values())


def unrealized_pnl(state: GameState) -> float:
    return sum(h.qty * (state.stocks[h.symbol].price - h.avg_cost) for h in state.portfolio.holdings.values())


def trader_skill(state: GameState) -> float:
    t = state.team.get("trader")
    return (t.skills.get("execution", 50) / 100) if t else 0.5


def _impact(state: GameState, symbol: str, qty: int) -> float:
    s = state.stocks[symbol]
    participation = qty / max(s.avg_hourly_volume, 1.0)
    return min(MAX_IMPACT, IMPACT_COEFF * participation * (1 - 0.4 * trader_skill(state)))


def _validate(state: GameState, symbol: str, qty) -> None:
    if symbol not in state.stocks:
        raise TradeError("INVALID_SYMBOL", f"Unknown symbol '{symbol}'.")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        raise TradeError("INVALID_QUANTITY", "Quantity must be a positive whole number.")
    if qty > 50_000_000:
        raise TradeError("INVALID_QUANTITY", "Quantity exceeds the exchange's maximum order size.")


def quote(state: GameState, side: str, symbol: str, qty: int, price_override: Optional[float] = None) -> Quote:
    _validate(state, symbol, qty)
    s = state.stocks[symbol]
    p = state.portfolio
    total_nav = nav(state)
    held = p.holdings.get(symbol)
    warnings: list[str] = []
    if side == "BUY":
        impact = 0.0 if price_override else _impact(state, symbol, qty)
        px = price_override or s.price * (1 + impact)
        value = px * qty
        fee = max(MIN_FEE, value * FEE_RATE)
        total = value + fee
        cash_after = p.cash - total
        pos_after = (held.qty if held else 0) + qty
        weight_after = pos_after * s.price / total_nav if total_nav else 0
        realized = 0.0
        if impact > 0.004:
            warnings.append(f"Large order: estimated market impact {impact * 100:.2f}% of price.")
    else:
        impact = _impact(state, symbol, qty)
        px = s.price * (1 - impact)
        value = px * qty
        fee = max(MIN_FEE, value * (FEE_RATE + STT_RATE))
        total = value - fee
        cash_after = p.cash + total
        pos_after = (held.qty if held else 0) - qty
        weight_after = max(pos_after, 0) * s.price / total_nav if total_nav else 0
        realized = (px - held.avg_cost) * qty - fee if held else 0.0
    return Quote(side=side, symbol=symbol, name=s.name, qty=qty, market_price=s.price, exec_price=round(px, 2),
                 impact_pct=round(impact * 100, 3), value=round(value, 2), fee=round(fee, 2), total=round(total, 2),
                 cash_before=round(p.cash, 2), cash_after=round(cash_after, 2), position_after=pos_after,
                 weight_after=round(weight_after, 4), realized_pnl=round(realized, 2), warnings=warnings)


def execute_buy(state: GameState, symbol: str, qty: int, source: str = "PLAYER",
                price_override: Optional[float] = None) -> Transaction:
    q = quote(state, "BUY", symbol, qty, price_override)
    p = state.portfolio
    if q.total > p.cash + 1e-6:
        raise TradeError("INSUFFICIENT_CASH",
                         f"Insufficient cash: order needs ₹{q.total:,.0f} but only ₹{p.cash:,.0f} is available.")
    p.cash -= q.total
    p.fees_paid += q.fee
    h = p.holdings.get(symbol)
    if h:
        cost = h.avg_cost * h.qty + q.exec_price * qty + q.fee
        h.qty += qty
        h.avg_cost = cost / h.qty
    else:
        p.holdings[symbol] = Holding(symbol=symbol, qty=qty, avg_cost=(q.exec_price * qty + q.fee) / qty,
                                     opened_at=state.now)
    tx = Transaction(id=state.next_id("TX"), time=state.now, side="BUY", symbol=symbol, qty=qty,
                     price=q.exec_price, fee=q.fee, value=q.value, source=source)
    _record(state, tx)
    return tx


def execute_sell(state: GameState, symbol: str, qty: int, source: str = "PLAYER") -> Transaction:
    _validate(state, symbol, qty)
    p = state.portfolio
    h = p.holdings.get(symbol)
    if not h or h.qty <= 0:
        raise TradeError("NO_POSITION", f"You do not hold any {symbol}.")
    if qty > h.qty:
        raise TradeError("INSUFFICIENT_SHARES", f"Cannot sell {qty:,} shares; you only hold {h.qty:,}.")
    q = quote(state, "SELL", symbol, qty)
    p.cash += q.total
    p.fees_paid += q.fee
    realized = (q.exec_price - h.avg_cost) * qty - q.fee
    p.realized_pnl += realized
    h.realized_pnl += realized
    h.qty -= qty
    pct = (q.exec_price / h.avg_cost - 1) if h.avg_cost else 0.0
    state.stats.closed_trades.append({"symbol": symbol, "pnl": round(realized, 2), "pct": round(pct, 4),
                                      "t": state.now.isoformat(), "qty": qty})
    state.stats.closed_trades = state.stats.closed_trades[-300:]
    if realized >= 0:
        state.stats.wins += 1
    else:
        state.stats.losses += 1
    if h.qty == 0:
        del p.holdings[symbol]
    tx = Transaction(id=state.next_id("TX"), time=state.now, side="SELL", symbol=symbol, qty=qty,
                     price=q.exec_price, fee=q.fee, value=q.value, realized_pnl=round(realized, 2), source=source)
    _record(state, tx)
    return tx


def _record(state: GameState, tx: Transaction) -> None:
    state.transactions.append(tx)
    state.outbox("transactions").append({
        "tx_id": tx.id, "t": tx.time.isoformat(), "side": tx.side, "symbol": tx.symbol, "qty": tx.qty,
        "price": tx.price, "fee": tx.fee, "value": tx.value, "realized_pnl": tx.realized_pnl, "source": tx.source,
    })
    update_marks(state)


def update_marks(state: GameState) -> None:
    """Refresh peak/drawdown after any price or position change."""
    p = state.portfolio
    v = nav(state)
    if v > p.peak_value:
        p.peak_value = v
    dd = 1 - v / p.peak_value if p.peak_value else 0.0
    p.max_drawdown = max(p.max_drawdown, dd)


def current_drawdown(state: GameState) -> float:
    p = state.portfolio
    return max(0.0, 1 - nav(state) / p.peak_value) if p.peak_value else 0.0


def record_hour(state: GameState) -> None:
    update_marks(state)
    bench = state.indices["BH50"].value
    state.portfolio.hourly_nav.append(NavPoint(t=state.now, nav=round(nav(state), 2), bench=bench))
    state.portfolio.hourly_nav = state.portfolio.hourly_nav[-900:]


def daily_returns(state: GameState) -> list[float]:
    d = state.portfolio.daily
    return [r.close_nav / r.open_nav - 1 for r in d if r.open_nav]


def portfolio_volatility(state: GameState) -> float:
    """Annualised volatility estimate from holdings (forward-looking) blended with realised."""
    total = nav(state)
    if total <= 0:
        return 0.0
    var_mkt, idio = 0.0, 0.0
    beta_sum = 0.0
    sector_w: dict[str, float] = {}
    for h in state.portfolio.holdings.values():
        s = state.stocks[h.symbol]
        w = h.qty * s.price / total
        beta_sum += w * s.beta
        idio += (w * s.volatility * 0.85) ** 2
        sector_w[s.sector] = sector_w.get(s.sector, 0.0) + w
    var_mkt = (beta_sum * 0.009) ** 2
    var_sec = sum((w * 0.005) ** 2 for w in sector_w.values())
    daily = math.sqrt(var_mkt + var_sec + idio)
    return daily * math.sqrt(252)


def portfolio_beta(state: GameState) -> float:
    total = nav(state)
    if total <= 0:
        return 0.0
    return sum(h.qty * state.stocks[h.symbol].price / total * state.stocks[h.symbol].beta
               for h in state.portfolio.holdings.values())
