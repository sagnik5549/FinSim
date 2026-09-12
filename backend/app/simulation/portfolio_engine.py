from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from app.simulation.constants import CRORE, TRANSACTION_FEE_RATE


@dataclass
class PortfolioMetrics:
    cash: float
    invested_value: float
    total_value: float
    starting_capital: float
    quarterly_target: float
    total_pnl: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    daily_pnl: float
    max_drawdown: float
    portfolio_volatility: float
    target_progress: float
    to_target: float
    target_met: bool
    sector_exposure: dict[str, float] = field(default_factory=dict)
    largest_position: str | None = None
    largest_position_pct: float = 0.0
    holdings: list[dict[str, Any]] = field(default_factory=list)


class PortfolioEngine:

    @staticmethod
    def fee_for_trade(value: float) -> float:
        if value <= 0:
            return 0.0

        return round(
            value * TRANSACTION_FEE_RATE,
            2,
        )

    @staticmethod
    def compute(
        cash: float,
        holdings_db: list,
        stocks_map: dict,
        starting_capital: float,
        quarterly_target: float,
        peak_portfolio_value: float,
        daily_open_portfolio: float,
        realized_pnl: float,
    ) -> PortfolioMetrics:

        cash = max(0.0, float(cash))
        starting_capital = max(
            0.0,
            float(starting_capital),
        )
        quarterly_target = float(quarterly_target)
        daily_open_portfolio = float(
            daily_open_portfolio
        )
        realized_pnl = float(realized_pnl)

        holdings: list[dict[str, Any]] = []
        sector_values: dict[str, float] = {}

        invested_value = 0.0
        unrealized_pnl = 0.0

        for holding in holdings_db:
            quantity = int(holding.quantity)

            if quantity <= 0:
                continue

            symbol = str(
                holding.symbol
            ).upper().strip()

            stock = stocks_map.get(symbol)

            if stock is None:
                continue

            price = max(
                0.0,
                float(stock.current_price),
            )

            avg_buy_price = max(
                0.0,
                float(holding.avg_buy_price),
            )

            market_value = quantity * price
            cost_basis = quantity * avg_buy_price
            position_pnl = market_value - cost_basis

            invested_value += market_value
            unrealized_pnl += position_pnl

            sector = str(
                stock.sector
            )

            sector_values[sector] = (
                sector_values.get(sector, 0.0)
                + market_value
            )

            holdings.append(
                {
                    "symbol": symbol,
                    "name": stock.name,
                    "sector": sector,
                    "quantity": quantity,
                    "avg_buy_price": avg_buy_price,
                    "current_price": price,
                    "cost_basis": cost_basis,
                    "current_value": market_value,
                    "market_value": market_value,
                    "unrealized_pnl": position_pnl,
                    "unrealized_pnl_pct": (
                        (position_pnl / cost_basis * 100)
                        if cost_basis > 0
                        else 0.0
                    ),
                }
            )

        total_value = cash + invested_value

        if starting_capital > 0:
            total_pnl = (
                total_value
                - starting_capital
            )

            total_return_pct = (
                total_pnl
                / starting_capital
                * 100
            )
        else:
            total_pnl = 0.0
            total_return_pct = 0.0

        if daily_open_portfolio > 0:
            daily_pnl = (
                total_value
                - daily_open_portfolio
            )
        else:
            daily_pnl = 0.0

        peak = max(
            float(peak_portfolio_value),
            total_value,
            0.0,
        )

        if peak > 0:
            max_drawdown = max(
                0.0,
                (peak - total_value) / peak,
            )
        else:
            max_drawdown = 0.0

        if total_value > 0:
            for item in holdings:
                item["position_pct"] = (
                    item["market_value"]
                    / total_value
                )

            sector_exposure = {
                sector: value / total_value
                for sector, value in sector_values.items()
            }
        else:
            sector_exposure = {}

            for item in holdings:
                item["position_pct"] = 0.0

        if holdings:
            largest = max(
                holdings,
                key=lambda item: item["market_value"],
            )

            largest_position = largest["symbol"]
            largest_position_pct = (
                largest["current_value"]
                / total_value
                if total_value > 0
                else 0.0
            )
        else:
            largest_position = None
            largest_position_pct = 0.0

        weighted_variance = 0.0

        if total_value > 0:
            for item in holdings:
                stock = stocks_map.get(
                    item["symbol"]
                )

                if stock is None:
                    continue

                weight = (
                    item["current_value"]
                    / total_value
                )

                volatility = max(
                    0.0,
                    float(stock.volatility),
                )

                weighted_variance += (
                    weight
                    * volatility
                ) ** 2

        portfolio_volatility = (
            sqrt(weighted_variance)
            * sqrt(252)
        )

        target_gap = (
            quarterly_target
            - starting_capital
        )

        if target_gap > 0:
            target_progress = (
                total_value
                - starting_capital
            ) / target_gap
        else:
            target_progress = (
                1.0
                if total_value >= quarterly_target
                else 0.0
            )

        target_progress = max(
            0.0,
            min(1.0, target_progress),
        )

        to_target = max(
            0.0,
            quarterly_target - total_value,
        )

        target_met = (
            total_value >= quarterly_target
        )

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
            portfolio_volatility=portfolio_volatility,
            target_progress=target_progress,
            to_target=to_target,
            target_met=target_met,
            sector_exposure=sector_exposure,
            largest_position=largest_position,
            largest_position_pct=largest_position_pct,
            holdings=holdings,
        )

    @staticmethod
    def validate_buy(
        cash: float,
        symbol: str,
        quantity: int,
        price: float,
        stocks_map: dict,
    ) -> tuple[bool, str]:

        symbol = str(symbol).upper().strip()

        if symbol not in stocks_map:
            return False, f"Unknown symbol: {symbol}"

        if isinstance(quantity, bool) or quantity <= 0:
            return False, "Quantity must be positive."

        price = float(price)

        if price <= 0:
            return False, "Stock price must be positive."

        trade_value = quantity * price
        fee = PortfolioEngine.fee_for_trade(
            trade_value
        )

        total_cost = (
            trade_value + fee
        )

        if total_cost > float(cash):
            return (
                False,
                (
                    f"Insufficient cash. "
                    f"Required ₹{total_cost / CRORE:.4f} Cr, "
                    f"available ₹{float(cash) / CRORE:.4f} Cr."
                ),
            )

        return True, "BUY validated."

    @staticmethod
    def validate_sell(
        holdings_db: list,
        symbol: str,
        quantity: int,
    ) -> tuple[bool, str, int]:

        symbol = str(symbol).upper().strip()

        if isinstance(quantity, bool) or quantity <= 0:
            return (
                False,
                "Quantity must be positive.",
                0,
            )

        holding = next(
            (
                item
                for item in holdings_db
                if str(item.symbol).upper().strip()
                == symbol
            ),
            None,
        )

        if holding is None:
            return (
                False,
                f"You do not hold {symbol}.",
                0,
            )

        available = int(
            holding.quantity
        )

        if quantity > available:
            return (
                False,
                (
                    f"Cannot sell {quantity:,} shares. "
                    f"You only hold {available:,}."
                ),
                available,
            )

        return (
            True,
            "SELL validated.",
            available,
        )