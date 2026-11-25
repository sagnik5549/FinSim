"""Live clock, resting orders, brackets, price alerts, research jobs and intraday charts."""
from datetime import timedelta

import pytest

from app.simulation.game_engine import ActionError, GameEngine
from app.simulation.state import Popup

SESSION = 7200.0  # 1x: one 8-hour session in two real hours -> 15 s per game minute
CLOSED = 45.0


def sync(eng: GameEngine, wall: float) -> bool:
    return eng.sync_live(wall, SESSION, CLOSED)


def test_live_clock_runs_at_15_seconds_per_minute(engine):
    s = engine.state
    t0 = s.now
    assert sync(engine, 1000.0)  # first sync only anchors the clock
    assert s.now == t0
    assert not sync(engine, 1014.0)  # under one game minute: nothing to do, nothing to save
    assert sync(engine, 1060.0)
    assert s.now == t0 + timedelta(minutes=4)
    assert s.hour is not None and s.hour.minute == 4
    assert s.recent.t[-4:] == [(t0 + timedelta(minutes=m)).isoformat() for m in range(4)]


def test_live_speed_multiplies_pace(engine):
    s = engine.state
    t0 = s.now
    engine.set_speed(4, [1, 2, 4])
    sync(engine, 0.0)
    sync(engine, 60.0)
    assert s.now == t0 + timedelta(minutes=16)
    with pytest.raises(ActionError):
        engine.set_speed(3, [1, 2, 4])


def test_unattended_desk_resumes_without_catch_up(engine):
    s = engine.state
    t0 = s.now
    sync(engine, 0.0)
    sync(engine, 10_000.0)
    assert s.now == t0
    sync(engine, 10_030.0)
    assert s.now == t0 + timedelta(minutes=2)


def test_close_then_next_session_opens(engine):
    s = engine.state
    engine.advance("hours", 7)  # 16:00
    s.popups = [p for p in s.popups if not p.blocking]
    sync(engine, 0.0)
    for w in range(15, 15 * 61, 15):
        sync(engine, float(w))
    assert s.now.hour == 17 and s.now.minute == 0
    assert any(p.type == "DAILY_REPORT" for p in s.popups)
    day = s.now.date()
    sync(engine, 15 * 61 + CLOSED + 1)
    assert s.now.date() > day and s.now.hour == 9


def test_risk_warning_does_not_stop_the_live_market_but_review_does(engine):
    s = engine.state
    s.popups.append(Popup(id="P1", type="RISK_WARNING", created=s.now, blocking=True))
    sync(engine, 0.0)
    sync(engine, 30.0)
    assert s.now.minute == 2
    s.popups.append(Popup(id="P2", type="REVIEW", created=s.now, blocking=True))
    sync(engine, 60.0)
    assert s.now.minute == 2


def _force_move(eng: GameEngine, symbol: str, factor: float):
    """Make the next simulated minute jump the price by roughly `factor`."""
    import math
    s = eng.state
    jumps = s.hour.jumps if s.hour is not None else s.flags.setdefault("pending_jumps", {})
    jumps[symbol] = math.log(factor)


def test_limit_buy_rests_then_fills_with_bracket(engine):
    s = engine.state
    px = s.stocks["AKSH"].price
    res = engine.place_order("AKSH", "BUY", "LIMIT", 100, price=round(px * 0.95, 2),
                             target=round(px * 1.05, 2), stoploss=round(px * 0.90, 2))
    assert res["order"]["status"] == "OPEN"
    assert "AKSH" not in s.portfolio.holdings
    _force_move(engine, "AKSH", 0.93)
    engine.time.advance_minutes(2)
    o = next(x for x in s.orders if x.id == res["order"]["id"])
    assert o.status == "EXECUTED" and o.fill_price <= round(px * 0.95, 2)
    assert s.portfolio.holdings["AKSH"].qty == 100
    legs = [x for x in s.orders if x.tag in ("TARGET", "STOPLOSS")]
    assert {x.tag for x in legs} == {"TARGET", "STOPLOSS"} and legs[0].group == legs[1].group
    # The stop-loss fires on a further drop and cancels the target.
    _force_move(engine, "AKSH", 0.94)
    engine.time.advance_minutes(2)
    stop = next(x for x in legs if x.tag == "STOPLOSS")
    tgt = next(x for x in legs if x.tag == "TARGET")
    assert stop.status == "EXECUTED" and tgt.status == "CANCELLED"
    assert "AKSH" not in s.portfolio.holdings


def test_marketable_limit_fills_at_market(engine):
    s = engine.state
    px = s.stocks["TRGM"].price
    res = engine.place_order("TRGM", "BUY", "LIMIT", 50, price=round(px * 1.02, 2))
    assert res["order"]["status"] == "EXECUTED"
    assert res["order"]["fill_price"] <= px * 1.02


def test_order_validation(engine):
    s = engine.state
    px = s.stocks["AKSH"].price
    with pytest.raises(ActionError):
        engine.place_order("AKSH", "SELL", "LIMIT", 10, price=px)  # nothing to sell (no shorting)
    with pytest.raises(ActionError):
        engine.place_order("AKSH", "BUY", "SL-M", 10, trigger=px * 0.99)  # buy stop below market
    with pytest.raises(ActionError):
        engine.place_order("AKSH", "BUY", "LIMIT", 10, price=px * 0.5)  # outside the 20% band
    with pytest.raises(ActionError):
        engine.place_order("AKSH", "BUY", "LIMIT", 10, price=px * 0.95, target=px * 0.9)


def test_day_orders_expire_gtc_orders_survive(engine):
    s = engine.state
    px = s.stocks["AKSH"].price
    day = engine.place_order("AKSH", "BUY", "LIMIT", 10, price=round(px * 0.85, 2))["order"]["id"]
    gtc = engine.place_order("AKSH", "BUY", "LIMIT", 10, price=round(px * 0.85, 2), validity="GTC")["order"]["id"]
    engine.advance("close")
    status = {o.id: o.status for o in s.orders}
    assert status[day] == "EXPIRED" and status[gtc] == "OPEN"
    engine.cancel_order(gtc)
    assert next(o for o in s.orders if o.id == gtc).status == "CANCELLED"


def test_modify_order(engine):
    s = engine.state
    px = s.stocks["AKSH"].price
    oid = engine.place_order("AKSH", "BUY", "LIMIT", 10, price=round(px * 0.9, 2))["order"]["id"]
    engine.modify_order(oid, qty=25, price=round(px * 0.92, 2))
    o = next(o for o in s.orders if o.id == oid)
    assert o.qty == 25 and o.price == round(px * 0.92, 2)


def test_price_alert_triggers(engine):
    s = engine.state
    px = s.stocks["VYMK"].price
    engine.add_alert("VYMK", round(px * 0.97, 2), "support")
    _force_move(engine, "VYMK", 0.95)
    engine.time.advance_minutes(1)
    a = s.alerts[-1]
    assert a.status == "TRIGGERED" and a.op == "BELOW"
    assert any(n.kind == "PRICE_ALERT" for n in s.notifications)


def test_research_runs_in_the_background(engine):
    s = engine.state
    t0 = s.now
    res = engine.research("AKSH", "QUICK")
    assert s.now == t0  # the clock is not fast-forwarded any more
    assert res["job"]["ready_at"] == (t0 + timedelta(hours=1)).isoformat()
    with pytest.raises(ActionError):
        engine.research("AKSH", "DEEP")
    engine.time.advance_minutes(59)
    assert not any(r.symbol == "AKSH" for r in s.research)
    engine.time.advance_minutes(1)
    assert any(r.symbol == "AKSH" for r in s.research) and not s.research_jobs


def test_api_tick_orders_and_intraday_candles(game):
    c, h, state = game
    assert state["live"]["speeds"] == [1, 2, 4]
    assert state["minutes"]["t"], "warm-up leaves recent 1-minute bars for the charts"
    r = c.post("/api/game/tick", headers=h, json={"version": state["version"]}).json()
    assert r.get("unchanged") is True
    sym = state["stocks"][0]["symbol"]
    px = state["stocks"][0]["price"]
    r = c.post("/api/orders", headers=h, json={"symbol": sym, "side": "BUY", "type": "LIMIT", "quantity": 10,
                                                "price": round(px * 0.9, 2)})
    assert r.status_code == 200, r.text
    assert r.json()["state"]["orders"][0]["status"] == "OPEN"
    c.post("/api/game/advance-hours", headers=h, json={"hours": 1})
    for tf, mins in (("1m", 1), ("5m", 5), ("15m", 15)):
        d = c.get(f"/api/market/{sym}?tf={tf}&limit=50", headers=h).json()
        assert len(d["candles"]) >= 4
        ts = [x["t"] for x in d["candles"]]
        assert ts == sorted(ts) and all(int(t[14:16]) % mins == 0 for t in ts)
    d = c.get(f"/api/market/{sym}?tf=1h", headers=h).json()
    assert d["depth"]["bids"][0]["price"] < d["depth"]["asks"][0]["price"]
    r = c.post("/api/game/speed", headers=h, json={"speed": 2})
    assert r.status_code == 200 and r.json()["state"]["live"]["speed"] == 2
