"""
Player-behaviour models behind one interface.

`RuleBasedBehaviorModel` is always available and is the fallback. A trained
scikit-learn / XGBoost classifier (see ml/training) is used when its artifact
exists. Swapping models never touches the game engine.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.ml.features import FEATURE_NAMES, vector

LABELS = ["CONSERVATIVE", "BALANCED", "AGGRESSIVE", "SPECULATIVE"]


class BehaviorModel(Protocol):
    source: str

    def predict(self, features: dict[str, float]) -> tuple[str, dict[str, float]]: ...


class RuleBasedBehaviorModel:
    source = "rules"

    def predict(self, f: dict[str, float]) -> tuple[str, dict[str, float]]:
        invested = f.get("avg_invested", 0.0)
        conc = min(1.5, f.get("avg_max_weight", 0.0) / 0.15)
        vol = min(1.5, f.get("portfolio_vol", 0.0) / 0.30)
        freq = min(1.5, f.get("trades_per_day", 0.0) / 3.0)
        aggression = 0.35 * invested + 0.30 * conc + 0.20 * vol + 0.15 * freq
        spec = aggression * 0.6 + 0.25 * f.get("news_reaction", 0.0) + 0.15 * freq \
            - 0.2 * min(1.0, f.get("research_per_trade", 0.0)) + 0.1 * min(2.0, f.get("ignored_breaches", 0.0))
        if spec > 0.72 and freq > 0.6:
            label = "SPECULATIVE"
        elif aggression > 0.7:
            label = "AGGRESSIVE"
        elif aggression > 0.38:
            label = "BALANCED"
        else:
            label = "CONSERVATIVE"
        # Soft pseudo-probabilities centred on the rule decision
        proba = {k: 0.1 for k in LABELS}
        proba[label] = 0.7
        return label, proba


class SklearnBehaviorModel:
    """Wraps any fitted estimator with predict_proba (sklearn, XGBoost sklearn API)."""

    def __init__(self, path: Path):
        import joblib

        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.labels = bundle["labels"]
        self.feature_names = bundle.get("features", FEATURE_NAMES)
        self.source = f"ml:{bundle.get('kind', 'sklearn')}"

    def predict(self, f: dict[str, float]) -> tuple[str, dict[str, float]]:
        x = [[float(f.get(k, 0.0)) for k in self.feature_names]]
        p = self.model.predict_proba(x)[0]
        proba = {self.labels[i]: float(p[i]) for i in range(len(self.labels))}
        return max(proba, key=proba.get), proba


__all__ = ["BehaviorModel", "RuleBasedBehaviorModel", "SklearnBehaviorModel", "LABELS", "vector"]
