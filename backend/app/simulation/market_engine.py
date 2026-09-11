from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.simulation.constants import (
    REGIME_PARAMS,
    SECTOR_CORRELATIONS,
)


@dataclass
class MarketTickResult:
    regime: str
    regime_changed: bool
    index_values: dict[str, float]
    stock_prices: dict[str, float]


class MarketEngine:

    @staticmethod
    def _clamp_price(price: float) -> float:
        return max(0.01, float(price))

    @staticmethod
    def _get_regime_params(regime: str) -> dict:
        return REGIME_PARAMS.get(
            regime,
            REGIME_PARAMS["STABLE"],
        )

    @staticmethod
    def _sector_correlation(
        sector_a: str,
        sector_b: str,
    ) -> float:
        if sector_a == sector_b:
            return 1.0

        direct = SECTOR_CORRELATIONS.get(
            (sector_a, sector_b)
        )

        if direct is not None:
            return float(direct)

        reverse = SECTOR_CORRELATIONS.get(
            (sector_b, sector_a)
        )

        if reverse is not None:
            return float(reverse)

        return 0.25

    @staticmethod
    def _market_shock(
        rng: np.random.Generator,
        volatility: float,
    ) -> float:
        return float(
            rng.normal(
                0.0,
                max(0.0001, volatility),
            )
        )

    @staticmethod
    def _update_regime(
        game,
        rng: np.random.Generator,
    ) -> tuple[str, bool]:

        current_regime = str(
            game.market_regime
        ).upper()

        params = MarketEngine._get_regime_params(
            current_regime
        )

        remaining = int(
            game.regime_days_remaining or 0
        )

        if remaining > 0:
            return current_regime, False

        transitions = {
            "BULL": ["BULL", "STABLE", "VOLATILE"],
            "STABLE": ["STABLE", "BULL", "BEAR", "VOLATILE"],
            "VOLATILE": ["VOLATILE", "STABLE", "BEAR", "CRISIS"],
            "BEAR": ["BEAR", "STABLE", "VOLATILE", "CRISIS"],
            "CRISIS": ["CRISIS", "BEAR", "VOLATILE", "STABLE"],
        }

        candidates = transitions.get(
            current_regime,
            ["STABLE"],
        )

        if len(candidates) == 1:
            next_regime = candidates[0]
        else:
            weights = np.ones(
                len(candidates),
                dtype=float,
            )

            if current_regime in candidates:
                current_index = candidates.index(
                    current_regime
                )
                weights[current_index] = 3.0

            weights /= weights.sum()

            next_regime = str(
                rng.choice(
                    candidates,
                    p=weights,
                )
            )

        regime_params = MarketEngine._get_regime_params(
            next_regime
        )

        min_days = int(
            regime_params.get(
                "min_days",
                5,
            )
        )

        max_days = int(
            regime_params.get(
                "max_days",
                20,
            )
        )

        game.regime_days_remaining = int(
            rng.integers(
                min_days,
                max_days + 1,
            )
        )

        changed = (
            next_regime != current_regime
        )

        game.market_regime = next_regime

        return next_regime, changed

    @staticmethod
    def simulate_tick(
        stocks: list,
        game,
        rng: np.random.Generator,
        event_shocks: Optional[dict[str, float]] = None,
        sector_shocks: Optional[dict[str, float]] = None,
        market_nudge: float = 0.0,
    ) -> MarketTickResult:

        event_shocks = event_shocks or {}
        sector_shocks = sector_shocks or {}

        regime, regime_changed = (
            MarketEngine._update_regime(
                game,
                rng,
            )
        )

        params = MarketEngine._get_regime_params(
            regime
        )

        drift = float(
            params.get("drift", 0.0)
        )

        volatility = float(
            params.get("volatility", 0.02)
        )

        market_factor = MarketEngine._market_shock(
            rng,
            volatility / np.sqrt(8.0),
        )

        market_factor += float(
            np.clip(
                market_nudge,
                -0.02,
                0.02,
            )
        )

        stock_returns: dict[str, float] = {}

        for stock in stocks:
            symbol = str(
                stock.symbol
            ).upper()

            stock_volatility = max(
                0.0001,
                float(stock.volatility),
            )

            hourly_volatility = (
                stock_volatility
                / np.sqrt(8.0)
            )

            idiosyncratic = MarketEngine._market_shock(
                rng,
                hourly_volatility,
            )

            sector_factor = 0.0

            for other_stock in stocks:
                other_symbol = str(
                    other_stock.symbol
                ).upper()

                if other_symbol == symbol:
                    continue

                other_return = stock_returns.get(
                    other_symbol
                )

                if other_return is None:
                    continue

                correlation = (
                    MarketEngine._sector_correlation(
                        str(stock.sector),
                        str(other_stock.sector),
                    )
                )

                sector_factor += (
                    other_return
                    * correlation
                    * 0.05
                )

            event_impact = float(
                event_shocks.get(
                    symbol,
                    0.0,
                )
            )

            sector_impact = float(
                sector_shocks.get(
                    str(stock.sector),
                    0.0,
                )
            )

            return_value = (
                drift
                + market_factor
                + idiosyncratic
                + sector_factor
                + sector_impact
                + event_impact
            )

            regime_multiplier = {
                "BULL": 1.0,
                "STABLE": 1.0,
                "VOLATILE": 1.20,
                "BEAR": 1.15,
                "CRISIS": 1.50,
            }.get(
                regime,
                1.0,
            )

            return_value *= regime_multiplier

            stock_returns[symbol] = (
                float(return_value)
            )

        stock_prices: dict[str, float] = {}

        for stock in stocks:
            symbol = str(
                stock.symbol
            ).upper()

            old_price = max(
                0.01,
                float(stock.current_price),
            )

            return_value = stock_returns.get(
                symbol,
                0.0,
            )

            new_price = old_price * np.exp(
                return_value
            )

            new_price = MarketEngine._clamp_price(
                new_price
            )

            stock.current_price = round(
                new_price,
                4,
            )

            stock_prices[symbol] = (
                stock.current_price
            )

        indices = MarketEngine._update_indices(
            game,
            regime,
            market_factor,
            rng,
        )

        if game.regime_days_remaining:
            game.regime_days_remaining = max(
                0,
                int(game.regime_days_remaining) - 1,
            )

        return MarketTickResult(
            regime=regime,
            regime_changed=regime_changed,
            index_values=indices,
            stock_prices=stock_prices,
        )

    @staticmethod
    def _update_indices(
        game,
        regime: str,
        market_factor: float,
        rng: np.random.Generator,
    ) -> dict[str, float]:

        current_indices = dict(
            game.indices or {}
        )

        defaults = {
            "NIFTY": 22000.0,
            "SENSEX": 72000.0,
            "BANKNIFTY": 47000.0,
            "VIX": 14.0,
            "GOLD": 70000.0,
        }

        for name, value in defaults.items():
            current_indices.setdefault(
                name,
                value,
            )

        index_values = {}

        equity_multiplier = {
            "BULL": 1.10,
            "STABLE": 1.00,
            "VOLATILE": 1.15,
            "BEAR": 1.20,
            "CRISIS": 1.40,
        }.get(
            regime,
            1.0,
        )

        for name in (
            "NIFTY",
            "SENSEX",
            "BANKNIFTY",
        ):
            index_return = (
                market_factor
                * equity_multiplier
            )

            index_return += float(
                rng.normal(
                    0.0,
                    0.0015,
                )
            )

            index_values[name] = round(
                max(
                    1.0,
                    current_indices[name]
                    * np.exp(index_return),
                ),
                2,
            )

        vix_change = {
            "BULL": -0.02,
            "STABLE": 0.0,
            "VOLATILE": 0.04,
            "BEAR": 0.06,
            "CRISIS": 0.12,
        }.get(
            regime,
            0.0,
        )

        vix_return = (
            vix_change
            + abs(market_factor) * 1.5
            + float(
                rng.normal(
                    0.0,
                    0.01,
                )
            )
        )

        index_values["VIX"] = round(
            max(
                8.0,
                current_indices["VIX"]
                * np.exp(vix_return),
            ),
            2,
        )

        gold_return = (
            -market_factor * 0.15
            + (
                0.004
                if regime == "CRISIS"
                else 0.0
            )
            + float(
                rng.normal(
                    0.0,
                    0.001,
                )
            )
        )

        index_values["GOLD"] = round(
            max(
                1000.0,
                current_indices["GOLD"]
                * np.exp(gold_return),
            ),
            2,
        )

        return index_values

    @staticmethod
    def reset_daily_ohlc(
        stocks: list,
    ) -> None:

        for stock in stocks:
            price = max(
                0.01,
                float(stock.current_price),
            )

            stock.day_open = price
            stock.day_high = price
            stock.day_low = price
            stock.day_close = price
            stock.day_volume = 0

    @staticmethod
    def update_daily_ohlc(
        stocks: list,
        volume_multiplier: float = 1.0,
    ) -> None:

        volume_multiplier = max(
            0.0,
            float(volume_multiplier),
        )

        for stock in stocks:
            price = max(
                0.01,
                float(stock.current_price),
            )

            if stock.day_open is None:
                stock.day_open = price

            if stock.day_high is None:
                stock.day_high = price

            if stock.day_low is None:
                stock.day_low = price

            stock.day_high = max(
                float(stock.day_high),
                price,
            )

            stock.day_low = min(
                float(stock.day_low),
                price,
            )

            stock.day_close = price

            base_volume = max(
                0,
                int(stock.avg_volume),
            )

            hourly_volume = (
                base_volume
                / 8.0
            )

            stock.day_volume = int(
                (stock.day_volume or 0)
                + max(
                    1,
                    hourly_volume
                    * volume_multiplier,
                )
            )