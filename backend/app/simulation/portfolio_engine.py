"""
PortfolioEngine — computes portfolio metrics from holdings and current prices.
All values in INR (Rupees).
"""
from dataclasses import dataclass, field
from typing import Optional

from app.simulation.constants import CRORE, LAKH


@dataclass
class PortfolioMetrics:
    # Core balances
    cash: float
    invested_value: float           # current market value of all holdings
    total_value: float              # cash + invested_value
    starting_capital: float
    quarterly_target: float

    # P&L
    total_pnl: float                # total_value - starting_capital
    total_return_pct: float         # (total_value / starting_capital - 1) * 100
    realized_pnl: float
    unrealized_pnl: float
    daily_pnl: float

    # Risk metrics
    max_drawdown: float             # fraction (e.g. 0.05 = 5%)
    portfolio_volatility: float     # annualized estimated vol

    # Target tracking
    target_progress: float          # 0–1 (how close to target)
    to_target: float                # INR needed to reach target
    target_met: bool

    # Sector exposure
    sector_exposure: dict[str, float]   # sector → % of portfolio
    largest_position: Optional[str]
    largest_position_pct: float

    # Holdings detail
    holdings: list[dict]            # symbol, qty, avg_price, current_price, value, pnl, pnl_pct


class PortfolioEngine:

    @staticmethod
    def compute(
        cash: float,
        holdings_db: list,          # list of Holding ORM objects
        stocks_map: dict[str, dict], # symbol → stock snapshot dict
        starting_capital: float,
        quarterly_target: float,
        peak_portfolio_value: float,
        daily_open_portfolio: Optional[float],
        realized_pnl: float = 0.0,
    ) -> PortfolioMetrics:
        """
        Compute all portfolio metrics from current holdings and prices.
        """
        holdings_detail = []
        invested_value = 0.0
        unrealized_pnl = 0.0
        sector_values: dict[str, float] = {}

        for h in holdings_db:
            sym = h.symbol if hasattr(h, "symbol") else h["symbol"]
            qty = int(h.quantity if hasattr(h, "quantity") else h["quantity"])
            avg_price = float(h.avg_buy_price if hasattr(h, "avg_buy_price") else h["avg_buy_price"])

            if qty <= 0:
                continue

            stock = stocks_map.get(sym)
            if not stock:
                continue

            cur_price = stock["current_price"] if isinstance(stock, dict) else stock.current_price
            sector = stock["sector"] if isinstance(stock, dict) else stock.sector
            name = stock["name"] if isinstance(stock, dict) else stock.name

            cur_value = qty * cur_price
            cost_basis = qty * avg_price
            unrealized = cur_value - cost_basis
            unrealized_pct = (cur_value / cost_basis - 1) * 100 if cost_basis > 0 else 0.0

            holdings_detail.append({
                "symbol": sym,
                "name": name,
                "sector": sector,
                "quantity": qty,
                "avg_buy_price": avg_price,
                "current_price": cur_price,
                "current_value": cur_value,
                "cost_basis": cost_basis,
                "unrealized_pnl": unrealized,
                "unrealized_pnl_pct": unrealized_pct,
                "daily_return": stock.get("daily_return", 0.0) if isinstance(stock, dict) else getattr(stock, "daily_return", 0.0),
            })

            invested_value += cur_value
            unrealized_pnl += unrealized
            sector_values[sector] = sector_values.get(sector, 0.0) + cur_value

        total_value = cash + invested_value
        total_pnl = total_value - starting_capital
        total_return_pct = (total_value / starting_capital - 1) * 100

        # Drawdown
        current_peak = max(peak_portfolio_value, total_value)
        max_drawdown = (current_peak - total_value) / current_peak if current_peak > 0 else 0.0

        # Target progress
        target_gap = quarterly_target - starting_capital
        current_gain = total_value - starting_capital
        target_progress = min(1.0, max(0.0, current_gain / target_gap)) if target_gap > 0 else 1.0

        # Sector exposure (% of total portfolio)
        sector_exposure = {}
        if total_value > 0:
            for sec, val in sector_values.items():
                sector_exposure[sec] = (val / total_value) * 100

        # Largest position
        largest_sym = None
        largest_pct = 0.0
        if holdings_detail and total_value > 0:
            largest = max(holdings_detail, key=lambda h: h["current_value"])
            largest_sym = largest["symbol"]
            largest_pct = (largest["current_value"] / total_value) * 100

        # Daily P&L
        daily_pnl = 0.0
        if daily_open_portfolio is not None:
            daily_pnl = total_value - daily_open_portfolio

        # Portfolio volatility (rough estimate from position-weighted vols)
        portfolio_vol = 0.0
        if total_value > 0 and holdings_detail:
            weighted_vols = []
            stocks_list = [stocks_map.get(h["symbol"]) for h in holdings_detail]
            for h, s in zip(holdings_detail, stocks_list):
                if s:
                    w = h["current_value"] / total_value
                    v = s.get("volatility", 0.02) if isinstance(s, dict) else getattr(s, "volatility", 0.02)
                    weighted_vols.append(w * v)
            portfolio_vol = sum(weighted_vols) * (252 ** 0.5)  # annualized

        return PortfolioMetrics(
            cash=cash,
            invested_value=invested_value,
            total_value=total_value,
            starting_capital=starting_capital,
            quarterly_target=quarterly_target,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            daily_pnl=daily_pnl,
            max_drawdown=max_drawdown,
            portfolio_volatility=portfolio_vol,
            target_progress=target_progress,
            to_target=max(0.0, quarterly_target - total_value),
            target_met=total_value >= quarterly_target,
            sector_exposure=sector_exposure,
            largest_position=largest_sym,
            largest_position_pct=largest_pct,
            holdings=holdings_detail,
        )

    @staticmethod
    def validate_buy(
        cash: float,
        symbol: str,
        quantity: int,
        price: float,
        stocks_map: dict,
    ) -> tuple[bool, str]:
        """Returns (ok, error_message)."""
        if quantity <= 0:
            return False, "Quantity must be a positive integer."
        if symbol not in stocks_map:
            return False, f"Unknown symbol: {symbol}"
        total = quantity * price
        fee = total * 0.0002
        total_with_fee = total + fee
        if cash < total_with_fee:
            available_cr = cash / (100 * 10**6)
            needed_cr = total_with_fee / (100 * 10**6)
            return False, (
                f"Insufficient cash. Available: ₹{available_cr:.2f} Cr. "
                f"Required: ₹{needed_cr:.2f} Cr (including fee)."
            )
        return True, ""

    @staticmethod
    def validate_sell(
        holdings_db: list,
        symbol: str,
        quantity: int,
    ) -> tuple[bool, str, int]:
        """Returns (ok, error_message, current_qty)."""
        if quantity <= 0:
            return False, "Quantity must be a positive integer.", 0
        current_qty = 0
        for h in holdings_db:
            sym = h.symbol if hasattr(h, "symbol") else h.get("symbol", "")
            if sym == symbol:
                current_qty = int(h.quantity if hasattr(h, "quantity") else h.get("quantity", 0))
                break
        if current_qty == 0:
            return False, f"You do not hold any shares of {symbol}.", 0
        if quantity > current_qty:
            return False, (
                f"Cannot sell {quantity} shares. You only hold {current_qty} shares of {symbol}."
            ), current_qty
        return True, "", current_qty
