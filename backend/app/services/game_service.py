import uuid
from datetime import datetime

import numpy as np
from sqlalchemy.orm import Session

from app.models.db_models import (
    Game,
    Stock,
    Holding,
    Transaction,
    StockTick,
    MarketTick,
    NewsItem,
    GameEvent,
    Telemetry,
)
from app.schemas.game_schemas import (
    GameStateResponse,
    TimeInfo,
    FinancialsInfo,
    CareerInfo,
    MarketInfo,
    IndexInfo,
    StockInfo,
    HoldingInfo,
    RiskInfo,
    RiskWarningInfo,
    NewsItemInfo,
    NotificationInfo,
    TradeResult,
    StockCandlesResponse,
    CandleData,
    PerformanceData,
    TransactionInfo,
    QuarterlyReviewResponse,
)
from app.simulation.constants import (
    STOCK_UNIVERSE,
    STARTING_CAPITAL,
    QUARTERLY_TARGET,
    MAX_DRAWDOWN_LIMIT,
    TRANSACTION_FEE_RATE,
    WORKING_HOURS,
    CAREER_DAYS,
    CRORE,
    INDEX_DEFAULTS,
    CAREER_LEVELS,
    MARKET_CLOSE_HOUR,
)
from app.simulation.time_engine import TimeEngine, TimeState
from app.simulation.market_engine import MarketEngine
from app.simulation.event_engine import EventEngine
from app.simulation.news_engine import NewsEngine
from app.simulation.portfolio_engine import PortfolioEngine
from app.simulation.risk_engine import RiskEngine
from app.simulation.career_engine import CareerEngine
from app.simulation.game_director import GameDirector
from app.simulation.ml_engine import MLQuantEngine


def _get_game(game_id: str, db: Session) -> Game:
    game = (
        db.query(Game)
        .filter(Game.id == game_id)
        .first()
    )

    if game is None:
        raise ValueError(f"Game {game_id} not found.")

    return game


def _stocks_map(
    db: Session,
    game_id,
) -> dict[str, Stock]:
    stocks = (
        db.query(Stock)
        .filter(Stock.game_id == game_id)
        .order_by(Stock.symbol)
        .all()
    )

    return {
        stock.symbol: stock
        for stock in stocks
    }


def _holdings_list(
    db: Session,
    game_id,
) -> list[Holding]:
    return (
        db.query(Holding)
        .filter(
            Holding.game_id == game_id,
            Holding.quantity > 0,
        )
        .order_by(Holding.symbol)
        .all()
    )


def _realized_pnl_total(
    db: Session,
    game_id,
) -> float:
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.game_id == game_id,
            Transaction.action == "SELL",
        )
        .all()
    )

    return sum(
        transaction.realized_pnl or 0.0
        for transaction in transactions
    )


def _get_rng(game: Game) -> np.random.Generator:
    tick = TimeEngine.tick_index(
        game.career_day,
        game.game_hour,
    )

    return np.random.default_rng(
        int(game.seed) + tick
    )


def _portfolio_metrics(
    game: Game,
    db: Session,
):
    stocks = _stocks_map(
        db,
        game.id,
    )

    holdings = _holdings_list(
        db,
        game.id,
    )

    metrics = PortfolioEngine.compute(
        cash=game.cash,
        holdings_db=holdings,
        stocks_map=stocks,
        starting_capital=game.starting_capital,
        quarterly_target=game.quarterly_target,
        peak_portfolio_value=game.peak_portfolio_value,
        daily_open_portfolio=game.daily_open_portfolio,
        realized_pnl=_realized_pnl_total(
            db,
            game.id,
        ),
    )

    metrics.max_drawdown = max(
        float(game.max_drawdown or 0.0),
        float(metrics.max_drawdown or 0.0),
    )

    return metrics


def _risk_assessment(
    game: Game,
    db: Session,
    portfolio,
):
    return RiskEngine.assess(
        total_value=portfolio.total_value,
        cash=game.cash,
        holdings_detail=portfolio.holdings,
        sector_exposure=portfolio.sector_exposure,
        max_drawdown=portfolio.max_drawdown,
        portfolio_volatility=portfolio.portfolio_volatility,
        market_regime=game.market_regime,
        max_drawdown_limit=game.max_drawdown_limit,
    )


def _append_notification(
    game: Game,
    level: str,
    message: str,
    category: str,
) -> None:
    notifications = list(
        game.pending_notifications or []
    )

    notifications.append(
        {
            "id": str(uuid.uuid4()),
            "level": level,
            "message": message,
            "category": category,
        }
    )

    game.pending_notifications = notifications[-20:]


def build_state_response(
    game: Game,
    db: Session,
) -> GameStateResponse:
    stocks = _stocks_map(
        db,
        game.id,
    )

    portfolio = _portfolio_metrics(
        game,
        db,
    )

    risk = _risk_assessment(
        game,
        db,
        portfolio,
    )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    working_hours_left = 0

    if game.market_status == "OPEN":
        working_hours_left = max(
            0,
            max(WORKING_HOURS) - game.game_hour + 1,
        )

    time_info = TimeInfo(
        game_date=game.game_date.isoformat(),
        game_hour=game.game_hour,
        day_of_week=days[
            game.game_date.weekday()
        ],
        career_day=game.career_day,
        quarter=game.quarter,
        career_year=game.career_year,
        market_status=game.market_status,
        working_hours_left=working_hours_left,
    )

    financials = FinancialsInfo(
        cash=portfolio.cash,
        cash_cr=round(
            portfolio.cash / CRORE,
            4,
        ),
        invested_value=portfolio.invested_value,
        invested_value_cr=round(
            portfolio.invested_value / CRORE,
            4,
        ),
        total_value=portfolio.total_value,
        total_value_cr=round(
            portfolio.total_value / CRORE,
            4,
        ),
        starting_capital=portfolio.starting_capital,
        starting_capital_cr=round(
            portfolio.starting_capital / CRORE,
            4,
        ),
        quarterly_target=portfolio.quarterly_target,
        quarterly_target_cr=round(
            portfolio.quarterly_target / CRORE,
            4,
        ),
        total_pnl=portfolio.total_pnl,
        total_pnl_cr=round(
            portfolio.total_pnl / CRORE,
            4,
        ),
        total_return_pct=round(
            portfolio.total_return_pct,
            4,
        ),
        realized_pnl=portfolio.realized_pnl,
        unrealized_pnl=portfolio.unrealized_pnl,
        daily_pnl=portfolio.daily_pnl,
        daily_pnl_cr=round(
            portfolio.daily_pnl / CRORE,
            4,
        ),
        max_drawdown=round(
            portfolio.max_drawdown * 100,
            4,
        ),
        target_progress=round(
            portfolio.target_progress * 100,
            2,
        ),
        to_target=portfolio.to_target,
        to_target_cr=round(
            portfolio.to_target / CRORE,
            4,
        ),
        target_met=portfolio.target_met,
        portfolio_volatility=round(
            portfolio.portfolio_volatility * 100,
            2,
        ),
    )

    level_data = CAREER_LEVELS.get(
        game.career_level,
        CAREER_LEVELS[1],
    )

    career = CareerInfo(
        level=game.career_level,
        role=CareerEngine.get_role_title(
            game.career_level
        ),
        xp=game.xp,
        xp_to_next_level=level_data.get(
            "xp_to_next",
            99999,
        ),
        reputation=round(
            game.reputation,
            1,
        ),
        leave_balance=game.leave_balance,
        leave_used=game.leave_used,
        leave_year=game.leave_year,
        on_leave=game.on_leave,
        career_status=game.career_status,
        career_review_count=game.career_review_count,
        career_failure_count=game.career_failure_count,
        last_review_result=game.last_review_result,
    )

    market_ticks = (
        db.query(MarketTick)
        .filter(
            MarketTick.game_id == game.id
        )
        .order_by(
            MarketTick.tick_index.desc()
        )
        .limit(2)
        .all()
    )

    previous_tick = (
        market_ticks[1]
        if len(market_ticks) > 1
        else None
    )

    previous = {
        "NIFTY50": INDEX_DEFAULTS["nifty"],
        "SENSEX": INDEX_DEFAULTS["sensex"],
        "BANKNIFTY": INDEX_DEFAULTS["bank_nifty"],
        "INDIAVIX": INDEX_DEFAULTS["india_vix"],
        "USDINR": INDEX_DEFAULTS["usdinr"],
        "GOLD": INDEX_DEFAULTS["gold"],
        "NASDAQ": INDEX_DEFAULTS["nasdaq"],
        "SP500": INDEX_DEFAULTS["sp500"],
    }

    if previous_tick:
        previous = {
            "NIFTY50": previous_tick.nifty,
            "SENSEX": previous_tick.sensex,
            "BANKNIFTY": previous_tick.bank_nifty,
            "INDIAVIX": previous_tick.india_vix,
            "USDINR": previous_tick.usdinr,
            "GOLD": previous_tick.gold,
            "NASDAQ": previous_tick.nasdaq,
            "SP500": previous_tick.sp500,
        }

    index_values = [
        ("NIFTY50", "NIFTY 50", game.nifty_value),
        ("SENSEX", "SENSEX", game.sensex_value),
        ("BANKNIFTY", "BANK NIFTY", game.bank_nifty_value),
        ("INDIAVIX", "INDIA VIX", game.india_vix_value),
        ("USDINR", "USD/INR", game.usdinr_value),
        ("GOLD", "GOLD (₹/10g)", game.gold_value),
        ("NASDAQ", "NASDAQ", game.nasdaq_value),
        ("SP500", "S&P 500", game.sp500_value),
    ]

    indices = []

    for symbol, name, value in index_values:
        prev = previous.get(symbol, value)

        change_pct = (
            ((value / prev) - 1.0) * 100
            if prev
            else 0.0
        )

        indices.append(
            IndexInfo(
                symbol=symbol,
                name=name,
                value=round(value, 4),
                prev_value=round(prev, 4),
                change_pct=round(change_pct, 4),
            )
        )

    stocks_response = []

    for stock in stocks.values():
        daily_return = (
            (
                stock.current_price /
                stock.daily_open
            ) - 1.0
        ) * 100 if stock.daily_open else 0.0

        stocks_response.append(
            StockInfo(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                current_price=stock.current_price,
                previous_price=stock.previous_price,
                daily_open=stock.daily_open,
                daily_high=stock.daily_high,
                daily_low=stock.daily_low,
                daily_return=round(
                    daily_return,
                    4,
                ),
                volume=int(stock.volume),
                volatility=stock.volatility,
                beta=stock.beta,
                sentiment=stock.sentiment,
                momentum=stock.momentum,
                growth=stock.growth,
                profitability=stock.profitability,
                debt=stock.debt,
                valuation=stock.valuation,
            )
        )

    holdings_response = [
        HoldingInfo(
            symbol=item["symbol"],
            name=item["name"],
            sector=item["sector"],
            quantity=item["quantity"],
            avg_buy_price=item["avg_buy_price"],
            current_price=item["current_price"],
            current_value=item["current_value"],
            current_value_cr=round(
                item["current_value"] / CRORE,
                4,
            ),
            cost_basis=item["cost_basis"],
            unrealized_pnl=item["unrealized_pnl"],
            unrealized_pnl_pct=round(
                item["unrealized_pnl_pct"],
                4,
            ),
            daily_return=round(
                item.get("daily_return", 0.0) * 100,
                4,
            ),
        )
        for item in portfolio.holdings
    ]

    risk_response = RiskInfo(
        overall_level=risk.overall_level,
        risk_score=risk.risk_score,
        warnings=[
            RiskWarningInfo(
                code=warning.code,
                level=warning.level,
                message=warning.message,
                value=warning.value,
                limit=warning.limit,
                symbol=warning.symbol,
                sector=warning.sector,
            )
            for warning in risk.warnings
        ],
        drawdown_pct=risk.drawdown_pct,
        cash_ratio=risk.cash_ratio,
        largest_position_pct=risk.largest_position_pct,
        sector_concentration=risk.sector_concentration,
        portfolio_volatility=risk.portfolio_volatility,
    )

    news = (
        db.query(NewsItem)
        .filter(
            NewsItem.game_id == game.id
        )
        .order_by(
            NewsItem.career_day.desc(),
            NewsItem.game_hour.desc(),
            NewsItem.created_at.desc(),
        )
        .limit(15)
        .all()
    )

    news_response = [
        NewsItemInfo(
            id=str(item.id),
            category=item.category,
            priority=item.priority,
            headline=item.headline,
            body=item.body,
            affected_symbol=item.affected_symbol,
            affected_sector=item.affected_sector,
            market_impact=item.market_impact,
            career_day=item.career_day,
            game_hour=item.game_hour,
            is_read=item.is_read,
        )
        for item in news
    ]

    notifications = [
        NotificationInfo(
            id=item["id"],
            level=item["level"],
            message=item["message"],
            category=item["category"],
        )
        for item in (
            game.pending_notifications or []
        )
    ]

    trade_count = _trade_count_today(
        game,
        db,
    )

    return GameStateResponse(
        game_id=str(game.id),
        player_name=game.player_name,
        status=game.status,
        time=time_info,
        financials=financials,
        career=career,
        market=MarketInfo(
            regime=game.market_regime,
            indices=indices,
            stocks=stocks_response,
        ),
        holdings=holdings_response,
        risk=risk_response,
        recent_news=news_response,
        notifications=notifications,
        trade_count_today=trade_count,
    )


def create_new_game(
    player_name: str,
    db: Session,
) -> str:
    seed = int(
        np.random.default_rng().integers(
            0,
            2**32,
        )
    )

    time_state = TimeEngine.build_initial_state()

    game = Game(
        id=uuid.uuid4(),
        player_name=player_name,
        seed=seed,
        status="ACTIVE",
        game_date=time_state.game_date,
        game_hour=time_state.game_hour,
        career_day=time_state.career_day,
        quarter=time_state.quarter,
        career_year=time_state.career_year,
        market_status=time_state.market_status,
        cash=STARTING_CAPITAL,
        starting_capital=STARTING_CAPITAL,
        quarterly_target=QUARTERLY_TARGET,
        max_drawdown_limit=MAX_DRAWDOWN_LIMIT,
        peak_portfolio_value=STARTING_CAPITAL,
        daily_open_portfolio=STARTING_CAPITAL,
        career_level=1,
        xp=0,
        reputation=50.0,
        career_review_count=0,
        career_failure_count=0,
        last_review_result=None,
        career_status="ACTIVE",
        leave_balance=60,
        leave_used=0,
        leave_year=1,
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

    rng = np.random.default_rng(seed)

    for definition in STOCK_UNIVERSE:
        base_price = round(
            definition["base_price"]
            * rng.uniform(0.95, 1.05),
            2,
        )

        db.add(
            Stock(
                game_id=game.id,
                symbol=definition["symbol"],
                name=definition["name"],
                sector=definition["sector"],
                base_price=base_price,
                current_price=base_price,
                previous_price=base_price,
                daily_open=base_price,
                daily_high=base_price,
                daily_low=base_price,
                volume=0,
                volatility=definition["volatility"],
                beta=definition["beta"],
                growth=definition["growth"],
                profitability=definition["profitability"],
                debt=definition["debt"],
                valuation=definition["valuation"],
                sentiment=rng.uniform(0.45, 0.55),
                momentum=0.0,
                market_sensitivity=definition["market_sensitivity"],
                event_sensitivity=definition["event_sensitivity"],
                institutional_pressure=0.0,
            )
        )

    db.flush()

    _store_market_tick(
        game,
        db,
    )

    db.commit()
    db.refresh(game)

    return str(game.id)


def advance_game_time(
    game_id: str,
    hours: int,
    db: Session,
) -> GameStateResponse:
    if hours < 1:
        raise ValueError("Hours must be at least 1.")

    game = _get_game(game_id, db)

    if game.status != "ACTIVE":
        raise ValueError(
            f"Game is {game.status} and cannot advance."
        )

    for _ in range(hours):
        if game.status != "ACTIVE":
            break

        _advance_one_hour(
            game,
            db,
        )

    game.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(game)

    return build_state_response(game, db)


def advance_to_market_close(
    game_id: str,
    db: Session,
) -> GameStateResponse:
    game = _get_game(game_id, db)

    if game.status != "ACTIVE":
        raise ValueError(
            f"Game is {game.status} and cannot advance."
        )

    state = _time_state_from_game(game)
    results = TimeEngine.advance_to_market_close(state)

    for _ in results:
        if game.status != "ACTIVE":
            break
        _advance_one_hour(game, db)

    game.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(game)

    return build_state_response(game, db)


def advance_to_next_business_day(
    game_id: str,
    db: Session,
) -> GameStateResponse:
    game = _get_game(game_id, db)

    if game.status != "ACTIVE":
        raise ValueError(
            f"Game is {game.status} and cannot advance."
        )

    state = _time_state_from_game(game)
    results = TimeEngine.advance_to_next_business_day(state)

    for _ in results:
        if game.status != "ACTIVE":
            break
        _advance_one_hour(game, db)

    game.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(game)

    return build_state_response(game, db)


def skip_weekend(
    game_id: str,
    db: Session,
) -> GameStateResponse:
    game = _get_game(game_id, db)

    if game.status != "ACTIVE":
        raise ValueError(
            f"Game is {game.status} and cannot advance."
        )

    if game.game_date.weekday() not in (4, 5, 6):
        raise ValueError(
            "Skip weekend is only available on Friday or during the weekend."
        )

    state = _time_state_from_game(game)
    results = TimeEngine.skip_weekend(state)

    for _ in results:
        if game.status != "ACTIVE":
            break
        _advance_one_hour(game, db)

    game.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(game)

    return build_state_response(game, db)

def _advance_one_hour(
    game: Game,
    db: Session,
) -> None:
    previous_day = game.career_day
    previous_hour = game.game_hour
    previous_date = game.game_date

    market_was_open = (
        previous_date.weekday() < 5
        and previous_hour in WORKING_HOURS
    )

    rng = _get_rng(game)

    if market_was_open:
        _simulate_market_hour(
            game=game,
            db=db,
            rng=rng,
            career_day=previous_day,
            game_hour=previous_hour,
        )

        _process_career_tick(
            game,
            db,
        )

        _record_telemetry(
            game,
            db,
        )

    state = _time_state_from_game(game)
    result = TimeEngine.advance_one_hour(state)
    new_state = result.new_state

    game.game_date = new_state.game_date
    game.game_hour = new_state.game_hour
    game.career_day = new_state.career_day

    game.quarter = (
        ((new_state.career_day - 1) // CAREER_DAYS) + 1
    )

    game.career_year = (
        ((new_state.career_day - 1) // (CAREER_DAYS * 4)) + 1
    )

    game.market_status = new_state.market_status
    game.on_leave = new_state.on_leave
    game.leave_balance = new_state.leave_balance
    game.leave_used = new_state.leave_used

    if result.new_career_day:
        game.daily_open_portfolio = (
            game.cash
            + _compute_invested_value(
                game,
                db,
            )
        )

        stocks = (
            db.query(Stock)
            .filter(Stock.game_id == game.id)
            .all()
        )

        MarketEngine.reset_daily_ohlc(
            stocks
        )

        for stock in stocks:
            stock.volume = 0

    if (
        game.career_day >= CAREER_DAYS
        and game.career_day % CAREER_DAYS == 0
        and game.status == "ACTIVE"
    ):
        game.status = "REVIEW"
        game.career_status = "REVIEW"

    game.updated_at = datetime.utcnow()

def _active_events_for_tick(
    game: Game,
    db: Session,
    career_day: int,
    game_hour: int,
) -> list[GameEvent]:
    events = (
        db.query(GameEvent)
        .filter(
            GameEvent.game_id == game.id,
            GameEvent.is_active.is_(True),
        )
        .order_by(
            GameEvent.trigger_day,
            GameEvent.trigger_hour,
        )
        .all()
    )

    current_tick = TimeEngine.tick_index(
        career_day,
        game_hour,
    )

    active = []

    for event in events:
        trigger_tick = TimeEngine.tick_index(
            event.trigger_day,
            event.trigger_hour,
        )

        duration = max(
            1,
            int(event.duration_hours),
        )

        if (
            trigger_tick
            <= current_tick
            < trigger_tick + duration
        ):
            active.append(event)

    return active


def _simulate_market_hour(
    game: Game,
    db: Session,
    rng: np.random.Generator,
    career_day: int,
    game_hour: int,
) -> None:
    stocks = (
        db.query(Stock)
        .filter(Stock.game_id == game.id)
        .order_by(Stock.symbol)
        .all()
    )

    portfolio = _portfolio_metrics(
        game,
        db,
    )

    risk = _risk_assessment(
        game,
        db,
        portfolio,
    )

    director = GameDirector.evaluate(
        career_day=career_day,
        target_progress=portfolio.target_progress,
        reputation=game.reputation,
        cash_ratio=risk.cash_ratio / 100.0,
        trade_count_today=_trade_count_today(
            game,
            db,
        ),
        max_drawdown=portfolio.max_drawdown,
        market_regime=game.market_regime,
        portfolio_volatility=portfolio.portfolio_volatility,
        rng=rng,
    )

    events = EventEngine.generate_daily_events(
        career_day=career_day,
        game_hour=game_hour,
        stocks=stocks,
        game=game,
        rng=rng,
        probability_multiplier=director.suggested_event_boost,
    )

    for event in events:
        _persist_event(
            game,
            event,
            db,
        )

    db.flush()

    active_events = _active_events_for_tick(
        game,
        db,
        career_day,
        game_hour,
    )

    event_shocks = EventEngine.get_event_shocks(
        active_events,
    )

    macro_sector_shocks = (
        EventEngine.get_macro_sector_shocks(
            active_events,
        )
    )

    for stock in stocks:
        sector_shock = macro_sector_shocks.get(
            stock.sector,
            0.0,
        )

        if sector_shock:
            event_shocks[stock.symbol] = (
                event_shocks.get(
                    stock.symbol,
                    0.0,
                )
                + sector_shock
            )

    result = MarketEngine.simulate_tick(
        stocks=stocks,
        game=game,
        rng=rng,
        event_shocks=event_shocks,
    )

    snapshots_map = {
        snapshot.symbol: snapshot
        for snapshot in result.updated_stocks
    }

    for stock in stocks:
        snapshot = snapshots_map.get(
            stock.symbol
        )

        if snapshot is None:
            continue

        stock.previous_price = stock.current_price
        stock.current_price = snapshot.current_price
        stock.daily_open = snapshot.daily_open
        stock.daily_high = snapshot.daily_high
        stock.daily_low = snapshot.daily_low
        stock.volume = snapshot.volume
        stock.sentiment = snapshot.sentiment
        stock.momentum = snapshot.momentum
        stock.institutional_pressure = (
            snapshot.institutional_pressure
        )

    game.nifty_value = result.nifty
    game.sensex_value = result.sensex
    game.bank_nifty_value = result.bank_nifty
    game.india_vix_value = result.india_vix
    game.usdinr_value = result.usdinr
    game.gold_value = result.gold
    game.nasdaq_value = result.nasdaq
    game.sp500_value = result.sp500

    if (
        result.regime_changed
        and result.new_regime
    ):
        game.market_regime = result.new_regime

        _append_notification(
            game,
            (
                "WARNING"
                if result.new_regime
                in ("BEAR", "CRISIS")
                else "INFO"
            ),
            (
                "Market regime shifted to "
                f"{result.new_regime}."
            ),
            "MARKET",
        )

    tick_index = TimeEngine.tick_index(
        career_day,
        game_hour,
    )

    _store_stock_ticks(
        game=game,
        stocks=stocks,
        snapshots=result.updated_stocks,
        tick_index=tick_index,
        career_day=career_day,
        game_hour=game_hour,
        db=db,
    )

    _store_market_tick_ex(
        game=game,
        tick_index=tick_index,
        career_day=career_day,
        game_hour=game_hour,
        db=db,
    )

    _deactivate_expired_events(
        game,
        db,
    )

    if game_hour == 14:
        portfolio = _portfolio_metrics(
            game,
            db,
        )

        ceo_news = (
            NewsEngine.generate_ceo_message(
                portfolio_return=portfolio.total_return_pct,
                career_day=career_day,
                target_progress=portfolio.target_progress,
                rng=rng,
            )
        )

        if ceo_news:
            db.add(
                NewsItem(
                    id=uuid.uuid4(),
                    game_id=game.id,
                    career_day=career_day,
                    game_hour=game_hour,
                    category="CEO",
                    priority="HIGH",
                    headline=ceo_news.headline,
                    body=ceo_news.body,
                    affected_symbol=None,
                    affected_sector=None,
                    market_impact=0.0,
                )
            )

def _process_career_tick(
    game: Game,
    db: Session,
) -> None:
    portfolio = _portfolio_metrics(
        game,
        db,
    )

    risk = _risk_assessment(
        game,
        db,
        portfolio,
    )

    career_update = CareerEngine.update_per_tick(
        career_level=game.career_level,
        xp=game.xp,
        reputation=game.reputation,
        total_return_pct=portfolio.total_return_pct,
        risk_assessment=risk,
        target_progress=portfolio.target_progress,
    )

    game.xp = min(
        99999,
        game.xp + career_update.xp_gained,
    )

    game.reputation = max(
        0.0,
        min(
            100.0,
            game.reputation
            + career_update.reputation_change,
        ),
    )

    game.peak_portfolio_value = max(
        game.peak_portfolio_value,
        portfolio.total_value,
    )

    game.max_drawdown = max(
        game.max_drawdown,
        portfolio.max_drawdown,
    )

    game.daily_pnl = portfolio.daily_pnl
    game.active_risk_level = risk.overall_level

    game.risk_warnings = [
        {
            "code": warning.code,
            "level": warning.level,
            "message": warning.message,
            "value": warning.value,
            "limit": warning.limit,
            "symbol": warning.symbol,
            "sector": warning.sector,
        }
        for warning in risk.warnings
    ]

    if career_update.notification:
        _append_notification(
            game,
            "INFO",
            career_update.notification,
            "CAREER",
        )


def _persist_event(
    game: Game,
    event,
    db: Session,
) -> None:
    db_event = GameEvent(
        id=uuid.uuid4(),
        game_id=game.id,
        event_type=event.event_type,
        severity=event.severity,
        affected_symbol=event.affected_symbol,
        affected_sector=event.affected_sector,
        trigger_day=event.trigger_day,
        trigger_hour=event.trigger_hour,
        duration_hours=event.duration_hours,
        price_impact=event.price_impact,
        narrative=event.narrative,
        is_processed=False,
        is_active=True,
        follow_up_event_type=event.follow_up_event_type,
        follow_up_day=event.follow_up_day,
    )

    db.add(db_event)

    news = NewsEngine.news_from_event(event)

    db.add(
        NewsItem(
            id=uuid.uuid4(),
            game_id=game.id,
            career_day=game.career_day,
            game_hour=game.game_hour,
            category=news.category,
            priority=news.priority,
            headline=news.headline,
            body=news.body,
            affected_symbol=news.affected_symbol,
            affected_sector=news.affected_sector,
            market_impact=news.market_impact,
        )
    )

    if event.severity in (
        "HIGH",
        "CRITICAL",
    ):
        level = (
            "CRITICAL"
            if event.severity == "CRITICAL"
            else "WARNING"
        )

        _append_notification(
            game,
            level,
            event.narrative[:160],
            "EVENT",
        )


def _deactivate_expired_events(
    game: Game,
    db: Session,
) -> None:
    events = (
        db.query(GameEvent)
        .filter(
            GameEvent.game_id == game.id,
            GameEvent.is_active.is_(True),
        )
        .all()
    )

    current_tick = TimeEngine.tick_index(
        game.career_day,
        game.game_hour,
    )

    for event in events:
        event_tick = TimeEngine.tick_index(
            event.trigger_day,
            event.trigger_hour,
        )

        if (
            current_tick - event_tick
            >= event.duration_hours
        ):
            event.is_active = False
            event.is_processed = True


def _record_telemetry(
    game: Game,
    db: Session,
) -> None:
    portfolio = _portfolio_metrics(
        game,
        db,
    )

    risk = _risk_assessment(
        game,
        db,
        portfolio,
    )

    tick_index = TimeEngine.tick_index(
        game.career_day,
        game.game_hour,
    )

    db.add(
        Telemetry(
            game_id=game.id,
            tick_index=tick_index,
            career_day=game.career_day,
            game_hour=game.game_hour,
            cash=game.cash,
            portfolio_value=portfolio.total_value,
            total_return_pct=portfolio.total_return_pct,
            max_drawdown=portfolio.max_drawdown,
            risk_score=risk.risk_score,
            holding_count=len(portfolio.holdings),
            trade_count_today=_trade_count_today(
                game,
                db,
            ),
            largest_position_pct=risk.largest_position_pct,
            market_regime=game.market_regime,
            reputation=game.reputation,
            target_progress=portfolio.target_progress,
        )
    )


def execute_buy(
    game_id: str,
    symbol: str,
    quantity: int,
    db: Session,
) -> TradeResult:
    game = _get_game(game_id, db)

    symbol = symbol.upper().strip()

    if game.status != "ACTIVE":
        return _failed_trade(
            game,
            symbol,
            quantity,
            "BUY",
            f"Game is {game.status}.",
        )

    if game.market_status != "OPEN":
        return _failed_trade(
            game,
            symbol,
            quantity,
            "BUY",
            "Market is closed.",
        )

    if quantity <= 0:
        return _failed_trade(
            game,
            symbol,
            quantity,
            "BUY",
            "Quantity must be positive.",
        )

    stock = (
        db.query(Stock)
        .filter(
            Stock.game_id == game.id,
            Stock.symbol == symbol,
        )
        .first()
    )

    if stock is None:
        return _failed_trade(
            game,
            symbol,
            quantity,
            "BUY",
            f"Unknown symbol: {symbol}",
        )

    stocks = _stocks_map(
        db,
        game.id,
    )

    valid, message = PortfolioEngine.validate_buy(
        game.cash,
        symbol,
        quantity,
        stock.current_price,
        stocks,
    )

    if not valid:
        return _failed_trade(
            game,
            symbol,
            quantity,
            "BUY",
            message,
            stock.current_price,
        )

    price = stock.current_price
    value = quantity * price

    fee = round(
        value * TRANSACTION_FEE_RATE,
        2,
    )

    total_cost = value + fee
    cash_before = game.cash

    game.cash -= total_cost

    holding = (
        db.query(Holding)
        .filter(
            Holding.game_id == game.id,
            Holding.symbol == symbol,
        )
        .first()
    )

    if holding is None:
        holding = Holding(
            game_id=game.id,
            symbol=symbol,
            quantity=quantity,
            avg_buy_price=total_cost / quantity,
            total_cost=total_cost,
        )

        db.add(holding)

    else:
        old_cost = (
            holding.quantity
            * holding.avg_buy_price
        )

        new_quantity = (
            holding.quantity
            + quantity
        )

        new_cost = (
            old_cost
            + total_cost
        )

        holding.quantity = new_quantity
        holding.avg_buy_price = (
            new_cost / new_quantity
        )
        holding.total_cost += total_cost

    db.add(
        Transaction(
            id=uuid.uuid4(),
            game_id=game.id,
            career_day=game.career_day,
            game_date=game.game_date,
            game_hour=game.game_hour,
            symbol=symbol,
            name=stock.name,
            action="BUY",
            quantity=quantity,
            price=price,
            total_value=value,
            fee=fee,
            cash_before=cash_before,
            cash_after=game.cash,
            realized_pnl=None,
        )
    )

    game.xp = min(
        99999,
        game.xp + 10,
    )

    game.updated_at = datetime.utcnow()

    db.commit()

    return TradeResult(
        success=True,
        message=(
            f"Bought {quantity:,} shares of "
            f"{stock.name} at ₹{price:,.2f}"
        ),
        symbol=symbol,
        action="BUY",
        quantity=quantity,
        price=price,
        total_value=value,
        fee=fee,
        cash_after=game.cash,
        cash_after_cr=round(
            game.cash / CRORE,
            4,
        ),
    )


def execute_sell(
    game_id: str,
    symbol: str,
    quantity: int,
    db: Session,
) -> TradeResult:
    game = _get_game(game_id, db)

    symbol = symbol.upper().strip()

    if game.status != "ACTIVE":
        return _failed_trade(
            game,
            symbol,
            quantity,
            "SELL",
            f"Game is {game.status}.",
        )

    if game.market_status != "OPEN":
        return _failed_trade(
            game,
            symbol,
            quantity,
            "SELL",
            "Market is closed.",
        )

    if quantity <= 0:
        return _failed_trade(
            game,
            symbol,
            quantity,
            "SELL",
            "Quantity must be positive.",
        )

    stock = (
        db.query(Stock)
        .filter(
            Stock.game_id == game.id,
            Stock.symbol == symbol,
        )
        .first()
    )

    if stock is None:
        return _failed_trade(
            game,
            symbol,
            quantity,
            "SELL",
            f"Unknown symbol: {symbol}",
        )

    holding = (
        db.query(Holding)
        .filter(
            Holding.game_id == game.id,
            Holding.symbol == symbol,
        )
        .first()
    )

    if holding is None:
        return _failed_trade(
            game,
            symbol,
            quantity,
            "SELL",
            f"You do not hold {symbol}.",
            stock.current_price,
        )

    if quantity > holding.quantity:
        return _failed_trade(
            game,
            symbol,
            quantity,
            "SELL",
            (
                f"Cannot sell {quantity:,} shares. "
                f"You only hold {holding.quantity:,}."
            ),
            stock.current_price,
        )

    price = stock.current_price
    value = quantity * price

    fee = round(
        value * TRANSACTION_FEE_RATE,
        2,
    )

    proceeds = value - fee
    cash_before = game.cash

    game.cash += proceeds

    avg_price = holding.avg_buy_price

    realized_pnl = (
        (price - avg_price)
        * quantity
        - fee
    )

    holding.quantity -= quantity

    holding.total_cost = max(
        0.0,
        holding.total_cost
        - avg_price * quantity,
    )

    if holding.quantity == 0:
        holding.avg_buy_price = 0.0
        holding.total_cost = 0.0

    db.add(
        Transaction(
            id=uuid.uuid4(),
            game_id=game.id,
            career_day=game.career_day,
            game_date=game.game_date,
            game_hour=game.game_hour,
            symbol=symbol,
            name=stock.name,
            action="SELL",
            quantity=quantity,
            price=price,
            total_value=value,
            fee=fee,
            cash_before=cash_before,
            cash_after=game.cash,
            realized_pnl=realized_pnl,
        )
    )

    game.xp = min(
        99999,
        game.xp + 10,
    )

    game.updated_at = datetime.utcnow()

    db.commit()

    return TradeResult(
        success=True,
        message=(
            f"Sold {quantity:,} shares of "
            f"{stock.name} at ₹{price:,.2f}"
        ),
        symbol=symbol,
        action="SELL",
        quantity=quantity,
        price=price,
        total_value=value,
        fee=fee,
        cash_after=game.cash,
        cash_after_cr=round(
            game.cash / CRORE,
            4,
        ),
        realized_pnl=realized_pnl,
    )


def start_leave(
    game_id: str,
    db: Session,
) -> GameStateResponse:
    game = _get_game(game_id, db)

    if game.status != "ACTIVE":
        raise ValueError(
            f"Game is {game.status} and cannot change leave status."
        )

    state = _time_state_from_game(game)
    new_state, error = TimeEngine.start_leave(state)

    if error:
        raise ValueError(error)

    game.on_leave = new_state.on_leave
    game.leave_balance = new_state.leave_balance
    game.leave_used = new_state.leave_used
    game.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(game)

    return build_state_response(game, db)


def end_leave(
    game_id: str,
    db: Session,
) -> GameStateResponse:
    game = _get_game(game_id, db)

    state = _time_state_from_game(game)
    new_state = TimeEngine.end_leave(state)

    game.on_leave = new_state.on_leave
    game.leave_balance = new_state.leave_balance
    game.leave_used = new_state.leave_used
    game.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(game)

    return build_state_response(game, db)


def take_leave(
    game_id: str,
    days: int,
    db: Session,
) -> GameStateResponse:
    game = _get_game(game_id, db)

    if game.status != "ACTIVE":
        raise ValueError(
            f"Game is {game.status} and cannot take leave."
        )

    state = _time_state_from_game(game)
    results, error = TimeEngine.take_leave(
        state,
        days,
    )

    if error:
        raise ValueError(error)

    for _ in results:
        if game.status != "ACTIVE":
            break
        _advance_one_hour(game, db)

    if results:
        final_state = results[-1].new_state

        game.game_date = final_state.game_date
        game.game_hour = final_state.game_hour
        game.career_day = final_state.career_day
        game.quarter = (
            ((final_state.career_day - 1) // CAREER_DAYS) + 1
        )
        game.career_year = (
            ((final_state.career_day - 1) // (CAREER_DAYS * 4)) + 1
        )
        game.market_status = final_state.market_status
        game.on_leave = final_state.on_leave
        game.leave_balance = final_state.leave_balance
        game.leave_used = final_state.leave_used

    game.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(game)

    return build_state_response(game, db)


def get_stock_candles(
    game_id: str,
    symbol: str,
    days: int,
    db: Session,
) -> StockCandlesResponse:
    game = _get_game(game_id, db)

    symbol = symbol.upper().strip()

    stock = (
        db.query(Stock)
        .filter(
            Stock.game_id == game.id,
            Stock.symbol == symbol,
        )
        .first()
    )

    if stock is None:
        raise ValueError(
            f"Stock {symbol} not found."
        )

    days = max(
        1,
        min(days, 90),
    )

    ticks_per_day = max(
        1,
        len(WORKING_HOURS),
    )

    ticks = (
        db.query(StockTick)
        .filter(
            StockTick.game_id == game.id,
            StockTick.symbol == symbol,
        )
        .order_by(
            StockTick.tick_index.desc()
        )
        .limit(days * ticks_per_day)
        .all()
    )

    ticks.reverse()

    daily = {}

    for tick in ticks:
        day = tick.career_day

        if day not in daily:
            daily[day] = {
                "open": tick.open_price,
                "high": tick.high_price,
                "low": tick.low_price,
                "close": tick.close_price,
                "volume": int(tick.volume),
            }

        else:
            daily[day]["high"] = max(
                daily[day]["high"],
                tick.high_price,
            )

            daily[day]["low"] = min(
                daily[day]["low"],
                tick.low_price,
            )

            daily[day]["close"] = tick.close_price

            daily[day]["volume"] += int(
                tick.volume
            )

    candles = []

    for career_day in sorted(daily)[-days:]:
        values = daily[career_day]

        candles.append(
            CandleData(
                time=f"Day {career_day}",
                open=values["open"],
                high=values["high"],
                low=values["low"],
                close=values["close"],
                volume=values["volume"],
            )
        )

    if not candles:
        candles.append(
            CandleData(
                time=game.game_date.isoformat(),
                open=stock.daily_open,
                high=stock.daily_high,
                low=stock.daily_low,
                close=stock.current_price,
                volume=int(stock.volume),
            )
        )

    return StockCandlesResponse(
        symbol=symbol,
        name=stock.name,
        candles=candles,
    )


def get_ml_prediction(
    game_id: str,
    symbol: str,
    db: Session,
) -> dict:
    game = _get_game(game_id, db)

    symbol = symbol.upper().strip()

    stock = (
        db.query(Stock)
        .filter(
            Stock.game_id == game.id,
            Stock.symbol == symbol,
        )
        .first()
    )

    if stock is None:
        raise ValueError(
            f"Stock {symbol} not found."
        )

    tick_history = (
        db.query(StockTick)
        .filter(
            StockTick.game_id == game.id,
            StockTick.symbol == symbol,
        )
        .order_by(
            StockTick.tick_index.desc()
        )
        .limit(250)
        .all()
    )

    tick_history.reverse()

    market_history = (
        db.query(MarketTick)
        .filter(
            MarketTick.game_id == game.id
        )
        .order_by(
            MarketTick.tick_index.desc()
        )
        .limit(250)
        .all()
    )

    market_history.reverse()

    nifty_history = [
        float(tick.nifty)
        for tick in market_history
    ]

    return MLQuantEngine.predict_stock(
        stock=stock,
        tick_history=tick_history,
        nifty_history=nifty_history,
        market_regime=game.market_regime,
        india_vix=game.india_vix_value,
    )


def get_ml_forecast(
    game_id: str,
    symbol: str,
    db: Session,
) -> dict:
    prediction = get_ml_prediction(
        game_id,
        symbol,
        db,
    )

    forecast_path = MLQuantEngine.generate_forecast_path(
        current_price=prediction["current_price"],
        target_price=prediction["predicted_price_1d"],
        expected_return_pct=prediction[
            "predicted_return_pct_1d"
        ],
        var_95_pct=prediction["var_95_pct"],
        num_ticks=len(WORKING_HOURS),
    )

    prediction["forecast_path"] = forecast_path

    return prediction


def get_performance(
    game_id: str,
    db: Session,
) -> PerformanceData:
    game = _get_game(game_id, db)

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.game_id == game.id
        )
        .order_by(
            Transaction.created_at
        )
        .all()
    )

    sell_transactions = [
        transaction
        for transaction in transactions
        if transaction.action == "SELL"
    ]

    pnls = [
        transaction.realized_pnl or 0.0
        for transaction in sell_transactions
    ]

    wins = [
        pnl
        for pnl in pnls
        if pnl > 0
    ]

    win_rate = (
        len(wins) / len(pnls) * 100
        if pnls
        else 0.0
    )

    portfolio = _portfolio_metrics(
        game,
        db,
    )

    telemetry = (
        db.query(Telemetry)
        .filter(
            Telemetry.game_id == game.id
        )
        .order_by(
            Telemetry.tick_index
        )
        .all()
    )

    daily_values = []
    seen_days = set()

    for item in telemetry:
        if item.career_day in seen_days:
            continue

        daily_values.append(
            {
                "day": item.career_day,
                "value": item.portfolio_value,
            }
        )

        seen_days.add(item.career_day)

    market_ticks = (
        db.query(MarketTick)
        .filter(
            MarketTick.game_id == game.id
        )
        .order_by(
            MarketTick.tick_index
        )
        .all()
    )

    benchmark_return = 0.0

    if market_ticks:
        benchmark_return = (
            (
                market_ticks[-1].nifty
                / INDEX_DEFAULTS["nifty"]
            ) - 1
        ) * 100

    transaction_response = [
        TransactionInfo(
            id=str(item.id),
            career_day=item.career_day,
            game_date=item.game_date.isoformat(),
            game_hour=item.game_hour,
            symbol=item.symbol,
            name=item.name,
            action=item.action,
            quantity=item.quantity,
            price=item.price,
            total_value=item.total_value,
            fee=item.fee,
            realized_pnl=item.realized_pnl,
            created_at=item.created_at.isoformat(),
        )
        for item in transactions
    ]

    return PerformanceData(
        total_return_pct=round(
            portfolio.total_return_pct,
            4,
        ),
        benchmark_return_pct=round(
            benchmark_return,
            4,
        ),
        max_drawdown=round(
            portfolio.max_drawdown * 100,
            4,
        ),
        portfolio_volatility=round(
            portfolio.portfolio_volatility * 100,
            4,
        ),
        win_rate=round(
            win_rate,
            2,
        ),
        avg_trade_pnl=round(
            sum(pnls) / len(pnls),
            2,
        ) if pnls else 0.0,
        best_trade_pnl=round(
            max(pnls),
            2,
        ) if pnls else 0.0,
        worst_trade_pnl=round(
            min(pnls),
            2,
        ) if pnls else 0.0,
        trade_count=len(transactions),
        sector_attribution=portfolio.sector_exposure,
        transactions=transaction_response,
        daily_portfolio_values=daily_values,
    )


def do_quarterly_review(
    game_id: str,
    db: Session,
) -> QuarterlyReviewResponse:
    game = _get_game(game_id, db)

    if game.status != "REVIEW":
        raise ValueError(
            "Quarterly review is only available at the end of a quarter."
        )

    if (
        game.career_day < CAREER_DAYS
        or game.career_day % CAREER_DAYS != 0
    ):
        raise ValueError(
            "Quarterly review is not due yet."
        )

    portfolio = _portfolio_metrics(
        game,
        db,
    )

    risk = _risk_assessment(
        game,
        db,
        portfolio,
    )

    level_data = CAREER_LEVELS.get(
        game.career_level,
        CAREER_LEVELS[1],
    )

    target_return = level_data[
        "target_return_pct"
    ]

    risk_violations_count = sum(
        1
        for warning in risk.warnings
        if warning.level in (
            "HIGH",
            "CRITICAL",
        )
    )

    review = CareerEngine.quarterly_review(
        career_level=game.career_level,
        reputation=game.reputation,
        xp=game.xp,
        total_return_pct=portfolio.total_return_pct,
        quarterly_target_return=target_return,
        max_drawdown=portfolio.max_drawdown * 100,
        max_drawdown_limit=level_data[
            "max_drawdown_limit"
        ],
        risk_violations_count=risk_violations_count,
        failure_count=game.career_failure_count,
    )

    game.career_review_count += 1
    game.last_review_result = review.outcome

    game.xp = min(
        99999,
        game.xp + review.xp_awarded,
    )

    game.reputation = max(
        0.0,
        min(
            100.0,
            game.reputation
            + review.reputation_change,
        ),
    )

    if review.outcome == "PROMOTED":
        game.career_level = review.next_level
        game.career_failure_count = 0
        game.career_status = "ACTIVE"

        next_level = CAREER_LEVELS[
            game.career_level
        ]

        game.starting_capital = (
            next_level["starting_capital"]
        )

        game.quarterly_target = (
            next_level["target_capital"]
        )

        game.max_drawdown_limit = (
            next_level["max_drawdown_limit"]
        )

        game.cash += (
            review.capital_injection or 0.0
        )

        total_value = (
            game.cash
            + _compute_invested_value(
                game,
                db,
            )
        )

        game.peak_portfolio_value = total_value
        game.max_drawdown = 0.0
        game.daily_open_portfolio = total_value

        _append_notification(
            game,
            "INFO",
            (
                f"PROMOTION: Level {game.career_level} — "
                f"{review.next_role_title}."
            ),
            "CAREER",
        )

    elif review.outcome == "WARNING":
        game.career_failure_count = (
            review.failure_count
        )
        game.career_status = "WARNING"

        _append_notification(
            game,
            "WARNING",
            (
                "Quarterly warning: performance was below "
                "the required standard. One more failure may "
                "result in demotion or termination."
            ),
            "CAREER",
        )

    elif review.outcome == "FAILED":
        if review.demoted and review.next_level:
            game.career_level = review.next_level
            game.career_failure_count = 0
            game.career_status = "ACTIVE"

            next_level = CAREER_LEVELS[
                game.career_level
            ]

            game.starting_capital = (
                next_level["starting_capital"]
            )

            game.quarterly_target = (
                next_level["target_capital"]
            )

            game.max_drawdown_limit = (
                next_level["max_drawdown_limit"]
            )

            total_value = (
                game.cash
                + _compute_invested_value(
                    game,
                    db,
                )
            )

            game.peak_portfolio_value = total_value
            game.max_drawdown = 0.0
            game.daily_open_portfolio = total_value

            _append_notification(
                game,
                "WARNING",
                (
                    f"DEMOTION: Level {game.career_level} — "
                    f"{review.next_role_title}."
                ),
                "CAREER",
            )

    elif review.outcome == "TERMINATED":
        game.career_failure_count = (
            review.failure_count
        )
        game.career_status = "TERMINATED"
        game.status = "TERMINATED"

        _append_notification(
            game,
            "CRITICAL",
            (
                "TERMINATED: Your employment has ended "
                "after repeated quarterly failure."
            ),
            "CAREER",
        )

    if review.outcome != "TERMINATED":
        game.status = "ACTIVE"

    game.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(game)

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
        can_advance=review.can_advance,
        next_level=review.next_level,
        next_role_title=review.next_role_title,
        capital_injection=review.capital_injection,
        capital_injection_cr=review.capital_injection_cr,
        next_target_return=review.next_target_return,
        next_drawdown_limit=review.next_drawdown_limit,
        next_perks=review.next_perks or [],
    )


def _time_state_from_game(
    game: Game,
) -> TimeState:
    return TimeState(
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


def _compute_invested_value(
    game: Game,
    db: Session,
) -> float:
    stocks = _stocks_map(
        db,
        game.id,
    )

    holdings = _holdings_list(
        db,
        game.id,
    )

    return sum(
        holding.quantity
        * stocks[holding.symbol].current_price
        for holding in holdings
        if holding.symbol in stocks
    )


def _trade_count_today(
    game: Game,
    db: Session,
) -> int:
    return (
        db.query(Transaction)
        .filter(
            Transaction.game_id == game.id,
            Transaction.career_day == game.career_day,
        )
        .count()
    )


def _store_stock_ticks(
    game: Game,
    stocks: list[Stock],
    snapshots: list,
    tick_index: int,
    career_day: int,
    game_hour: int,
    db: Session,
) -> None:
    snapshots_map = {
        snapshot.symbol: snapshot
        for snapshot in snapshots
    }

    for stock in stocks:
        snapshot = snapshots_map.get(
            stock.symbol
        )

        if snapshot is None:
            continue

        db.add(
            StockTick(
                game_id=game.id,
                tick_index=tick_index,
                career_day=career_day,
                game_hour=game_hour,
                symbol=stock.symbol,
                open_price=stock.daily_open,
                high_price=snapshot.daily_high,
                low_price=snapshot.daily_low,
                close_price=snapshot.current_price,
                volume=snapshot.volume,
            )
        )


def _store_market_tick(
    game: Game,
    db: Session,
) -> None:
    db.add(
        MarketTick(
            game_id=game.id,
            tick_index=-1,
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
    )


def _store_market_tick_ex(
    game: Game,
    tick_index: int,
    career_day: int,
    game_hour: int,
    db: Session,
) -> None:
    db.add(
        MarketTick(
            game_id=game.id,
            tick_index=tick_index,
            career_day=career_day,
            game_hour=game_hour,
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
    )


def _failed_trade(
    game: Game,
    symbol: str,
    quantity: int,
    action: str,
    message: str,
    price: float = 0.0,
) -> TradeResult:
    return TradeResult(
        success=False,
        message=message,
        symbol=symbol,
        action=action,
        quantity=quantity,
        price=price,
        total_value=0.0,
        fee=0.0,
        cash_after=game.cash,
        cash_after_cr=round(
            game.cash / CRORE,
            4,
        ),
    )

_build_state_response = build_state_response