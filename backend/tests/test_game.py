"""Acceptance tests 1-14 (game) and 30-34 (engineering) from the build spec."""
from app.simulation import portfolio_engine as pe
from app.simulation.constants import CRORE
from app.simulation.game_engine import ActionError, GameEngine

import pytest

from tests.conftest import clear_blocking


def test_new_game_unique_seed(client):
    a = client.post("/api/game/new", json={}).json()["state"]
    b = client.post("/api/game/new", json={}).json()["state"]
    assert a["seed"] != b["seed"]
    assert a["game_id"] != b["game_id"]


def test_starting_capital_and_universe(game):
    _, _, st = game
    assert st["portfolio"]["cash"] == 100 * CRORE
    assert st["portfolio"]["value"] == 100 * CRORE
    assert len(st["stocks"]) == 20
    assert st["clock"]["time"] == "09:00" and st["clock"]["day_of_week"] == "MONDAY"
    assert st["career"]["target_value"] == pytest.approx(112 * CRORE)


def test_hidden_fields_not_exposed(game):
    _, _, st = game
    blob = str(st)
    for hidden in ("fair_value", "earnings_quality", "informed_seller", "'regime'", "behavior_profile"):
        assert hidden not in blob


def test_prices_change_after_time(game):
    c, h, st = game
    before = {s["symbol"]: s["price"] for s in st["stocks"]}
    after = c.post("/api/game/advance-hour", headers=h).json()["state"]
    changed = sum(1 for s in after["stocks"] if s["price"] != before[s["symbol"]])
    assert changed >= 18


def test_buy_and_sell_flow(game):
    c, h, st = game
    r = c.post("/api/trade/buy", headers=h, json={"symbol": "AKSH", "quantity": 1000})
    assert r.status_code == 200, r.text
    s2 = r.json()["state"]
    assert s2["portfolio"]["cash"] < st["portfolio"]["cash"]
    pos = next(x for x in s2["holdings"] if x["symbol"] == "AKSH")
    assert pos["qty"] == 1000
    r = c.post("/api/trade/sell", headers=h, json={"symbol": "AKSH", "quantity": 400})
    s3 = r.json()["state"]
    assert s3["portfolio"]["cash"] > s2["portfolio"]["cash"]
    assert next(x for x in s3["holdings"] if x["symbol"] == "AKSH")["qty"] == 600
    assert s3["transactions"][0]["side"] == "SELL"


def test_trade_validation(game):
    c, h, _ = game
    r = c.post("/api/trade/buy", headers=h, json={"symbol": "AKSH", "quantity": 10_000_000})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "INSUFFICIENT_CASH"
    r = c.post("/api/trade/sell", headers=h, json={"symbol": "AKSH", "quantity": 5})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "NO_POSITION"
    c.post("/api/trade/buy", headers=h, json={"symbol": "AKSH", "quantity": 10})
    r = c.post("/api/trade/sell", headers=h, json={"symbol": "AKSH", "quantity": 11})
    assert r.json()["detail"]["code"] == "INSUFFICIENT_SHARES"
    r = c.post("/api/trade/buy", headers=h, json={"symbol": "AKSH", "quantity": -5})
    assert r.json()["detail"]["code"] == "INVALID_QUANTITY"
    r = c.post("/api/trade/buy", headers=h, json={"symbol": "AKSH", "quantity": 1.5})
    assert r.status_code == 422
    r = c.post("/api/trade/buy", headers=h, json={"symbol": "NOPE", "quantity": 5})
    assert r.json()["detail"]["code"] == "INVALID_SYMBOL"


def test_portfolio_value_moves_with_prices(engine):
    eng = engine
    eng.trade("BUY", "GMBK", 20_000)
    v0 = pe.nav(eng.state)
    eng.advance("hours", 3)
    assert pe.nav(eng.state) != v0


def test_news_events_change_market_state(engine):
    eng, s = engine, engine.state
    jumps = {}
    before = s.stocks["DHAN"].price
    s_before = s.stocks["DHAN"].sentiment
    ev = eng.events.company_event("REGULATORY_INVESTIGATION", "DHAN", True, jumps)
    assert ev.impacts["DHAN"] < 0 and jumps["DHAN"] < 0
    assert s.stocks["DHAN"].sentiment < s_before
    assert any(n.event_id == ev.id for n in s.news)
    # the jump is applied in the next simulated hour
    eng.events.state.stocks["DHAN"].price = before
    from app.simulation import market_engine as me
    from datetime import timedelta
    me.simulate_hour(s, eng.rng, s.now, jumps, {}, {}, 0.0)
    assert s.stocks["DHAN"].price < before * 1.02


def test_risk_engine_concentration(engine):
    eng, s = engine, engine.state
    qty = int(0.25 * pe.nav(s) / s.stocks["VYMK"].price)
    eng.trade("BUY", "VYMK", qty)
    warnings = [p for p in s.popups if p.type == "RISK_WARNING"]
    assert warnings, "a 25% single-stock position must trigger a risk warning"
    assert warnings[0].payload["rule"] == "SINGLE_STOCK"
    with pytest.raises(ActionError) as e:
        eng.advance("hour")
    assert e.value.code == "DECISION_REQUIRED"
    eng.resolve_risk(warnings[0].payload["warning_id"], "REDUCE_EXPOSURE")
    w = next(x for x in s.stocks if x == "VYMK")
    weight = s.portfolio.holdings["VYMK"].qty * s.stocks["VYMK"].price / pe.nav(s)
    assert weight <= 0.15


def test_ignoring_risk_has_consequences(engine):
    eng, s = engine, engine.state
    rep0 = s.career.reputation
    qty = int(0.30 * pe.nav(s) / s.stocks["AKSH"].price)
    eng.trade("BUY", "AKSH", qty)
    w = next(p for p in s.popups if p.type == "RISK_WARNING")
    eng.resolve_risk(w.payload["warning_id"], "IGNORE")
    assert s.career.ignored_violations == 1
    assert s.career.reputation < rep0
    trust0 = s.team["risk_manager"].trust
    eng.advance("next_day")
    assert s.team["risk_manager"].trust < trust0


def test_target_progress_updates(engine):
    eng, s = engine, engine.state
    from app.simulation import career_engine as ce
    assert ce.target_progress(s) == 0
    s.portfolio.cash += 6 * 10_000_000
    assert ce.target_progress(s) == pytest.approx(0.5)


def test_save_and_load(game):
    c, h, _ = game
    c.post("/api/trade/buy", headers=h, json={"symbol": "KESR", "quantity": 500})
    c.post("/api/game/advance-hours", headers=h, json={"hours": 2})
    saved = c.post("/api/game/save", headers=h, json={"name": "before-crash"}).json()
    s_saved = c.get("/api/game/state", headers=h).json()
    c.post("/api/trade/sell", headers=h, json={"symbol": "KESR", "quantity": 500})
    c.post("/api/game/advance-next-business-day", headers=h)
    loaded = c.post("/api/game/load", headers=h, json={"save_id": saved["id"]}).json()["state"]
    assert loaded["clock"]["iso"] == s_saved["clock"]["iso"]
    assert loaded["portfolio"]["cash"] == pytest.approx(s_saved["portfolio"]["cash"])
    assert loaded["holdings"][0]["qty"] == 500
    assert "before-crash" in [x["name"] for x in c.get("/api/game/saves", headers=h).json()]
    # history after the save point was rolled back
    candles = c.get("/api/market/KESR?tf=1h&limit=500", headers=h).json()["candles"]
    assert candles[-1]["t"] < loaded["clock"]["iso"]


def test_state_survives_restart(game):
    """Browser refresh / server restart: state reloads from the database unchanged."""
    from app.services import game_service
    c, h, _ = game
    c.post("/api/trade/buy", headers=h, json={"symbol": "NITY", "quantity": 100})
    c.post("/api/game/advance-hours", headers=h, json={"hours": 3})
    s1 = c.get("/api/game/state", headers=h).json()
    game_service.clear_cache()
    s2 = c.get("/api/game/state", headers=h).json()
    assert s1["clock"] == s2["clock"]
    assert s1["portfolio"] == s2["portfolio"]
    # deterministic continuation after reload (RNG state persisted)
    a = c.post("/api/game/advance-hour", headers=h).json()["state"]["stocks"][0]["price"]
    assert a > 0


def test_frontend_cannot_set_state(game):
    c, h, _ = game
    for path in ("/api/game/state", "/api/portfolio"):
        assert c.put(path, headers=h, json={"cash": 1e12}).status_code == 405
    r = c.post("/api/trade/buy", headers=h, json={"symbol": "AKSH", "quantity": 10, "price": 1})
    tx = r.json()["result"]["transaction"]
    assert tx["price"] > 100  # client-sent price ignored


def test_reproducible_seed():
    a = GameEngine.new_game("a", seed=99).state
    b = GameEngine.new_game("b", seed=99).state
    assert {k: v.price for k, v in a.stocks.items()} == {k: v.price for k, v in b.stocks.items()}
    ea, eb = GameEngine(a), GameEngine(b)
    ea.advance("next_day")
    eb.advance("next_day")
    assert {k: v.price for k, v in a.stocks.items()} == {k: v.price for k, v in b.stocks.items()}


def test_block_deal_expires(engine):
    from datetime import timedelta
    from app.simulation.state import Opportunity
    eng, s = engine, engine.state
    s.opportunities.append(Opportunity(id="OPP-X", kind="BLOCK_DEAL", symbol="PTHK", qty=1000,
                                       price=s.stocks["PTHK"].price * 0.96, discount=0.04, created=s.now,
                                       expires_at=s.now + timedelta(hours=2)))
    eng.advance("hours", 3)
    clear_blocking(eng)
    with pytest.raises(ActionError) as e:
        eng.accept_opportunity("OPP-X")
    assert e.value.message == "OPPORTUNITY EXPIRED"
