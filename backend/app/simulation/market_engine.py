import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.simulation.constants import (
    REGIME_PARAMS,
    SECTOR_MARKET_CORRELATION,
    WORKING_HOURS,
)


HOURS_PER_DAY = len(WORKING_HOURS)
HOURS_PER_YEAR = 252 * HOURS_PER_DAY


@dataclass
class StockSnapshot:
    symbol: str
    name: str
    sector: str
    current_price: float
    previous_price: float
    daily_open: float
    daily_high: float
    daily_low: float
    volume: int
    daily_return: float
    volatility: float
    beta: float
    sentiment: float
    momentum: float
    growth: float
    profitability: float
    debt: float
    valuation: float
    market_sensitivity: float
    event_sensitivity: float
    institutional_pressure: float


@dataclass
class MarketTickResult:
    updated_stocks: list[StockSnapshot]
    nifty: float
    sensex: float
    bank_nifty: float
    india_vix: float
    usdinr: float
    gold: float
    nasdaq: float
    sp500: float
    market_regime: str
    regime_changed: bool = False
    new_regime: Optional[str] = None


class MarketEngine:

    @staticmethod
    def _get(
        stock,
        field: str,
        default=0.0,
    ):
        if isinstance(stock, dict):
            return stock.get(field, default)

        return getattr(
            stock,
            field,
            default,
        )

    @staticmethod
    def _update_index(
        current: float,
        drift: float,
        rng: np.random.Generator,
        volatility: float,
    ) -> float:

        current = max(
            1.0,
            float(current),
        )

        shock = float(
            rng.normal(
                0.0,
                volatility,
            )
        )

        return max(
            1.0,
            current * (
                1.0
                + drift
                + shock
            ),
        )

    @staticmethod
    def _transition_regime(
        game,
        params: dict,
        rng: np.random.Generator,
    ) -> tuple[str, bool, Optional[str]]:

        current = str(
            game.market_regime
        ).upper()

        probabilities = params.get(
            "transition_probs",
            {},
        )

        if not probabilities:
            return current, False, None

        regimes = list(
            probabilities.keys()
        )

        probs = np.asarray(
            [
                float(
                    probabilities[regime]
                )
                for regime in regimes
            ],
            dtype=float,
        )

        total = probs.sum()

        if total <= 0:
            return current, False, None

        probs /= total

        selected = str(
            rng.choice(
                regimes,
                p=probs,
            )
        )

        if selected == current:
            return current, False, None

        return selected, True, selected

    @staticmethod
    def simulate_tick(
        stocks: list,
        game,
        rng: np.random.Generator,
        event_shocks: Optional[
            dict[str, float]
        ] = None,
    ) -> MarketTickResult:

        event_shocks = event_shocks or {}

        current_regime = str(
            game.market_regime
        ).upper()

        params = REGIME_PARAMS.get(
            current_regime,
            REGIME_PARAMS["STABLE"],
        )

        drift_range = params.get(
            "daily_drift_range",
            (-0.001, 0.002),
        )

        volatility_multiplier = float(
            params.get(
                "vol_multiplier",
                1.0,
            )
        )

        daily_drift = float(
            rng.uniform(
                *drift_range
            )
        )

        hourly_drift = (
            daily_drift
            / HOURS_PER_DAY
        )

        market_volatility = (
            0.012
            * volatility_multiplier
            / math.sqrt(HOURS_PER_DAY)
        )

        market_shock = float(
            rng.normal(
                0.0,
                market_volatility,
            )
        )

        market_factor = (
            hourly_drift
            + market_shock
        )

        nifty = MarketEngine._update_index(
            game.nifty_value,
            market_factor,
            rng,
            0.003
            * volatility_multiplier,
        )

        sensex = MarketEngine._update_index(
            game.sensex_value,
            market_factor * 1.02,
            rng,
            0.003
            * volatility_multiplier,
        )

        bank_nifty = MarketEngine._update_index(
            game.bank_nifty_value,
            market_factor * 1.15,
            rng,
            0.004
            * volatility_multiplier,
        )

        vix_change = (
            -market_factor * 15.0
            + rng.normal(
                0.0,
                0.30
                * volatility_multiplier,
            )
        )

        india_vix = max(
            8.0,
            min(
                80.0,
                float(game.india_vix_value)
                + vix_change,
            ),
        )

        usdinr_change = float(
            rng.normal(
                -market_factor * 0.30,
                0.05
                * volatility_multiplier,
            )
        )

        usdinr = max(
            70.0,
            min(
                100.0,
                float(game.usdinr_value)
                + usdinr_change,
            ),
        )

        gold = MarketEngine._update_index(
            game.gold_value,
            -market_factor * 0.30,
            rng,
            0.005
            * volatility_multiplier,
        )

        nasdaq = MarketEngine._update_index(
            game.nasdaq_value,
            market_factor * 0.80,
            rng,
            0.006
            * volatility_multiplier,
        )

        sp500 = MarketEngine._update_index(
            game.sp500_value,
            market_factor * 0.75,
            rng,
            0.005
            * volatility_multiplier,
        )

        sector_factors = {}

        for sector, correlation in (
            SECTOR_MARKET_CORRELATION.items()
        ):
            sector_noise = float(
                rng.normal(
                    0.0,
                    0.004
                    * volatility_multiplier,
                )
            )

            sector_factors[sector] = (
                float(correlation)
                * market_factor
                + (
                    1.0
                    - float(correlation)
                )
                * sector_noise
            )

        updated_stocks = []

        for stock in stocks:

            symbol = str(
                MarketEngine._get(
                    stock,
                    "symbol",
                    "",
                )
            ).upper()

            name = str(
                MarketEngine._get(
                    stock,
                    "name",
                    symbol,
                )
            )

            sector = str(
                MarketEngine._get(
                    stock,
                    "sector",
                    "Unknown",
                )
            )

            price = max(
                1.0,
                float(
                    MarketEngine._get(
                        stock,
                        "current_price",
                        1.0,
                    )
                ),
            )

            previous_price = float(
                MarketEngine._get(
                    stock,
                    "previous_price",
                    price,
                )
            )

            daily_open = max(
                1.0,
                float(
                    MarketEngine._get(
                        stock,
                        "daily_open",
                        price,
                    )
                ),
            )

            daily_high = max(
                price,
                float(
                    MarketEngine._get(
                        stock,
                        "daily_high",
                        price,
                    )
                ),
            )

            daily_low = min(
                price,
                float(
                    MarketEngine._get(
                        stock,
                        "daily_low",
                        price,
                    )
                ),
            )

            volatility = max(
                0.0001,
                float(
                    MarketEngine._get(
                        stock,
                        "volatility",
                        0.02,
                    )
                ),
            )

            beta = float(
                MarketEngine._get(
                    stock,
                    "beta",
                    1.0,
                )
            )

            sentiment = float(
                MarketEngine._get(
                    stock,
                    "sentiment",
                    0.5,
                )
            )

            momentum = float(
                MarketEngine._get(
                    stock,
                    "momentum",
                    0.0,
                )
            )

            growth = float(
                MarketEngine._get(
                    stock,
                    "growth",
                    0.10,
                )
            )

            profitability = float(
                MarketEngine._get(
                    stock,
                    "profitability",
                    0.10,
                )
            )

            debt = float(
                MarketEngine._get(
                    stock,
                    "debt",
                    0.30,
                )
            )

            valuation = float(
                MarketEngine._get(
                    stock,
                    "valuation",
                    0.50,
                )
            )

            market_sensitivity = float(
                MarketEngine._get(
                    stock,
                    "market_sensitivity",
                    1.0,
                )
            )

            event_sensitivity = float(
                MarketEngine._get(
                    stock,
                    "event_sensitivity",
                    0.5,
                )
            )

            institutional_pressure = float(
                MarketEngine._get(
                    stock,
                    "institutional_pressure",
                    0.0,
                )
            )

            fundamental_annual_drift = (
                growth * 0.50
                + profitability * 0.30
                - debt * 0.10
                + (1.0 - valuation) * 0.05
            )

            fundamental_hourly = (
                fundamental_annual_drift
                / HOURS_PER_YEAR
            )

            hourly_volatility = (
                volatility
                * volatility_multiplier
                / math.sqrt(HOURS_PER_DAY)
            )

            idiosyncratic_shock = float(
                rng.normal(
                    0.0,
                    hourly_volatility,
                )
            )

            sector_return = sector_factors.get(
                sector,
                market_factor,
            )

            sentiment_nudge = (
                sentiment - 0.5
            ) * 0.0002

            momentum_drift = (
                momentum * 0.0001
            )

            institutional_drift = (
                institutional_pressure
                * 0.0005
            )

            event_shock = float(
                event_shocks.get(
                    symbol,
                    0.0,
                )
            )

            total_return = (
                fundamental_hourly
                + (
                    beta
                    * sector_return
                    * market_sensitivity
                )
                + sentiment_nudge
                + momentum_drift
                + institutional_drift
                + idiosyncratic_shock
                + (
                    event_shock
                    * event_sensitivity
                )
            )

            total_return = float(
                np.clip(
                    total_return,
                    -0.30,
                    0.30,
                )
            )

            new_price = max(
                1.0,
                price
                * (
                    1.0
                    + total_return
                ),
            )

            new_price = round(
                new_price,
                2,
            )

            new_momentum = (
                0.90 * momentum
                + 0.10 * total_return
            )

            base_volume = max(
                1,
                int(
                    1_000_000
                    / max(
                        1.0,
                        new_price,
                    )
                ),
            )

            volume_factor = (
                1.0
                + abs(total_return)
                * 50.0
            )

            stock_volume = int(
                base_volume
                * volume_factor
                * rng.uniform(
                    0.80,
                    1.20,
                )
            )

            new_daily_high = max(
                daily_high,
                new_price,
            )

            new_daily_low = min(
                daily_low,
                new_price,
            )

            new_sentiment = float(
                np.clip(
                    sentiment
                    + rng.normal(
                        0.0,
                        0.01,
                    ),
                    0.0,
                    1.0,
                )
            )

            new_institutional_pressure = float(
                np.clip(
                    institutional_pressure
                    * 0.95,
                    -1.0,
                    1.0,
                )
            )

            daily_return = (
                (
                    new_price
                    / daily_open
                )
                - 1.0
            )

            updated_stocks.append(
                StockSnapshot(
                    symbol=symbol,
                    name=name,
                    sector=sector,
                    current_price=new_price,
                    previous_price=price,
                    daily_open=daily_open,
                    daily_high=new_daily_high,
                    daily_low=new_daily_low,
                    volume=stock_volume,
                    daily_return=daily_return,
                    volatility=volatility,
                    beta=beta,
                    sentiment=new_sentiment,
                    momentum=new_momentum,
                    growth=growth,
                    profitability=profitability,
                    debt=debt,
                    valuation=valuation,
                    market_sensitivity=market_sensitivity,
                    event_sensitivity=event_sensitivity,
                    institutional_pressure=(
                        new_institutional_pressure
                    ),
                )
            )

        (
            new_regime,
            regime_changed,
            selected_regime,
        ) = MarketEngine._transition_regime(
            game,
            params,
            rng,
        )

        return MarketTickResult(
            updated_stocks=updated_stocks,
            nifty=round(nifty, 2),
            sensex=round(sensex, 2),
            bank_nifty=round(
                bank_nifty,
                2,
            ),
            india_vix=round(
                india_vix,
                2,
            ),
            usdinr=round(
                usdinr,
                4,
            ),
            gold=round(
                gold,
                2,
            ),
            nasdaq=round(
                nasdaq,
                2,
            ),
            sp500=round(
                sp500,
                2,
            ),
            market_regime=new_regime,
            regime_changed=regime_changed,
            new_regime=selected_regime,
        )

    @staticmethod
    def reset_daily_ohlc(
        stocks: list,
    ) -> list:

        for stock in stocks:
            price = max(
                1.0,
                float(
                    MarketEngine._get(
                        stock,
                        "current_price",
                        1.0,
                    )
                ),
            )

            if hasattr(
                stock,
                "daily_open",
            ):
                stock.daily_open = price

            if hasattr(
                stock,
                "daily_high",
            ):
                stock.daily_high = price

            if hasattr(
                stock,
                "daily_low",
            ):
                stock.daily_low = price

            if hasattr(
                stock,
                "volume",
            ):
                stock.volume = 0

        return stocks