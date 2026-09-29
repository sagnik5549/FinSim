"""
Feature extraction for the player-behaviour model.

The same function produces features for live games and for the offline
training dataset, so training/serving skew is impossible by construction.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.simulation.state import GameState

FEATURE_NAMES = [
    "avg_invested",       # average fraction of capital invested
    "avg_max_weight",     # average largest-position weight
    "avg_hhi",            # average Herfindahl concentration
    "trades_per_day",     # trading frequency
    "loss_reaction",      # share of trades placed while the day was down >1%
    "news_reaction",      # share of trades placed within 2h of news on that stock
    "research_per_trade",
    "portfolio_vol",      # forward-looking annualised volatility
    "drawdown",
    "target_progress",
    "ignored_breaches",
    "block_deal_rate",
]


def extract(state: "GameState") -> dict[str, float]:
    from app.simulation import career_engine as ce
    from app.simulation import portfolio_engine as pe

    st = state.stats
    b = st.behavior_scores
    days = max(1.0, b.get("n", 0.0) / 8.0)
    trades = max(st.trades, 0)
    return {
        "avg_invested": round(b.get("avg_invested", 0.0), 4),
        "avg_max_weight": round(b.get("avg_max_weight", 0.0), 4),
        "avg_hhi": round(b.get("avg_hhi", 0.0), 4),
        "trades_per_day": round(trades / days, 4),
        "loss_reaction": round(st.trades_after_loss / trades, 4) if trades else 0.0,
        "news_reaction": round(st.trades_after_news / trades, 4) if trades else 0.0,
        "research_per_trade": round(st.research_count / trades, 4) if trades else float(st.research_count > 0),
        "portfolio_vol": round(pe.portfolio_volatility(state), 4),
        "drawdown": round(pe.current_drawdown(state), 4),
        "target_progress": round(ce.target_progress(state), 4),
        "ignored_breaches": float(state.career.ignored_violations),
        "block_deal_rate": round(st.block_deals / trades, 4) if trades else 0.0,
    }


def vector(f: dict[str, float]) -> list[float]:
    return [float(f.get(k, 0.0)) for k in FEATURE_NAMES]
