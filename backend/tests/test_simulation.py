import pytest
from datetime import date, timedelta
import numpy as np

from app.simulation.time_engine import TimeEngine, TimeState, AdvanceResult
from app.simulation.market_engine import MarketEngine, StockSnapshot, MarketTickResult
from app.simulation.constants import (
    MARKET_OPEN_HOUR,
    MARKET_CLOSE_HOUR,
    WORKING_HOURS,
    CAREER_DAYS,
    DAYS_PER_QUARTER,
    CAREER_LEVELS,
    STOCK_UNIVERSE,
    REGIME_PARAMS,
)
from app.simulation.game_director import GameDirector
from app.simulation.risk_engine import RiskEngine
from app.simulation.portfolio_engine import PortfolioEngine
from app.simulation.career_engine import CareerEngine


class TestTimeEngine:

    def test_build_initial_state(self):
        state = TimeEngine.build_initial_state()
        assert state.game_hour == MARKET_OPEN_HOUR
        assert state.career_day == 1
        assert state.quarter == 1
        assert state.career_year == 1
        assert state.market_status == "OPEN"
        assert state.on_leave is False
        assert state.leave_balance == 60
        assert state.is_weekend is False

    def test_build_initial_state_skips_weekend(self):
        start = date(2026, 9, 13)  # Sunday
        state = TimeEngine.build_initial_state(start_date=start)
        assert state.game_date == date(2026, 9, 14)  # Monday
        assert state.is_weekend is False

    @pytest.mark.parametrize("hour", list(range(9, 17)))
    def test_tick_index_working_hours_never_negative(self, hour):
        idx = TimeEngine.tick_index(1, hour)
        assert idx >= 0, f"tick_index for hour {hour} was negative"

    def test_tick_index_pre_market_never_negative(self):
        for day in range(1, 5):
            idx = TimeEngine.tick_index(day, 8)
            assert idx >= 0, f"Pre-market tick_index negative for day {day}"

    def test_tick_index_close_hour(self):
        idx = TimeEngine.tick_index(1, 17)
        assert idx == len(WORKING_HOURS)

    def test_tick_index_zero_for_first_day_pre_market(self):
        idx = TimeEngine.tick_index(1, 8)
        assert idx == 0

    def test_advance_one_hour_within_day(self):
        state = TimeEngine.build_initial_state()
        result = TimeEngine.advance_one_hour(state)
        assert result.crossed_day_boundary is False
        assert result.new_career_day is False
        assert result.new_state.game_hour == 10
        assert result.hours_processed == 1

    def test_advance_one_hour_to_close(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date.today(),
            game_hour=16,
            career_day=1,
        )
        result = TimeEngine.advance_one_hour(state)
        assert result.crossed_day_boundary is False
        assert result.new_career_day is False
        assert result.new_state.game_hour == 17

    def test_advance_one_hour_from_close_to_next_day(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date.today(),
            game_hour=17,
            career_day=1,
        )
        result = TimeEngine.advance_one_hour(state)
        assert result.crossed_day_boundary is True
        assert result.new_career_day is True
        assert result.new_state.game_hour == MARKET_OPEN_HOUR

    def test_advance_one_hour_to_next_day(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date.today(),
            game_hour=17,
            career_day=1,
        )
        result = TimeEngine.advance_one_hour(state)
        assert result.crossed_day_boundary is True
        assert result.new_career_day is True
        assert result.new_state.game_hour == MARKET_OPEN_HOUR
        assert result.new_state.career_day == 2

    def test_advance_to_next_business_day_from_premarket(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date(2026, 9, 14),  # Monday
            game_hour=8,
            career_day=1,
        )
        results = TimeEngine.advance_to_next_business_day(state)
        assert len(results) > 0, "advance_to_next_business_day returned empty for PRE_MARKET weekday"
        final = results[-1].new_state
        assert final.game_hour == MARKET_OPEN_HOUR
        assert final.career_day == 2

    def test_advance_to_next_business_day_from_open(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date(2026, 9, 14),  # Monday
            game_hour=MARKET_OPEN_HOUR,
            career_day=1,
        )
        results = TimeEngine.advance_to_next_business_day(state)
        assert len(results) > 0
        final = results[-1].new_state
        assert final.game_hour == MARKET_OPEN_HOUR
        assert final.career_day == 2

    def test_advance_to_next_business_day_from_weekend(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date(2026, 9, 13),  # Sunday
            game_hour=MARKET_CLOSE_HOUR,
            career_day=1,
        )
        results = TimeEngine.advance_to_next_business_day(state)
        assert len(results) > 0
        final = results[-1].new_state
        assert final.is_weekend is False
        assert final.game_hour == MARKET_OPEN_HOUR

    def test_skip_weekend_from_friday(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date(2026, 9, 11),  # Friday
            game_hour=MARKET_CLOSE_HOUR,
            career_day=1,
        )
        results = TimeEngine.skip_weekend(state)
        assert len(results) > 0
        final = results[-1].new_state
        assert final.game_date.weekday() == 0  # Monday
        assert final.game_hour == MARKET_OPEN_HOUR

    def test_skip_weekend_from_saturday(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date(2026, 9, 12),  # Saturday
            game_hour=MARKET_CLOSE_HOUR,
            career_day=1,
        )
        results = TimeEngine.skip_weekend(state)
        assert len(results) > 0
        final = results[-1].new_state
        assert final.game_date.weekday() == 0  # Monday

    def test_skip_weekend_from_sunday(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date(2026, 9, 13),  # Sunday
            game_hour=MARKET_CLOSE_HOUR,
            career_day=1,
        )
        results = TimeEngine.skip_weekend(state)
        assert len(results) > 0
        final = results[-1].new_state
        assert final.game_date.weekday() == 0

    def test_start_leave(self):
        state = TimeEngine.build_initial_state()
        new_state, error = TimeEngine.start_leave(state)
        assert error == ""
        assert new_state.on_leave is True
        assert new_state.leave_balance == 60

    def test_start_leave_insufficient_balance(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date.today(),
            game_hour=10,
            career_day=1,
            leave_balance=0,
        )
        _, error = TimeEngine.start_leave(state)
        assert "No paid leave" in error

    def test_end_leave(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date.today(),
            game_hour=10,
            career_day=1,
            on_leave=True,
        )
        new_state = TimeEngine.end_leave(state)
        assert new_state.on_leave is False

    def test_take_leave(self):
        state = TimeEngine.build_initial_state()
        results, error = TimeEngine.take_leave(state, 2)
        assert error == ""
        assert len(results) > 0
        final = results[-1].new_state
        assert final.leave_balance == 58
        assert final.leave_used == 2

    def test_take_leave_insufficient(self):
        state = TimeEngine._make_state(
            state=TimeEngine.build_initial_state(),
            game_date=date.today(),
            game_hour=10,
            career_day=1,
            leave_balance=1,
        )
        _, error = TimeEngine.take_leave(state, 5)
        assert "Insufficient leave" in error

    def test_is_quarter_complete(self):
        assert TimeEngine.is_quarter_complete(90) is True
        assert TimeEngine.is_quarter_complete(91) is False
        assert TimeEngine.is_quarter_complete(180) is True

    def test_get_quarter_from_career_day(self):
        assert TimeEngine.get_quarter(1) == 1
        assert TimeEngine.get_quarter(90) == 1
        assert TimeEngine.get_quarter(91) == 2

    def test_get_career_year(self):
        assert TimeEngine.get_career_year(1) == 1
        assert TimeEngine.get_career_year(361) == 2


class TestMarketEngine:

    def _make_game_state(self):
        class FakeGame:
            def __init__(self):
                self.market_regime = "STABLE"
                self.nifty_value = 24500.0
                self.sensex_value = 80500.0
                self.bank_nifty_value = 51000.0
                self.india_vix_value = 14.5
                self.usdinr_value = 83.5
                self.gold_value = 72000.0
                self.nasdaq_value = 17500.0
                self.sp500_value = 5450.0

        return FakeGame()

    def test_simulate_tick_returns_result(self):
        rng = np.random.default_rng(42)
        stocks = [
            StockSnapshot(
                symbol="APXT", name="Test", sector="Technology",
                current_price=100.0, previous_price=100.0, daily_open=100.0,
                daily_high=100.0, daily_low=100.0, volume=0, daily_return=0.0,
                volatility=0.02, beta=1.0, sentiment=0.5, momentum=0.0,
                growth=0.10, profitability=0.10, debt=0.30, valuation=0.50,
                market_sensitivity=1.0, event_sensitivity=0.5, institutional_pressure=0.0,
            )
        ]
        result = MarketEngine.simulate_tick(
            stocks=stocks, game=self._make_game_state(), rng=rng
        )
        assert isinstance(result, MarketTickResult)
        assert len(result.updated_stocks) == 1
        assert result.nifty > 0
        assert result.sensex > 0

    def test_regime_transition_uses_probabilities(self):
        rng = np.random.default_rng(42)
        game = self._make_game_state()
        game.market_regime = "STABLE"
        params = REGIME_PARAMS["STABLE"]
        results = {}
        for _ in range(5000):
            regime, changed, _ = MarketEngine._transition_regime(game, params, rng)
            results[regime] = results.get(regime, 0) + 1

        total_changes = sum(1 for r in results if r != "STABLE")
        stable_pct = results.get("STABLE", 0) / 5000

        assert stable_pct > 0.4, f"STABLE should be ~60% but got {stable_pct:.2%}"
        assert results.get("BULL", 0) > 0, "BULL transitions should occur (~20%)"
        assert results.get("VOLATILE", 0) > 0, "VOLATILE transitions should occur (~15%)"

    def test_regime_change_detection(self):
        rng = np.random.default_rng(12345)
        game = self._make_game_state()
        game.market_regime = "STABLE"
        params = REGIME_PARAMS["STABLE"]

        changed_count = 0
        for _ in range(5000):
            _, changed, new_regime = MarketEngine._transition_regime(game, params, rng)
            if changed:
                changed_count += 1
                assert new_regime != "STABLE" or new_regime is None

        assert changed_count > 0, "At least some regime changes should occur"
        assert changed_count < 3000, "Not all ticks should change regime"

    def test_reset_daily_ohlc(self):
        stocks = [
            StockSnapshot(
                symbol="APXT", name="Test", sector="Technology",
                current_price=150.0, previous_price=148.0, daily_open=145.0,
                daily_high=155.0, daily_low=140.0, volume=1000, daily_return=0.0,
                volatility=0.02, beta=1.0, sentiment=0.5, momentum=0.0,
                growth=0.10, profitability=0.10, debt=0.30, valuation=0.50,
                market_sensitivity=1.0, event_sensitivity=0.5, institutional_pressure=0.0,
            )
        ]
        result = MarketEngine.reset_daily_ohlc(stocks)
        assert result[0].daily_open == 150.0
        assert result[0].daily_high == 150.0
        assert result[0].daily_low == 150.0
        assert result[0].volume == 0


class TestPortfolioEngine:

    def test_fee_for_trade(self):
        assert PortfolioEngine.fee_for_trade(100000) == 100.0
        assert PortfolioEngine.fee_for_trade(0) == 0.0
        assert PortfolioEngine.fee_for_trade(-100) == 0.0

    def test_validate_buy_sufficient_cash(self):
        stocks = {
            "APXT": type("S", (), {"current_price": 100.0, "name": "Test"})(),
        }
        valid, msg = PortfolioEngine.validate_buy(
            cash=10000.0, symbol="APXT", quantity=50, price=100.0, stocks_map=stocks
        )
        assert valid is True
        assert msg == "BUY validated."

    def test_validate_buy_insufficient_cash(self):
        stocks = {
            "APXT": type("S", (), {"current_price": 1000.0, "name": "Test"})(),
        }
        valid, msg = PortfolioEngine.validate_buy(
            cash=100.0, symbol="APXT", quantity=50, price=1000.0, stocks_map=stocks
        )
        assert valid is False
        assert "Insufficient cash" in msg

    def test_validate_buy_bad_quantity(self):
        valid, msg = PortfolioEngine.validate_buy(
            cash=100000.0, symbol="APXT", quantity=0, price=100.0, stocks_map={}
        )
        assert valid is False

    def test_validate_sell_holding_found(self):
        class Holding:
            symbol = "APXT"
            quantity = 100
        valid, msg, available = PortfolioEngine.validate_sell(
            holdings_db=[Holding()], symbol="APXT", quantity=50
        )
        assert valid is True
        assert available == 100

    def test_validate_sell_no_holding(self):
        valid, msg, available = PortfolioEngine.validate_sell(
            holdings_db=[], symbol="APXT", quantity=50
        )
        assert valid is False
        assert available == 0


class TestCareerEngine:

    def test_update_per_tick_positive_return(self):
        update = CareerEngine.update_per_tick(
            career_level=1, xp=0, reputation=50.0,
            total_return_pct=5.0, risk_assessment=None, target_progress=0.5,
        )
        assert update.xp_gained > 0

    def test_update_per_tick_negative_return(self):
        update = CareerEngine.update_per_tick(
            career_level=1, xp=0, reputation=50.0,
            total_return_pct=-60.0, risk_assessment=None, target_progress=0.1,
        )
        assert update.reputation_change < 0

    def test_quarterly_review_pass(self):
        result = CareerEngine.quarterly_review(
            career_level=1, reputation=50.0, xp=1000,
            total_return_pct=15.0, quarterly_target_return=12.0,
            max_drawdown=3.0, max_drawdown_limit=0.10,
            risk_violations_count=0, failure_count=0,
        )
        assert result.outcome == "PROMOTED"
        assert result.next_level == 2

    def test_quarterly_review_warning(self):
        result = CareerEngine.quarterly_review(
            career_level=1, reputation=50.0, xp=1000,
            total_return_pct=8.0, quarterly_target_return=12.0,
            max_drawdown=5.0, max_drawdown_limit=0.10,
            risk_violations_count=0, failure_count=0,
        )
        assert result.outcome == "WARNING"

    def test_quarterly_review_terminate_at_level1(self):
        result = CareerEngine.quarterly_review(
            career_level=1, reputation=10.0, xp=1000,
            total_return_pct=-20.0, quarterly_target_return=12.0,
            max_drawdown=50.0, max_drawdown_limit=0.10,
            risk_violations_count=2, failure_count=1,
        )
        assert result.outcome == "TERMINATED"

    def test_quarterly_review_demote(self):
        result = CareerEngine.quarterly_review(
            career_level=2, reputation=10.0, xp=1000,
            total_return_pct=-20.0, quarterly_target_return=15.0,
            max_drawdown=50.0, max_drawdown_limit=0.085,
            risk_violations_count=2, failure_count=1,
        )
        assert result.outcome == "FAILED"
        assert result.demoted is True
        assert result.next_level == 1

    def test_get_role_title(self):
        assert CareerEngine.get_role_title(1) == CAREER_LEVELS[1]["title"]
        assert CareerEngine.get_role_title(5) == CAREER_LEVELS[5]["title"]


class TestGameDirector:

    def test_evaluate_conservative(self):
        rng = np.random.default_rng(42)
        state = GameDirector.evaluate(
            career_day=30, target_progress=0.1, reputation=50.0,
            cash_ratio=0.8, trade_count_today=0, max_drawdown=0.0,
            market_regime="STABLE", portfolio_volatility=0.1, rng=rng,
        )
        assert state.player_risk_profile == "CONSERVATIVE"

    def test_evaluate_aggressive(self):
        rng = np.random.default_rng(42)
        state = GameDirector.evaluate(
            career_day=30, target_progress=0.5, reputation=50.0,
            cash_ratio=0.3, trade_count_today=0, max_drawdown=0.0,
            market_regime="STABLE", portfolio_volatility=0.1, rng=rng,
        )
        assert state.player_risk_profile == "AGGRESSIVE"

    def test_evaluate_speculative(self):
        rng = np.random.default_rng(42)
        state = GameDirector.evaluate(
            career_day=30, target_progress=0.5, reputation=50.0,
            cash_ratio=0.3, trade_count_today=0, max_drawdown=0.0,
            market_regime="STABLE", portfolio_volatility=0.3, rng=rng,
        )
        assert state.player_risk_profile == "SPECULATIVE"


class TestRiskEngine:

    def test_assess_low_risk(self):
        assessment = RiskEngine.assess(
            total_value=1000000.0, cash=900000.0,
            holdings_detail=[], sector_exposure={},
            max_drawdown=0.0, portfolio_volatility=0.05,
            market_regime="STABLE", max_drawdown_limit=0.10,
        )
        assert assessment.overall_level == "LOW"

    def test_assess_drawdown_breach(self):
        assessment = RiskEngine.assess(
            total_value=1000000.0, cash=100000.0,
            holdings_detail=[], sector_exposure={},
            max_drawdown=0.15, portfolio_volatility=0.05,
            market_regime="STABLE", max_drawdown_limit=0.10,
        )
        assert any(w.code == "DRAWDOWN_BREACH" for w in assessment.warnings)

    def test_assess_concentration(self):
        holdings = [{"symbol": "APXT", "market_value": 500000.0}]
        assessment = RiskEngine.assess(
            total_value=1000000.0, cash=500000.0,
            holdings_detail=holdings, sector_exposure={"Technology": 0.5},
            max_drawdown=0.0, portfolio_volatility=0.05,
            market_regime="STABLE", max_drawdown_limit=0.10,
        )
        assert any(w.code == "SINGLE_STOCK_CONCENTRATION" for w in assessment.warnings)
