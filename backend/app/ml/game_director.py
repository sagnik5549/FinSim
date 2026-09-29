"""
Adaptive game director.

Runs once per trading day. It reads the player's (hidden) behaviour profile and
situation and adjusts *market-wide* dials within tight bounds:

  event_intensity  — overall frequency of news/events (0.85 .. 1.20)
  opportunity_rate — frequency of block-deal offers   (0.80 .. 1.40)
  regime_bias      — small tilts to regime-transition odds (±15%)

Fairness guarantees (enforced here, and tested):
  * it never selects which company an event hits, never looks at holdings
  * it never sets prices or event outcomes
  * all outputs are clipped to narrow ranges
"""
from __future__ import annotations

from typing import Any

import numpy as np

from app.simulation.state import GameState

BOUNDS = {"event_intensity": (0.85, 1.20), "opportunity_rate": (0.80, 1.40), "regime_bias": (-0.15, 0.15)}


def decide(state: GameState) -> dict[str, Any]:
    from app.ml.inference import get_behavior_model
    from app.simulation import career_engine as ce
    from app.simulation import portfolio_engine as pe

    profile = state.stats.behavior_profile
    prog = ce.target_progress(state)
    tprog = ce.time_progress(state)
    dd = pe.current_drawdown(state)
    pace = prog - tprog  # >0 ahead of schedule

    intensity = 1.0
    opp = 1.0
    bias: dict[str, float] = {}
    reasons = []

    # Cruising far ahead with a sleepy book -> a livelier (but fair) market.
    if pace > 0.3 and dd < 0.03:
        intensity += 0.12
        bias["VOLATILE"] = 0.10
        reasons.append("player comfortably ahead: raise market activity")
    # Struggling -> more chances to act, calmer tape; never a guaranteed bailout.
    if pace < -0.3 or dd > 0.07:
        intensity -= 0.08
        opp += 0.3
        bias["CRISIS"] = -0.10
        reasons.append("player under pressure: more opportunities, less chaos")
    # Style-specific narrative pressure
    if profile == "CONSERVATIVE" and pace < 0:
        opp += 0.15
        reasons.append("conservative & behind: surface opportunities")
    elif profile == "SPECULATIVE":
        intensity += 0.05
        reasons.append("speculative style: more news flow")
    difficulty = float(np.clip(1.0 + 0.5 * (intensity - 1.0) - 0.2 * (opp - 1.0), 0.8, 1.2))

    return {
        "event_intensity": float(np.clip(intensity, *BOUNDS["event_intensity"])),
        "opportunity_rate": float(np.clip(opp, *BOUNDS["opportunity_rate"])),
        "regime_bias": {k: float(np.clip(v, *BOUNDS["regime_bias"])) for k, v in bias.items()},
        "difficulty": round(difficulty, 3),
        "profile": profile,
        "reasons": reasons,
        "source": f"rules+{get_behavior_model().source}",
    }
