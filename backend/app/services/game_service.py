"""
GameService — central orchestrator for all game actions.
Coordinates TimeEngine, MarketEngine, EventEngine, NewsEngine,
PortfolioEngine, RiskEngine, CareerEngine, and GameDirector.
All mutations go through this service. State is authoritative in PostgreSQL.
"""
import uuid
import math
from datetime import date, datetime
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models.db_models import (
    Game, Stock, Holding, Transaction, StockTick,
    MarketTick, NewsItem, GameEvent, Telemetry
)
from app.simulation.constants import (
    STOCK_UNIVERSE, STARTING_CAPITAL, QUARTERLY_TARGET,
    MAX_DRAWDOWN_LIMIT, TRANSACTION_FEE_RATE,
    WORKING_HOURS, CAREER_DAYS, CRORE, LAKH, INDEX_DEFAULTS,
    CAREER_LEVELS,
)
from app.simulation.time_engine import TimeEngine, TimeState
from app.simulation.market_engine import MarketEngine
from app.simulation.event_engine import EventEngine
from app.simulation.news_engine import NewsEngine
from app.simulation.portfolio_engine import PortfolioEngine
from app.simulation.risk_engine import RiskEngine
from app.simulation.career_engine import CareerEngine
from app.simulation.game_director import GameDirector
from app.schemas.game_schemas import (
    GameStateResponse, TimeInfo, FinancialsInfo, CareerInfo,
    MarketInfo, IndexInfo, StockInfo, HoldingInfo, RiskInfo,
    RiskWarningInfo, NewsItemInfo, NotificationInfo, TradeResult,
    StockCandlesResponse, CandleData, PerformanceData,
    TransactionInfo, QuarterlyReviewResponse,
)


def _get_rng(game: Game) -> np.random.Generator:
    """Deterministic RNG seeded by game seed + career day + hour."""
    tick = (game.career_day * 100) + game.game_hour
    return np.random.default_rng(game.seed + tick)


def _stocks_map(db: Session, game_id) -> dict:
    """Load all stocks for game as a dict symbol → Stock ORM object."""
    stocks = db.query(Stock).filter(Stock.game_id == game_id).all()
    return {s.symbol: s for s in stocks}


def _holdings_list(db: Session, game_id) -> list:
    return db.query(Holding).filter(Holding.game_id == game_id, Holding.quantity > 0).all()


def _realized_pnl_total(db: Session, game_id) -> float:
    txns = db.query(Transaction).filter(
        Transaction.game_id == game_id, Transaction.action == "SELL"
    ).all()
    return sum(t.realized_pnl or 0.0 for t in txns)


def _build_state_response(game: Game, db: Session) -> GameStateResponse:
    """Build the full API response from current game state."""
    stocks_map = _stocks_map(db, game.id)
    holdings_db = _holdings_list(db, game.id)
    realized_pnl = _realized_pnl_total(db, game.id)

    # Portfolio metrics
    port = PortfolioEngine.compute(
        cash=game.cash,
        holdings_db=holdings_db,
        stocks_map=stocks_map,
        starting_capital=game.starting_capital,
        quarterly_target=game.quarterly_target,
        peak_portfolio_value=game.peak_portfolio_value,
        daily_open_portfolio=game.daily_open_portfolio,
        realized_pnl=realized_pnl,
    )

    # Risk assessment
    risk = RiskEngine.assess(
        total_value=port.total_value,
        cash=game.cash,
        holdings_detail=port.holdings,
        sector_exposure=port.sector_exposure,
        max_drawdown=port.max_drawdown,
        portfolio_volatility=port.portfolio_volatility,
        market_regime=game.market_regime,
    )

    # Time info
    game_date_obj = game.game_date
    days_map = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = days_map[game_date_obj.weekday()]
    hours_left = max(0, max(WORKING_HOURS) + 1 - game.game_hour)

    time_info = TimeInfo(
        game_date=game_date_obj.isoformat(),
        game_hour=game.game_hour,
        day_of_week=dow,
        career_day=game.career_day,
        quarter=game.quarter,
        career_year=game.career_year,
        market_status=game.market_status,
        working_hours_left=hours_left,
    )

    # Financials
    fin = FinancialsInfo(
        cash=port.cash,
        cash_cr=round(port.cash / CRORE, 4),
        invested_value=port.invested_value,
        invested_value_cr=round(port.invested_value / CRORE, 4),
        total_value=port.total_value,
        total_value_cr=round(port.total_value / CRORE, 4),
        starting_capital=port.starting_capital,
        starting_capital_cr=round(port.starting_capital / CRORE, 2),
        quarterly_target=port.quarterly_target,
        quarterly_target_cr=round(port.quarterly_target / CRORE, 2),
        total_pnl=port.total_pnl,
        total_pnl_cr=round(port.total_pnl / CRORE, 4),
        total_return_pct=round(port.total_return_pct, 4),
        realized_pnl=port.realized_pnl,
        unrealized_pnl=port.unrealized_pnl,
        daily_pnl=port.daily_pnl,
        daily_pnl_cr=round(port.daily_pnl / CRORE, 4),
        max_drawdown=round(port.max_drawdown * 100, 4),
        target_progress=round(port.target_progress * 100, 2),
        to_target=port.to_target,
        to_target_cr=round(port.to_target / CRORE, 4),
        target_met=port.target_met,
        portfolio_volatility=round(port.portfolio_volatility * 100, 2),
    )

    # Career
    lvl_data = CAREER_LEVELS.get(game.career_level, CAREER_LEVELS[1])
    career = CareerInfo(
        level=game.career_level,
        role=CareerEngine.get_role_title(game.career_level),
        xp=game.xp,
        xp_to_next_level=lvl_data.get("xp_to_next", 9999),
        reputation=round(game.reputation, 1),
        leave_balance=game.leave_balance,
        leave_used=game.leave_used,
        on_leave=game.on_leave,
    )

    # Indices
    # Build prev values from last market tick if available
    prev_nifty = game.nifty_value  # fallback; real prev computed below
    last_tick = (
        db.query(MarketTick)
        .filter(MarketTick.game_id == game.id)
        .order_by(MarketTick.tick_index.desc())
        .first()
    )
    if last_tick:
        prev_nifty = last_tick.nifty

    indices = [
        IndexInfo(symbol="NIFTY50", name="NIFTY 50", value=game.nifty_value,
                  prev_value=prev_nifty,
                  change_pct=round((game.nifty_value / prev_nifty - 1) * 100, 3) if prev_nifty else 0),
        IndexInfo(symbol="SENSEX", name="SENSEX", value=game.sensex_value,
                  prev_value=game.sensex_value, change_pct=0),
        IndexInfo(symbol="BANKNIFTY", name="BANK NIFTY", value=game.bank_nifty_value,
                  prev_value=game.bank_nifty_value, change_pct=0),
        IndexInfo(symbol="INDIAVIX", name="INDIA VIX", value=game.india_vix_value,
                  prev_value=game.india_vix_value, change_pct=0),
        IndexInfo(symbol="USDINR", name="USD/INR", value=game.usdinr_value,
                  prev_value=game.usdinr_value, change_pct=0),
        IndexInfo(symbol="GOLD", name="GOLD (₹/10g)", value=game.gold_value,
                  prev_value=game.gold_value, change_pct=0),
        IndexInfo(symbol="NASDAQ", name="NASDAQ", value=game.nasdaq_value,
                  prev_value=game.nasdaq_value, change_pct=0),
        IndexInfo(symbol="SP500", name="S&P 500", value=game.sp500_value,
                  prev_value=game.sp500_value, change_pct=0),
    ]

    # Stocks
    stocks_list = [
        StockInfo(
            symbol=s.symbol, name=s.name, sector=s.sector,
            current_price=s.current_price, previous_price=s.previous_price,
            daily_open=s.daily_open, daily_high=s.daily_high, daily_low=s.daily_low,
            daily_return=round((s.current_price / s.daily_open - 1) * 100, 4) if s.daily_open else 0.0,
            volume=s.volume, volatility=s.volatility, beta=s.beta,
            sentiment=s.sentiment, momentum=s.momentum,
            growth=s.growth, profitability=s.profitability,
            debt=s.debt, valuation=s.valuation,
        )
        for s in stocks_map.values()
    ]

    # Holdings
    holdings_resp = [
        HoldingInfo(
            symbol=h["symbol"], name=h["name"], sector=h["sector"],
            quantity=h["quantity"], avg_buy_price=h["avg_buy_price"],
            current_price=h["current_price"],
            current_value=h["current_value"],
            current_value_cr=round(h["current_value"] / CRORE, 4),
            cost_basis=h["cost_basis"],
            unrealized_pnl=h["unrealized_pnl"],
            unrealized_pnl_pct=round(h["unrealized_pnl_pct"], 4),
            daily_return=round(h.get("daily_return", 0.0) * 100, 4),
        )
        for h in port.holdings
    ]

    # Risk
    risk_resp = RiskInfo(
        overall_level=risk.overall_level,
        risk_score=risk.risk_score,
        warnings=[RiskWarningInfo(**w.__dict__) for w in risk.warnings],
        drawdown_pct=risk.drawdown_pct,
        cash_ratio=risk.cash_ratio,
        largest_position_pct=risk.largest_position_pct,
        sector_concentration=risk.sector_concentration,
        portfolio_volatility=risk.portfolio_volatility,
    )

    # Recent news (last 15)
    news_db = (
        db.query(NewsItem)
        .filter(NewsItem.game_id == game.id)
        .order_by(NewsItem.created_at.desc())
        .limit(15)
        .all()
    )
    news_resp = [
        NewsItemInfo(
            id=str(n.id), category=n.category, priority=n.priority,
            headline=n.headline, body=n.body,
            affected_symbol=n.affected_symbol, affected_sector=n.affected_sector,
            market_impact=n.market_impact, career_day=n.career_day,
            game_hour=n.game_hour, is_read=n.is_read,
        )
        for n in news_db
    ]

    # Notifications
    notifs = [NotificationInfo(**n) for n in (game.pending_notifications or [])]

    # Trade count today
    trade_count = db.query(Transaction).filter(
        Transaction.game_id == game.id,
        Transaction.career_day == game.career_day,
    ).count()

    return GameStateResponse(
        game_id=str(game.id),
        player_name=game.player_name,
        status=game.status,
        time=time_info,
        financials=fin,
        career=career,
        market=MarketInfo(regime=game.market_regime, indices=indices, stocks=stocks_list),
        holdings=holdings_resp,
        risk=risk_resp,
        recent_news=news_resp,
        notifications=notifs,
        trade_count_today=trade_count,
    )


def create_new_game(player_name: str, db: Session) -> str:
    """Create a new game session, seed stocks, return game_id."""
    seed = int(np.random.default_rng().integers(0, 2**32))

    # Initial game date: next Monday
    from datetime import timedelta
    today = date.today()
    days_to_monday = (7 - today.weekday()) % 7
    if days_to_monday == 0:
        days_to_monday = 0
    start_date = today + timedelta(days=days_to_monday)
    while start_date.weekday() != 0:
        start_date += timedelta(days=1)

    game = Game(
        id=uuid.uuid4(),
        player_name=player_name,
        seed=seed,
        status="ACTIVE",
        game_date=start_date,
        game_hour=9,
        career_day=1,
        quarter=1,
        career_year=1,
        market_status="OPEN",
        cash=STARTING_CAPITAL,
        starting_capital=STARTING_CAPITAL,
        quarterly_target=QUARTERLY_TARGET,
        max_drawdown_limit=MAX_DRAWDOWN_LIMIT,
        peak_portfolio_value=STARTING_CAPITAL,
        daily_open_portfolio=STARTING_CAPITAL,
        career_level=1,
        xp=0,
        reputation=50.0,
        leave_balance=60,
        leave_used=0,
        on_leave=False,
        market_regime="STABLE",
        regime_days_remaining=15,
        nifty_value=INDEX_DEFAULTS["nifty"],
        sensex_value=INDEX_DEFAULTS["sensex"],
        bank_nifty_value=INDEX_DEFAULTS["bank_nifty"],
        india_vix_value=INDEX_DEFAULTS["india_vix"],
        usdinr_value=INDEX_DEFAULTS["usdinr"],
        gold_value=INDEX_DEFAULTS["gold"],
        nasdaq_value=INDEX_DEFAULTS["nasdaq"],
        sp500_value=INDEX_DEFAULTS["sp500"],
        risk_warnings=[],
        active_risk_level="LOW",
        daily_pnl=0.0,
        max_drawdown=0.0,
        pending_notifications=[],
    )
    db.add(game)

    # Seed stocks with slight price variation from seed
    rng = np.random.default_rng(seed)
    for stock_def in STOCK_UNIVERSE:
        variation = rng.uniform(0.95, 1.05)
        base_price = round(stock_def["base_price"] * variation, 2)
        stock = Stock(
            game_id=game.id,
            symbol=stock_def["symbol"],
            name=stock_def["name"],
            sector=stock_def["sector"],
            base_price=base_price,
            current_price=base_price,
            previous_price=base_price,
            daily_open=base_price,
            daily_high=base_price,
            daily_low=base_price,
            volume=0,
            volatility=stock_def["volatility"],
            beta=stock_def["beta"],
            growth=stock_def["growth"],
            profitability=stock_def["profitability"],
            debt=stock_def["debt"],
            valuation=stock_def["valuation"],
            sentiment=rng.uniform(0.45, 0.55),
            momentum=0.0,
            market_sensitivity=stock_def["market_sensitivity"],
            event_sensitivity=stock_def["event_sensitivity"],
            institutional_pressure=0.0,
        )
        db.add(stock)

    db.commit()
    db.refresh(game)

    # Store initial market tick
    _store_market_tick(game, db)

    return str(game.id)


def advance_game_time(game_id: str, hours: int, db: Session) -> GameStateResponse:
    """Advance game by N hours, processing all simulation steps."""
    game = _get_game(game_id, db)
    if game.status != "ACTIVE":
        raise ValueError(f"Game is {game.status} — cannot advance time.")

    rng = _get_rng(game)

    for h in range(hours):
        _advance_one_hour(game, db, rng)
        # Re-seed rng each hour for determinism
        rng = _get_rng(game)

    db.commit()
    return _build_state_response(game, db)


def _advance_one_hour(game: Game, db: Session, rng: np.random.Generator):
    """Process one game hour: time → market → events → news → portfolio → risk → career."""
    prev_career_day = game.career_day
    prev_hour = game.game_hour

    # ── 1. Advance time ──
    time_state = TimeState(
        game_date=game.game_date,
        game_hour=game.game_hour,
        career_day=game.career_day,
        quarter=game.quarter,
        career_year=game.career_year,
        market_status=game.market_status,
        on_leave=game.on_leave,
        leave_balance=game.leave_balance,
        leave_used=game.leave_used,
    )
    result = TimeEngine.advance_one_hour(time_state)
    new_state = result.new_state

    # Update game time
    game.game_date = new_state.game_date
    game.game_hour = new_state.game_hour
    game.career_day = new_state.career_day
    game.quarter = new_state.quarter
    game.career_year = new_state.career_year
    game.market_status = new_state.market_status

    # If crossed into a new day, reset daily OHLC
    if result.new_career_day:
        game.daily_open_portfolio = game.cash + _compute_invested_value(game, db)
        _reset_daily_ohlc(game, db)

    # ── 2. Simulate market (only during trading hours) ──
    if prev_hour in WORKING_HOURS:
        stocks = db.query(Stock).filter(Stock.game_id == game.id).all()

        # Get active events
        active_events = db.query(GameEvent).filter(
            GameEvent.game_id == game.id,
            GameEvent.is_active == True,
            GameEvent.trigger_day <= game.career_day,
        ).all()

        event_shocks = EventEngine.get_event_shocks(active_events)

        market_result = MarketEngine.simulate_tick(
            stocks=stocks,
            game=game,
            rng=rng,
            event_shocks=event_shocks,
        )

        # Update stock prices in DB
        for snap in market_result.updated_stocks:
            stock = next((s for s in stocks if s.symbol == snap.symbol), None)
            if stock:
                stock.previous_price = stock.current_price
                stock.current_price = snap.current_price
                stock.daily_high = snap.daily_high
                stock.daily_low = snap.daily_low
                stock.volume = snap.volume
                stock.sentiment = snap.sentiment
                stock.momentum = snap.momentum
                stock.institutional_pressure = snap.institutional_pressure

        # Update indices
        game.nifty_value = market_result.nifty
        game.sensex_value = market_result.sensex
        game.bank_nifty_value = market_result.bank_nifty
        game.india_vix_value = market_result.india_vix
        game.usdinr_value = market_result.usdinr
        game.gold_value = market_result.gold
        game.nasdaq_value = market_result.nasdaq
        game.sp500_value = market_result.sp500
        if market_result.regime_changed and market_result.new_regime:
            game.market_regime = market_result.new_regime
            # Add notification
            notifs = list(game.pending_notifications or [])
            notifs.append({
                "id": str(uuid.uuid4()),
                "level": "WARNING" if market_result.new_regime in ("BEAR", "CRISIS") else "INFO",
                "message": f"Market regime shifted to {market_result.new_regime}.",
                "category": "MARKET",
            })
            game.pending_notifications = notifs[-20:]  # keep last 20

        # Store stock ticks
        tick_idx = TimeEngine.tick_index(prev_career_day, prev_hour)
        _store_stock_ticks(game, stocks, market_result.updated_stocks, tick_idx, prev_career_day, prev_hour, db)
        _store_market_tick_ex(game, tick_idx, prev_career_day, prev_hour, db)

        # ── 3. Generate events ──
        new_events = EventEngine.generate_daily_events(
            career_day=game.career_day,
            game_hour=game.game_hour,
            stocks=stocks,
            game=game,
            rng=rng,
        )
        for evt in new_events:
            db_event = GameEvent(
                id=uuid.uuid4(),
                game_id=game.id,
                event_type=evt.event_type,
                severity=evt.severity,
                affected_symbol=evt.affected_symbol,
                affected_sector=evt.affected_sector,
                trigger_day=evt.trigger_day,
                trigger_hour=evt.trigger_hour,
                duration_hours=evt.duration_hours,
                price_impact=evt.price_impact,
                narrative=evt.narrative,
                is_processed=False,
                is_active=True,
                follow_up_event_type=evt.follow_up_event_type,
                follow_up_day=evt.follow_up_day,
            )
            db.add(db_event)

            # Generate news for this event
            news_result = NewsEngine.news_from_event(evt)
            news_item = NewsItem(
                id=uuid.uuid4(),
                game_id=game.id,
                career_day=game.career_day,
                game_hour=game.game_hour,
                category=news_result.category,
                priority=news_result.priority,
                headline=news_result.headline,
                body=news_result.body,
                affected_symbol=news_result.affected_symbol,
                affected_sector=news_result.affected_sector,
                market_impact=news_result.market_impact,
            )
            db.add(news_item)

            # Push notification for important events
            if evt.severity in ("HIGH", "CRITICAL"):
                notifs = list(game.pending_notifications or [])
                notifs.append({
                    "id": str(uuid.uuid4()),
                    "level": "CRITICAL" if evt.severity == "CRITICAL" else "WARNING",
                    "message": evt.narrative[:120],
                    "category": "EVENT",
                })
                game.pending_notifications = notifs[-20:]

        # Deactivate expired events
        for evt in active_events:
            if (game.career_day - evt.trigger_day) * 8 + (game.game_hour - evt.trigger_hour) >= evt.duration_hours:
                evt.is_active = False

    # ── 4. Career update ──
    stocks_map = _stocks_map_raw(db, game.id)
    holdings_db = _holdings_list(db, game.id)
    port = PortfolioEngine.compute(
        cash=game.cash, holdings_db=holdings_db, stocks_map=stocks_map,
        starting_capital=game.starting_capital, quarterly_target=game.quarterly_target,
        peak_portfolio_value=game.peak_portfolio_value,
        daily_open_portfolio=game.daily_open_portfolio,
        realized_pnl=_realized_pnl_total(db, game.id),
    )
    risk = RiskEngine.assess(
        total_value=port.total_value, cash=game.cash,
        holdings_detail=port.holdings, sector_exposure=port.sector_exposure,
        max_drawdown=port.max_drawdown, portfolio_volatility=port.portfolio_volatility,
        market_regime=game.market_regime,
    )

    career_upd = CareerEngine.update_per_tick(
        career_level=game.career_level, xp=game.xp, reputation=game.reputation,
        total_return_pct=port.total_return_pct, risk_assessment=risk,
        target_progress=port.target_progress,
    )
    game.xp = min(game.xp + career_upd.xp_gained, 99999)
    game.reputation = max(0.0, min(100.0, game.reputation + career_upd.reputation_change))
    if career_upd.level_up and career_upd.new_level:
        game.career_level = career_upd.new_level
    if career_upd.notification:
        notifs = list(game.pending_notifications or [])
        notifs.append({
            "id": str(uuid.uuid4()),
            "level": "INFO",
            "message": career_upd.notification,
            "category": "CAREER",
        })
        game.pending_notifications = notifs[-20:]

    # Update peak portfolio
    game.peak_portfolio_value = max(game.peak_portfolio_value, port.total_value)
    game.max_drawdown = port.max_drawdown

    # CEO message occasionally
    if game.game_hour == 14:  # 2 PM
        ceo_news = NewsEngine.generate_ceo_message(
            portfolio_return=port.total_return_pct,
            career_day=game.career_day,
            target_progress=port.target_progress,
            rng=rng,
        )
        if ceo_news:
            db.add(NewsItem(
                id=uuid.uuid4(),
                game_id=game.id,
                career_day=game.career_day,
                game_hour=game.game_hour,
                category="CEO",
                priority="HIGH",
                headline=ceo_news.headline,
                body=ceo_news.body,
                affected_symbol=None,
                affected_sector=None,
                market_impact=0.0,
            ))

    # ── 5. Check quarterly review ──
    if game.career_day > CAREER_DAYS and game.status == "ACTIVE":
        _trigger_quarterly_review(game, port, db)

    game.updated_at = datetime.utcnow()


def execute_buy(game_id: str, symbol: str, quantity: int, db: Session) -> TradeResult:
    game = _get_game(game_id, db)
    if game.status != "ACTIVE":
        return TradeResult(success=False, message="Game is not active.", symbol=symbol,
                           action="BUY", quantity=quantity, price=0, total_value=0, fee=0,
                           cash_after=game.cash, cash_after_cr=game.cash/CRORE)

    stocks_map = _stocks_map(db, game.id)
    stock = stocks_map.get(symbol)
    if not stock:
        return TradeResult(success=False, message=f"Unknown symbol: {symbol}", symbol=symbol,
                           action="BUY", quantity=quantity, price=0, total_value=0, fee=0,
                           cash_after=game.cash, cash_after_cr=game.cash/CRORE)

    price = stock.current_price
    ok, err = PortfolioEngine.validate_buy(game.cash, symbol, quantity, price, stocks_map)
    if not ok:
        return TradeResult(success=False, message=err, symbol=symbol, action="BUY",
                           quantity=quantity, price=price, total_value=0, fee=0,
                           cash_after=game.cash, cash_after_cr=game.cash/CRORE)

    total = quantity * price
    fee = round(total * TRANSACTION_FEE_RATE, 2)
    total_with_fee = total + fee
    cash_before = game.cash
    game.cash -= total_with_fee

    # Update or create holding
    holding = db.query(Holding).filter(
        Holding.game_id == game.id, Holding.symbol == symbol
    ).first()
    if holding:
        # Weighted average cost
        old_total_cost = holding.quantity * holding.avg_buy_price
        new_total_cost = old_total_cost + total
        holding.quantity += quantity
        holding.avg_buy_price = new_total_cost / holding.quantity
        holding.total_cost = new_total_cost + fee
    else:
        holding = Holding(
            game_id=game.id, symbol=symbol, quantity=quantity,
            avg_buy_price=price, total_cost=total + fee,
        )
        db.add(holding)

    # Record transaction
    txn = Transaction(
        id=uuid.uuid4(), game_id=game.id,
        career_day=game.career_day, game_date=game.game_date,
        game_hour=game.game_hour, symbol=symbol, name=stock.name,
        action="BUY", quantity=quantity, price=price,
        total_value=total, fee=fee,
        cash_before=cash_before, cash_after=game.cash,
        realized_pnl=None,
    )
    db.add(txn)

    # XP for trading
    game.xp += 10
    game.updated_at = datetime.utcnow()
    db.commit()

    return TradeResult(
        success=True,
        message=f"Bought {quantity:,} shares of {stock.name} at ₹{price:,.2f}",
        symbol=symbol, action="BUY", quantity=quantity, price=price,
        total_value=total, fee=fee,
        cash_after=game.cash, cash_after_cr=game.cash/CRORE,
    )


def execute_sell(game_id: str, symbol: str, quantity: int, db: Session) -> TradeResult:
    game = _get_game(game_id, db)
    if game.status != "ACTIVE":
        return TradeResult(success=False, message="Game is not active.", symbol=symbol,
                           action="SELL", quantity=quantity, price=0, total_value=0, fee=0,
                           cash_after=game.cash, cash_after_cr=game.cash/CRORE)

    stocks_map = _stocks_map(db, game.id)
    stock = stocks_map.get(symbol)
    if not stock:
        return TradeResult(success=False, message=f"Unknown symbol: {symbol}", symbol=symbol,
                           action="SELL", quantity=quantity, price=0, total_value=0, fee=0,
                           cash_after=game.cash, cash_after_cr=game.cash/CRORE)

    holdings_db = _holdings_list(db, game.id)
    ok, err, current_qty = PortfolioEngine.validate_sell(holdings_db, symbol, quantity)
    if not ok:
        return TradeResult(success=False, message=err, symbol=symbol, action="SELL",
                           quantity=quantity, price=stock.current_price, total_value=0,
                           fee=0, cash_after=game.cash, cash_after_cr=game.cash/CRORE)

    price = stock.current_price
    total = quantity * price
    fee = round(total * TRANSACTION_FEE_RATE, 2)
    proceeds = total - fee
    cash_before = game.cash
    game.cash += proceeds

    # Update holding
    holding = db.query(Holding).filter(
        Holding.game_id == game.id, Holding.symbol == symbol
    ).first()
    avg_price = holding.avg_buy_price
    realized_pnl = (price - avg_price) * quantity - fee
    holding.quantity -= quantity
    if holding.quantity == 0:
        holding.avg_buy_price = 0.0
        holding.total_cost = 0.0
    else:
        holding.total_cost -= avg_price * quantity

    txn = Transaction(
        id=uuid.uuid4(), game_id=game.id,
        career_day=game.career_day, game_date=game.game_date,
        game_hour=game.game_hour, symbol=symbol, name=stock.name,
        action="SELL", quantity=quantity, price=price,
        total_value=total, fee=fee,
        cash_before=cash_before, cash_after=game.cash,
        realized_pnl=realized_pnl,
    )
    db.add(txn)

    game.xp += 10
    game.updated_at = datetime.utcnow()
    db.commit()

    return TradeResult(
        success=True,
        message=f"Sold {quantity:,} shares of {stock.name} at ₹{price:,.2f}",
        symbol=symbol, action="SELL", quantity=quantity, price=price,
        total_value=total, fee=fee,
        cash_after=game.cash, cash_after_cr=game.cash/CRORE,
        realized_pnl=realized_pnl,
    )


def get_stock_candles(game_id: str, symbol: str, days: int, db: Session) -> StockCandlesResponse:
    game = _get_game(game_id, db)
    stock = db.query(Stock).filter(Stock.game_id == game.id, Stock.symbol == symbol).first()
    if not stock:
        raise ValueError(f"Stock {symbol} not found.")

    ticks = (
        db.query(StockTick)
        .filter(StockTick.game_id == game.id, StockTick.symbol == symbol)
        .order_by(StockTick.tick_index)
        .all()
    )

    # Aggregate to daily OHLCV
    daily: dict[int, dict] = {}
    for t in ticks:
        d = t.career_day
        if d not in daily:
            daily[d] = {"open": t.open_price, "high": t.high_price,
                         "low": t.low_price, "close": t.close_price, "volume": 0}
        else:
            daily[d]["high"] = max(daily[d]["high"], t.high_price)
            daily[d]["low"] = min(daily[d]["low"], t.low_price)
            daily[d]["close"] = t.close_price
        daily[d]["volume"] += t.volume

    candles = []
    for day_num in sorted(daily.keys())[-days:]:
        d = daily[day_num]
        # Use career_day as a pseudo-date offset from game start date
        from datetime import timedelta
        day_date = (game.game_date - timedelta(days=game.career_day - day_num)).isoformat()
        candles.append(CandleData(
            time=day_date,
            open=d["open"], high=d["high"],
            low=d["low"], close=d["close"],
            volume=d["volume"],
        ))

    # If no ticks yet, return current price as a single candle
    if not candles:
        candles.append(CandleData(
            time=game.game_date.isoformat(),
            open=stock.daily_open, high=stock.daily_high,
            low=stock.daily_low, close=stock.current_price,
            volume=stock.volume,
        ))

    return StockCandlesResponse(symbol=symbol, name=stock.name, candles=candles)


def get_performance(game_id: str, db: Session) -> PerformanceData:
    game = _get_game(game_id, db)
    transactions = db.query(Transaction).filter(
        Transaction.game_id == game.id
    ).order_by(Transaction.created_at).all()

    sell_txns = [t for t in transactions if t.action == "SELL"]
    wins = [t for t in sell_txns if (t.realized_pnl or 0) > 0]
    win_rate = len(wins) / len(sell_txns) * 100 if sell_txns else 0.0
    pnls = [t.realized_pnl or 0 for t in sell_txns]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
    best_pnl = max(pnls) if pnls else 0.0
    worst_pnl = min(pnls) if pnls else 0.0

    # Sector attribution from holdings
    stocks_map = _stocks_map_raw(db, game.id)
    holdings_db = _holdings_list(db, game.id)
    port = PortfolioEngine.compute(
        cash=game.cash, holdings_db=holdings_db, stocks_map=stocks_map,
        starting_capital=game.starting_capital, quarterly_target=game.quarterly_target,
        peak_portfolio_value=game.peak_portfolio_value,
        daily_open_portfolio=game.daily_open_portfolio,
    )

    # Daily portfolio values from telemetry
    tel = db.query(Telemetry).filter(Telemetry.game_id == game.id).order_by(Telemetry.tick_index).all()
    daily_values = []
    seen_days = set()
    for t in tel:
        if t.career_day not in seen_days:
            daily_values.append({"day": t.career_day, "value": t.portfolio_value})
            seen_days.add(t.career_day)

    # NIFTY benchmark: estimate from market ticks
    first_nifty = INDEX_DEFAULTS["nifty"]
    nifty_ticks = db.query(MarketTick).filter(MarketTick.game_id == game.id).order_by(MarketTick.tick_index).all()
    if nifty_ticks:
        benchmark_return = (nifty_ticks[-1].nifty / first_nifty - 1) * 100
    else:
        benchmark_return = 0.0

    txn_resp = [
        TransactionInfo(
            id=str(t.id), career_day=t.career_day,
            game_date=t.game_date.isoformat(), game_hour=t.game_hour,
            symbol=t.symbol, name=t.name, action=t.action,
            quantity=t.quantity, price=t.price,
            total_value=t.total_value, fee=t.fee,
            realized_pnl=t.realized_pnl,
            created_at=t.created_at.isoformat(),
        )
        for t in transactions
    ]

    return PerformanceData(
        total_return_pct=round(port.total_return_pct, 4),
        benchmark_return_pct=round(benchmark_return, 4),
        max_drawdown=round(port.max_drawdown * 100, 4),
        portfolio_volatility=round(port.portfolio_volatility * 100, 4),
        win_rate=round(win_rate, 2),
        avg_trade_pnl=round(avg_pnl, 2),
        best_trade_pnl=round(best_pnl, 2),
        worst_trade_pnl=round(worst_pnl, 2),
        trade_count=len(transactions),
        sector_attribution=port.sector_exposure,
        transactions=txn_resp,
        daily_portfolio_values=daily_values,
    )


def do_quarterly_review(game_id: str, db: Session) -> QuarterlyReviewResponse:
    game = _get_game(game_id, db)
    stocks_map = _stocks_map_raw(db, game.id)
    holdings_db = _holdings_list(db, game.id)
    port = PortfolioEngine.compute(
        cash=game.cash, holdings_db=holdings_db, stocks_map=stocks_map,
        starting_capital=game.starting_capital, quarterly_target=game.quarterly_target,
        peak_portfolio_value=game.peak_portfolio_value,
        daily_open_portfolio=game.daily_open_portfolio,
    )
    review = CareerEngine.quarterly_review(
        career_level=game.career_level,
        reputation=game.reputation,
        xp=game.xp,
        total_return_pct=port.total_return_pct,
        quarterly_target_return=12.0,
        max_drawdown=port.max_drawdown * 100,
        max_drawdown_limit=game.max_drawdown_limit,
        risk_violations_count=0,
    )
    game.status = "COMPLETED"
    game.xp += review.xp_awarded
    game.reputation = max(0.0, min(100.0, game.reputation + review.reputation_change))
    game.updated_at = datetime.utcnow()
    db.commit()
    return QuarterlyReviewResponse(
        outcome=review.outcome,
        final_return=review.final_return,
        target_return=review.target_return,
        max_drawdown=review.max_drawdown,
        reputation=game.reputation,
        xp=game.xp,
        summary=review.summary,
        ceo_message=review.ceo_message,
        xp_awarded=review.xp_awarded,
        reputation_change=review.reputation_change,
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_game(game_id: str, db: Session) -> Game:
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise ValueError(f"Game {game_id} not found.")
    return game


def _stocks_map_raw(db: Session, game_id) -> dict:
    stocks = db.query(Stock).filter(Stock.game_id == game_id).all()
    return {s.symbol: s for s in stocks}


def _compute_invested_value(game: Game, db: Session) -> float:
    stocks_map = _stocks_map_raw(db, game.id)
    holdings = _holdings_list(db, game.id)
    total = 0.0
    for h in holdings:
        s = stocks_map.get(h.symbol)
        if s:
            total += h.quantity * s.current_price
    return total


def _reset_daily_ohlc(game: Game, db: Session):
    stocks = db.query(Stock).filter(Stock.game_id == game.id).all()
    for s in stocks:
        s.daily_open = s.current_price
        s.daily_high = s.current_price
        s.daily_low = s.current_price
        s.volume = 0


def _store_stock_ticks(game, stocks, updated_snaps, tick_idx, career_day, game_hour, db):
    snap_map = {s.symbol: s for s in updated_snaps}
    for stock in stocks:
        snap = snap_map.get(stock.symbol)
        if snap:
            tick = StockTick(
                game_id=game.id,
                tick_index=tick_idx,
                career_day=career_day,
                game_hour=game_hour,
                symbol=stock.symbol,
                open_price=stock.daily_open,
                high_price=snap.daily_high,
                low_price=snap.daily_low,
                close_price=snap.current_price,
                volume=snap.volume,
            )
            db.add(tick)


def _store_market_tick(game: Game, db: Session):
    tick = MarketTick(
        game_id=game.id,
        tick_index=0,
        career_day=game.career_day,
        game_hour=game.game_hour,
        nifty=game.nifty_value,
        sensex=game.sensex_value,
        bank_nifty=game.bank_nifty_value,
        india_vix=game.india_vix_value,
        usdinr=game.usdinr_value,
        gold=game.gold_value,
        nasdaq=game.nasdaq_value,
        sp500=game.sp500_value,
        market_regime=game.market_regime,
    )
    db.add(tick)
    db.commit()


def _store_market_tick_ex(game, tick_idx, career_day, game_hour, db):
    tick = MarketTick(
        game_id=game.id, tick_index=tick_idx,
        career_day=career_day, game_hour=game_hour,
        nifty=game.nifty_value, sensex=game.sensex_value,
        bank_nifty=game.bank_nifty_value, india_vix=game.india_vix_value,
        usdinr=game.usdinr_value, gold=game.gold_value,
        nasdaq=game.nasdaq_value, sp500=game.sp500_value,
        market_regime=game.market_regime,
    )
    db.add(tick)


def _trigger_quarterly_review(game: Game, port, db: Session):
    game.status = "COMPLETED"
    notifs = list(game.pending_notifications or [])
    notifs.append({
        "id": str(uuid.uuid4()),
        "level": "INFO",
        "message": "90 days complete. Quarterly review is ready.",
        "category": "CAREER",
    })
    game.pending_notifications = notifs
