"""Market realism, director fairness and ML fallback."""
import numpy as np

from app.ml import game_director
from app.ml.behavior_model import RuleBasedBehaviorModel
from app.ml.features import FEATURE_NAMES
from app.simulation.game_engine import GameEngine
from app.services import indicators


def test_market_is_generated_not_hardcoded():
    a = GameEngine.new_game("x1", seed=1).state
    b = GameEngine.new_game("x2", seed=2).state
    assert a.stocks["AKSH"].spark != b.stocks["AKSH"].spark


def test_daily_volatility_is_believable():
    eng = GameEngine.new_game("vol", seed=31)
    s = eng.state
    closes = []
    for _ in range(40):
        s.popups.clear()
        eng.advance("next_day")
        closes.append(s.indices["BH50"].prev_close)
    r = np.diff(np.log(closes))
    assert 0.004 < r.std() < 0.025


def test_director_is_bounded_and_portfolio_blind():
    eng = GameEngine.new_game("dir", seed=3)
    s = eng.state
    d1 = game_director.decide(s)
    eng.trade("BUY", "AKSH", 1000)
    d2 = game_director.decide(s)
    # holding a stock does not change market dials
    assert d1["event_intensity"] == d2["event_intensity"]
    for v in (d1, d2):
        assert 0.85 <= v["event_intensity"] <= 1.2
        assert 0.8 <= v["opportunity_rate"] <= 1.4
        assert all(-0.15 <= x <= 0.15 for x in v["regime_bias"].values())
        assert "symbol" not in str(v)


def test_behavior_model_fallback():
    m = RuleBasedBehaviorModel()
    label, proba = m.predict({k: 0.0 for k in FEATURE_NAMES})
    assert label == "CONSERVATIVE"
    label, _ = m.predict({"avg_invested": 1.0, "avg_max_weight": 0.3, "portfolio_vol": 0.4, "trades_per_day": 5,
                          "news_reaction": 0.8})
    assert label in ("AGGRESSIVE", "SPECULATIVE")


def test_indicators():
    rows = [{"t": f"2026-01-{i // 8 + 1:02d}T{9 + i % 8:02d}:00", "o": 100 + i, "h": 101 + i, "l": 99 + i,
             "c": 100 + i, "v": 10} for i in range(60)]
    ind = indicators.compute(rows)
    assert ind["sma20"][-1] == np.mean([100 + i for i in range(40, 60)])
    assert ind["rsi14"][-1] == 100.0
    daily = indicators.aggregate_daily(rows)
    assert len(daily) == 8 and daily[0]["o"] == 100 and daily[0]["c"] == 107


def test_trained_model_loads_when_present():
    import pytest
    from app.ml.behavior_model import SklearnBehaviorModel
    from app.ml.inference import BEHAVIOR_ARTIFACT
    if not BEHAVIOR_ARTIFACT.exists():
        pytest.skip("no trained artifact; rule-based fallback is used")
    m = SklearnBehaviorModel(BEHAVIOR_ARTIFACT)
    label, proba = m.predict({k: 0.0 for k in FEATURE_NAMES})
    assert label in proba and abs(sum(proba.values()) - 1) < 1e-6
    assert m.source.startswith("ml:")


def test_game_runs_without_ml(monkeypatch):
    """The game must stay playable if the ML model is unavailable."""
    from app.ml import inference
    monkeypatch.setenv("IBM_DISABLE_ML", "1")
    inference.reset_cache()
    eng = GameEngine.new_game("noml", seed=12)
    eng.advance("next_day")
    assert eng.state.stats.behavior_profile in ("CONSERVATIVE", "BALANCED", "AGGRESSIVE", "SPECULATIVE")
    inference.reset_cache()
