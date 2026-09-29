"""Acceptance tests 15-29: time, weekends, leave and career."""
from datetime import datetime, timedelta

import pytest

from app.simulation import portfolio_engine as pe
from app.simulation.game_engine import ActionError, GameEngine
from app.simulation.state import ScheduledEvent
from tests.conftest import clear_blocking


def test_monday_plus_one_hour(engine):
    s = engine.state
    assert s.now.strftime("%A %H:%M") == "Monday 09:00"
    engine.advance("hour")
    assert s.now.strftime("%A %H:%M") == "Monday 10:00"


def test_skip_hours_processes_every_hour(engine):
    s = engine.state
    t0 = s.now
    # Put scheduled items inside the skipped window: each must be processed.
    for h in (10, 11, 12, 13):
        s.scheduled.append(ScheduledEvent(id=f"T{h}", time=t0.replace(hour=h), kind="EARNINGS",
                                          title="test", symbol="AKSH"))
    hourly_before = len(s.portfolio.hourly_nav)
    done = engine.advance("hours", 4)["hours_simulated"]
    assert done == 4
    assert s.now == t0 + timedelta(hours=4)
    assert all(x.processed for x in s.scheduled if x.id.startswith("T"))
    assert len(s.portfolio.hourly_nav) == hourly_before + 4
    assert s.last_tick.t == t0 + timedelta(hours=3)


def test_skip_hours_stops_at_close(engine):
    s = engine.state
    engine.advance("hours", 6)
    clear_blocking(engine)
    res = engine.advance("hours", 4)
    assert s.now.hour == 17 and res["hours_simulated"] == 2
    with pytest.raises(ActionError):
        engine.advance("hours", 1)


def test_friday_skip_weekend_reaches_monday(engine):
    s = engine.state
    while s.now.weekday() != 4:
        engine.advance("next_day")
        clear_blocking(engine)
    engine.advance("weekend")
    assert s.now.weekday() == 0 and s.now.hour == 9
    assert any(p.type == "WEEKEND_REPORT" for p in s.popups)


def test_skip_weekend_rejected_midweek(engine):
    with pytest.raises(ActionError):
        engine.advance("weekend")


def test_weekend_events_processed(engine):
    s = engine.state
    while s.now.weekday() != 4:
        engine.advance("next_day")
        clear_blocking(engine)
    # Force a weekend event to exist and check it lands in the Monday gap
    s.market.event_intensity = 1.2
    n_before = s.counters.get("EVT", 0)
    fri_prices = None
    for _ in range(6):  # several weekends to be statistically certain events occur
        engine.advance("next_day") if s.now.weekday() != 4 else engine.advance("weekend")
        clear_blocking(engine)
    assert s.counters.get("EVT", 0) > n_before


def test_leave_advances_calendar_and_allowance(engine):
    s = engine.state
    start = s.now
    nav0 = pe.nav(s)
    engine.trade("BUY", "GMBK", 10_000)
    res = engine.take_leave(3)
    assert res["leave"]["days_away"] == 3
    assert s.leave.used == 3
    assert s.leave.allowance - s.leave.used == 57
    assert s.now.date() > start.date() + timedelta(days=2)
    assert s.now.hour == 9 and s.now.weekday() < 5
    assert not s.leave.is_on_leave
    assert any(p.type == "LEAVE_REPORT" for p in s.popups)
    assert pe.nav(s) != nav0  # market & portfolio kept evolving
    assert res["leave"]["new_events"] >= 0


def test_leave_cannot_exceed_allowance(engine):
    s = engine.state
    s.leave.used = 58
    with pytest.raises(ActionError) as e:
        engine.take_leave(3)
    assert e.value.code == "LEAVE_EXCEEDED"


def test_events_during_leave_processed(engine):
    s = engine.state
    n_news = s.counters.get("NEWS", 0)
    engine.take_leave(5)
    assert s.counters.get("NEWS", 0) > n_news + 5  # at least daily market wraps + events


def test_game_time_persists(game):
    c, h, _ = game
    c.post("/api/game/advance-hours", headers=h, json={"hours": 3})
    saved = c.post("/api/game/save", headers=h, json={"name": "t"}).json()
    c.post("/api/game/advance-next-business-day", headers=h)
    st = c.post("/api/game/load", headers=h, json={"save_id": saved["id"]}).json()["state"]
    assert st["clock"]["time"] == "12:00"


def test_quarter_ends_in_review_with_multiple_metrics(engine):
    s = engine.state
    engine.trade("BUY", "KESR", 1000)
    guard = 0
    while s.career.status == "ACTIVE" and guard < 200:
        clear_blocking(engine)
        if s.career.status != "ACTIVE":
            break
        engine.advance("next_day")
        guard += 1
    review = s.career.last_review
    assert review is not None
    assert review["outcome"] in ("PROMOTED", "TARGET ACHIEVED", "WARNING", "FAILED", "TERMINATED")
    assert set(review["scores"]) >= {"return", "risk", "reputation", "alpha", "decision_quality"}
    assert (s.now.date() - s.career.quarter_start.date()).days <= 90
    assert any(p.type == "REVIEW" for p in s.popups)


def test_review_outcomes_use_more_than_profit():
    """Same return, different risk conduct -> different outcome."""
    from app.simulation import career_engine as ce

    def run(ignored: int, mdd: float):
        eng = GameEngine.new_game("rv", seed=5)
        s = eng.state
        s.portfolio.cash = s.career.target_value * 1.01
        s.portfolio.max_drawdown = mdd
        s.career.ignored_violations = ignored
        return ce.quarterly_review(s)["outcome"]

    assert run(0, 0.04) == "PROMOTED"
    assert run(4, 0.04) == "TARGET ACHIEVED"
    assert run(0, 0.25) == "TERMINATED"


def test_reputation_changes_with_performance():
    from app.simulation import career_engine as ce
    eng = GameEngine.new_game("rp", seed=6)
    s = eng.state
    r0 = s.career.reputation
    ce.daily_reputation(s, 0.02, 0.0, 0)
    assert s.career.reputation > r0
    r1 = s.career.reputation
    ce.daily_reputation(s, -0.02, 0.0, 0)
    assert s.career.reputation < r1


def test_warning_ladder_to_termination():
    from app.simulation import career_engine as ce
    eng = GameEngine.new_game("wl", seed=8)
    s = eng.state
    s.portfolio.cash = s.portfolio.quarter_start_value * 0.99  # missed target, small loss
    s.career.warning_level = 2  # already on final warning
    out = ce.quarterly_review(s)
    assert out["outcome"] == "TERMINATED"


def test_drawdown_breach_triggers_ceo_warning(engine):
    s = engine.state
    engine.trade("BUY", "PRKS", int(0.14 * pe.nav(s) / s.stocks["PRKS"].price))
    # Crash the stock hard (simulated price shock) and let the hour process it
    s.portfolio.peak_value = pe.nav(s) * 1.12
    engine.advance("hour")
    assert s.career.warning_level >= 1
    assert any(p.type == "DIALOGUE" for p in s.popups) or any(p.type == "RISK_WARNING" for p in s.popups)


def test_termination_blocks_further_play(engine):
    s = engine.state
    s.portfolio.peak_value = pe.nav(s) * 1.3  # 23% drawdown
    engine.advance("hour")
    assert s.career.status == "TERMINATED"
    with pytest.raises(ActionError) as e:
        engine.advance("hour")
    assert e.value.code == "CAREER_OVER"


def test_next_quarter_after_review(engine):
    from app.simulation import career_engine as ce
    s = engine.state
    s.portfolio.cash = s.career.target_value * 1.05
    s.now = s.career.quarter_end - timedelta(days=1)
    s.now = s.now.replace(hour=17)
    while s.now.weekday() > 4:
        s.now -= timedelta(days=1)
    engine.advance("next_day")
    review = next(p for p in s.popups if p.type == "REVIEW")
    assert review.payload["outcome"] in ("PROMOTED", "TARGET ACHIEVED")
    engine.ack_popup(review.id)
    assert s.career.status == "ACTIVE" and s.career.quarter_index == 2
    assert s.now.hour == 9
