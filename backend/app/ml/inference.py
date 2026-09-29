"""
Model loading with graceful fallback. The game never depends on ML being present.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from app.ml.behavior_model import BehaviorModel, RuleBasedBehaviorModel, SklearnBehaviorModel

log = logging.getLogger(__name__)
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
BEHAVIOR_ARTIFACT = ARTIFACT_DIR / "behavior_model.joblib"


@lru_cache(maxsize=1)
def get_behavior_model() -> BehaviorModel:
    if os.environ.get("IBM_DISABLE_ML") == "1":
        return RuleBasedBehaviorModel()
    if BEHAVIOR_ARTIFACT.exists():
        try:
            return SklearnBehaviorModel(BEHAVIOR_ARTIFACT)
        except Exception as exc:  # corrupt artifact / missing library -> rules
            log.warning("Behaviour model unavailable (%s); using rule-based fallback.", exc)
    return RuleBasedBehaviorModel()


def reset_cache() -> None:
    get_behavior_model.cache_clear()
