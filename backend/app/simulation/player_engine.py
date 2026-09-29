"""
Player engine — tracks behaviour and classifies the player's style.

The classification (CONSERVATIVE / BALANCED / AGGRESSIVE / SPECULATIVE) is
hidden from the player; it feeds the adaptive director and telemetry.
"""
from __future__ import annotations

from app.ml import features as feat
from app.ml.inference import get_behavior_model
from app.simulation.state import GameState


def track_hour(state: GameState) -> None:
    """Running averages of exposure and concentration (updated every simulated hour)."""
    from app.simulation import portfolio_engine as pe

    b = state.stats.behavior_scores
    total = pe.nav(state)
    invested = 1 - state.portfolio.cash / total if total else 0.0
    weights = [h.qty * state.stocks[h.symbol].price / total for h in state.portfolio.holdings.values()] if total else []
    maxw = max(weights, default=0.0)
    hhi = sum(w * w for w in weights)
    n = b.get("n", 0.0) + 1
    for key, val in (("avg_invested", invested), ("avg_max_weight", maxw), ("avg_hhi", hhi)):
        b[key] = b.get(key, 0.0) + (val - b.get(key, 0.0)) / n
    b["n"] = n


def features(state: GameState) -> dict[str, float]:
    return feat.extract(state)


def update_profile(state: GameState) -> None:
    model = get_behavior_model()
    label, proba = model.predict(features(state))
    state.stats.behavior_profile = label
    state.stats.behavior_scores.update({f"p_{k.lower()}": round(v, 3) for k, v in proba.items()})
