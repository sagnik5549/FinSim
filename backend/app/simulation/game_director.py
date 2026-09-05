"""
GameDirector — rule-based adaptive director that adjusts event probabilities,
market narrative pressure, and scenario selection based on player behavior.
Phase 1 implementation: pure rule-based. ML layer plugs in here in Phase 2.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class DirectorState:
    player_risk_profile: str    # CONSERVATIVE, BALANCED, AGGRESSIVE, SPECULATIVE
    tension_level: float        # 0–1, controls narrative pressure
    suggested_event_boost: float # multiplier on event probabilities
    market_nudge: float         # small directional nudge to market regime transitions


class GameDirector:
    """
    Takes a read of the game state and returns director instructions.
    The director NEVER cheats the player — it adjusts probability, not outcomes.
    """

    @staticmethod
    def evaluate(
        career_day: int,
        target_progress: float,
        reputation: float,
        cash_ratio: float,
        trade_count_today: int,
        max_drawdown: float,
        market_regime: str,
        portfolio_volatility: float,
        rng: np.random.Generator,
    ) -> DirectorState:
        """
        Return director state that subtly guides narrative.
        Never directly rigged — only probability adjustments.
        """

        # ── Classify player risk profile ──
        if cash_ratio > 0.7:
            profile = "CONSERVATIVE"
        elif cash_ratio > 0.4:
            profile = "BALANCED"
        elif portfolio_volatility > 0.25:
            profile = "SPECULATIVE"
        else:
            profile = "AGGRESSIVE"

        # ── Tension: builds as we approach quarter end with low progress ──
        days_remaining = 90 - career_day
        time_pressure = 1.0 - (days_remaining / 90)
        progress_gap = max(0.0, 1.0 - target_progress)
        tension = min(1.0, time_pressure * 0.5 + progress_gap * 0.6)

        # ── Event probability boost based on tension ──
        # More tension → more events (but never guaranteed crashes)
        event_boost = 1.0 + tension * 0.5

        # ── If player is too comfortable (high progress, low vol), add interest ──
        if target_progress > 0.95 and market_regime == "STABLE":
            event_boost *= 1.3  # more interesting events when player is cruising

        # ── Market nudge: slight bias toward opportunity creation when player is far behind ──
        market_nudge = 0.0
        if target_progress < 0.3 and career_day > 45:
            # Create conditions for recovery opportunity — NOT a free win
            market_nudge = 0.002  # tiny positive nudge in transition probabilities
        elif target_progress > 0.9 and days_remaining < 10:
            # Player is close to target — no nudging needed
            market_nudge = 0.0

        return DirectorState(
            player_risk_profile=profile,
            tension_level=round(tension, 3),
            suggested_event_boost=round(event_boost, 2),
            market_nudge=market_nudge,
        )

    @staticmethod
    def classify_behavior(
        avg_cash_ratio: float,
        avg_daily_trades: float,
        reaction_to_loss_ratio: float,  # how quickly player sold after losses
        position_concentration: float,
    ) -> str:
        """Classify player investment behavior for telemetry and career review."""
        if avg_cash_ratio > 0.6:
            return "CONSERVATIVE"
        if position_concentration > 0.5:
            return "SPECULATIVE"
        if avg_daily_trades > 5:
            return "AGGRESSIVE"
        return "BALANCED"
