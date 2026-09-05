"""
MarketEngine — GBM-based price simulation with market regimes,
sector factors, fundamentals, and event shocks.
All prices in INR.
"""
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.simulation.constants import (
    REGIME_PARAMS, SECTOR_MARKET_CORRELATION,
    MARKET_OPEN_HOUR, MARKET_CLOSE_HOUR, WORKING_HOURS,
    INDEX_DEFAULTS,
)


# Hourly time fraction (8 market hours per day, 252 trading days/year)
HOURS_PER_YEAR = 252 * len(WORKING_HOURS)
DT = 1.0 / HOURS_PER_YEAR


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
    """Result of one hourly market simulation step."""
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
    """
    Stateless market simulator. Takes current state + rng seed, returns updated state.
    Uses GBM with correlated sector factors.
    """

    @staticmethod
    def simulate_tick(
        stocks: list[dict],
        game: "Game",  # type: ignore  (avoids circular import)
        rng: np.random.Generator,
        event_shocks: Optional[dict[str, float]] = None,
    ) -> MarketTickResult:
        """
        Simulate one market hour.
        
        Args:
            stocks: current stock state dicts (from DB or in-memory)
            game: current game state
            rng: seeded numpy random generator
            event_shocks: symbol → additional price shock fraction
        """
        regime = game.market_regime
        params = REGIME_PARAMS[regime]
        event_shocks = event_shocks or {}

        # ── Market factor (NIFTY direction for this hour) ──
        drift_range = params["daily_drift_range"]
        vol_mult = params["vol_multiplier"]
        market_daily_drift = rng.uniform(*drift_range)
        market_hourly_drift = market_daily_drift / len(WORKING_HOURS)
        market_vol = 0.012 * vol_mult / math.sqrt(len(WORKING_HOURS))
        market_shock = rng.normal(0, market_vol)
        market_factor = market_hourly_drift + market_shock  # fractional

        # ── Update indices ──
        nifty = MarketEngine._update_index(
            game.nifty_value, market_factor, 0.0, rng, 0.003 * vol_mult
        )
        sensex = MarketEngine._update_index(
            game.sensex_value, market_factor * 1.02, 0.0, rng, 0.003 * vol_mult
        )
        bank_nifty = MarketEngine._update_index(
            game.bank_nifty_value, market_factor * 1.15, 0.0, rng, 0.004 * vol_mult
        )
        # VIX moves inversely and is mean-reverting
        vix_change = -market_factor * 15 + rng.normal(0, 0.3)
        india_vix = max(8.0, min(80.0, game.india_vix_value + vix_change))
        # USD/INR — slight inverse to market
        usdinr_change = rng.normal(-market_factor * 0.3, 0.05)
        usdinr = max(70.0, min(100.0, game.usdinr_value + usdinr_change))
        # Gold — safe haven, slight inverse to market
        gold = MarketEngine._update_index(
            game.gold_value, -market_factor * 0.3, 0.0, rng, 0.005
        )
        # Global indices
        nasdaq = MarketEngine._update_index(
            game.nasdaq_value, market_factor * 0.8, 0.0, rng, 0.006
        )
        sp500 = MarketEngine._update_index(
            game.sp500_value, market_factor * 0.75, 0.0, rng, 0.005
        )

        # ── Sector factors ──
        sector_factors: dict[str, float] = {}
        for sector, corr in SECTOR_MARKET_CORRELATION.items():
            sector_idio = rng.normal(0, 0.004 * vol_mult)
            sector_factors[sector] = corr * market_factor + (1 - corr) * sector_idio

        # ── Update each stock ──
        updated_stocks = []
        for s in stocks:
            symbol = s["symbol"] if isinstance(s, dict) else s.symbol
            name = s["name"] if isinstance(s, dict) else s.name
            sector = s["sector"] if isinstance(s, dict) else s.sector
            price = s["current_price"] if isinstance(s, dict) else s.current_price
            prev_price = s.get("previous_price", price) if isinstance(s, dict) else s.previous_price
            daily_open = s.get("daily_open", price) if isinstance(s, dict) else s.daily_open
            daily_high = s.get("daily_high", price) if isinstance(s, dict) else s.daily_high
            daily_low = s.get("daily_low", price) if isinstance(s, dict) else s.daily_low
            vol = s.get("volatility", 0.02) if isinstance(s, dict) else s.volatility
            beta = s.get("beta", 1.0) if isinstance(s, dict) else s.beta
            sentiment = s.get("sentiment", 0.5) if isinstance(s, dict) else s.sentiment
            momentum = s.get("momentum", 0.0) if isinstance(s, dict) else s.momentum
            growth = s.get("growth", 0.1) if isinstance(s, dict) else s.growth
            profitability = s.get("profitability", 0.1) if isinstance(s, dict) else s.profitability
            debt = s.get("debt", 0.3) if isinstance(s, dict) else s.debt
            valuation = s.get("valuation", 0.5) if isinstance(s, dict) else s.valuation
            mkt_sens = s.get("market_sensitivity", 1.0) if isinstance(s, dict) else s.market_sensitivity
            evt_sens = s.get("event_sensitivity", 0.5) if isinstance(s, dict) else s.event_sensitivity
            inst_press = s.get("institutional_pressure", 0.0) if isinstance(s, dict) else s.institutional_pressure

            # Fundamental drift (annualized → hourly)
            fundamental_annual_drift = (
                growth * 0.5           # growth premium
                + profitability * 0.3   # profitability premium
                - debt * 0.1           # debt discount
                + (1 - valuation) * 0.05  # mean-reversion from overvaluation
            )
            fundamental_hourly = fundamental_annual_drift / HOURS_PER_YEAR

            # Combine factors
            hourly_vol = vol * vol_mult / math.sqrt(len(WORKING_HOURS))
            idio_shock = rng.normal(0, hourly_vol)
            sector_return = sector_factors.get(sector, market_factor)
            sentiment_nudge = (sentiment - 0.5) * 0.0002  # small nudge
            momentum_drift = momentum * 0.0001
            inst_drift = inst_press * 0.0005

            # GBM step
            total_return = (
                fundamental_hourly
                + beta * sector_return * mkt_sens
                + sentiment_nudge
                + momentum_drift
                + inst_drift
                + idio_shock
                + event_shocks.get(symbol, 0.0)
            )
            new_price = max(1.0, price * (1 + total_return))
            new_price = round(new_price, 2)

            # Update momentum (exponential decay)
            new_momentum = 0.9 * momentum + 0.1 * total_return

            # Volume (proportional to abs price move, with noise)
            base_volume = int(1_000_000 / max(1, new_price))
            vol_factor = 1.0 + abs(total_return) * 50
            stock_volume = int(base_volume * vol_factor * rng.uniform(0.8, 1.2))

            new_daily_high = max(daily_high, new_price)
            new_daily_low = min(daily_low, new_price)

            updated_stocks.append(StockSnapshot(
                symbol=symbol,
                name=name,
                sector=sector,
                current_price=new_price,
                previous_price=price,
                daily_open=daily_open,
                daily_high=new_daily_high,
                daily_low=new_daily_low,
                volume=stock_volume,
                daily_return=(new_price - daily_open) / daily_open if daily_open > 0 else 0.0,
                volatility=vol,
                beta=beta,
                sentiment=max(0.0, min(1.0, sentiment + rng.normal(0, 0.01))),
                momentum=new_momentum,
                growth=growth,
                profitability=profitability,
                debt=debt,
                valuation=valuation,
                market_sensitivity=mkt_sens,
                event_sensitivity=evt_sens,
                institutional_pressure=max(-1.0, min(1.0, inst_press * 0.95)),
            ))

        # ── Regime transition check ──
        regime_changed = False
        new_regime_name = None
        if rng.random() < 0.015:  # ~1.5% chance each hour to reconsider regime
            transition_probs = params["transition_probs"]
            regimes = list(transition_probs.keys())
            probs = [transition_probs[r] for r in regimes]
            new_regime_name = rng.choice(regimes, p=probs)
            if new_regime_name != regime:
                regime_changed = True

        return MarketTickResult(
            updated_stocks=updated_stocks,
            nifty=round(nifty, 2),
            sensex=round(sensex, 2),
            bank_nifty=round(bank_nifty, 2),
            india_vix=round(india_vix, 2),
            usdinr=round(usdinr, 4),
            gold=round(gold, 2),
            nasdaq=round(nasdaq, 2),
            sp500=round(sp500, 2),
            market_regime=new_regime_name if regime_changed else regime,
            regime_changed=regime_changed,
            new_regime=new_regime_name if regime_changed else None,
        )

    @staticmethod
    def _update_index(
        current: float,
        drift: float,
        mean_reversion: float,
        rng: np.random.Generator,
        vol: float,
    ) -> float:
        shock = rng.normal(0, vol)
        return max(1.0, current * (1 + drift + shock))

    @staticmethod
    def reset_daily_ohlc(stocks: list) -> list:
        """Reset open/high/low at start of each trading day."""
        for s in stocks:
            if hasattr(s, 'daily_open'):
                s.daily_open = s.current_price
                s.daily_high = s.current_price
                s.daily_low = s.current_price
        return stocks
