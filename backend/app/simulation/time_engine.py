"""
TimeEngine — authoritative game clock for Investment Banker Mode.
Manages simulated date, hour, market status, weekends, and career tracking.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from app.simulation.constants import (
    MARKET_OPEN_HOUR, MARKET_CLOSE_HOUR, WORKING_HOURS, CAREER_DAYS
)


@dataclass
class TimeState:
    game_date: date
    game_hour: int           # 9–16 (market hours), 17 = closed
    career_day: int          # 1–90
    quarter: int             # 1
    career_year: int         # 1
    market_status: str       # PRE_MARKET, OPEN, CLOSED, WEEKEND
    on_leave: bool = False
    leave_balance: int = 60
    leave_used: int = 0

    @property
    def day_of_week(self) -> str:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[self.game_date.weekday()]

    @property
    def is_weekend(self) -> bool:
        return self.game_date.weekday() >= 5

    @property
    def is_market_open(self) -> bool:
        return (
            not self.is_weekend
            and MARKET_OPEN_HOUR <= self.game_hour < MARKET_CLOSE_HOUR
        )


@dataclass
class AdvanceResult:
    new_state: TimeState
    crossed_day_boundary: bool = False
    crossed_weekend: bool = False
    market_was_open: bool = False
    hours_processed: int = 1
    new_career_day: bool = False


class TimeEngine:
    """
    Stateless engine — takes a TimeState, returns a new TimeState.
    The caller is responsible for persisting state.
    """

    @staticmethod
    def build_initial_state(start_date: Optional[date] = None) -> TimeState:
        """Create initial time state starting on a Monday at 09:00."""
        if start_date is None:
            # Start on the next Monday from today
            today = date.today()
            days_ahead = (7 - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 0
            start_date = today + timedelta(days=days_ahead)
            # Ensure it's a Monday
            while start_date.weekday() != 0:
                start_date += timedelta(days=1)

        return TimeState(
            game_date=start_date,
            game_hour=MARKET_OPEN_HOUR,
            career_day=1,
            quarter=1,
            career_year=1,
            market_status="OPEN",
            on_leave=False,
            leave_balance=60,
            leave_used=0,
        )

    @staticmethod
    def get_market_status(game_date: date, game_hour: int) -> str:
        if game_date.weekday() >= 5:
            return "WEEKEND"
        if game_hour < MARKET_OPEN_HOUR:
            return "PRE_MARKET"
        if MARKET_OPEN_HOUR <= game_hour < MARKET_CLOSE_HOUR:
            return "OPEN"
        return "CLOSED"

    @staticmethod
    def advance_one_hour(state: TimeState) -> AdvanceResult:
        """Advance game time by exactly one hour."""
        new_hour = state.game_hour + 1
        new_date = state.game_date
        new_career_day = state.career_day
        crossed_day = False
        crossed_weekend = False
        new_career_day_flag = False

        if new_hour >= MARKET_CLOSE_HOUR:
            # Move to next business day at market open
            new_date = state.game_date + timedelta(days=1)
            # Skip weekends
            while new_date.weekday() >= 5:
                crossed_weekend = True
                new_date += timedelta(days=1)
            new_hour = MARKET_OPEN_HOUR
            new_career_day = state.career_day + 1
            crossed_day = True
            new_career_day_flag = True

        new_status = TimeEngine.get_market_status(new_date, new_hour)

        new_state = TimeState(
            game_date=new_date,
            game_hour=new_hour,
            career_day=new_career_day,
            quarter=state.quarter,
            career_year=state.career_year,
            market_status=new_status,
            on_leave=state.on_leave,
            leave_balance=state.leave_balance,
            leave_used=state.leave_used,
        )

        return AdvanceResult(
            new_state=new_state,
            crossed_day_boundary=crossed_day,
            crossed_weekend=crossed_weekend,
            market_was_open=state.is_market_open,
            hours_processed=1,
            new_career_day=new_career_day_flag,
        )

    @staticmethod
    def advance_hours(state: TimeState, n: int) -> list[AdvanceResult]:
        """Advance by n hours, returning each step's result."""
        results = []
        current = state
        for _ in range(n):
            result = TimeEngine.advance_one_hour(current)
            results.append(result)
            current = result.new_state
        return results

    @staticmethod
    def advance_to_market_close(state: TimeState) -> list[AdvanceResult]:
        """Advance to 17:00 (market close)."""
        if state.is_weekend or state.game_hour >= MARKET_CLOSE_HOUR:
            return []
        hours_remaining = MARKET_CLOSE_HOUR - state.game_hour
        return TimeEngine.advance_hours(state, hours_remaining)

    @staticmethod
    def advance_to_next_business_day(state: TimeState) -> list[AdvanceResult]:
        """Advance to the next business day's market open (09:00)."""
        # First close the current day if market is open
        results = []
        current = state
        if current.is_market_open:
            close_results = TimeEngine.advance_to_market_close(current)
            results.extend(close_results)
            if close_results:
                current = close_results[-1].new_state

        # Now advance to next day
        result = TimeEngine.advance_one_hour(current)
        results.append(result)
        return results

    @staticmethod
    def skip_weekend(state: TimeState) -> list[AdvanceResult]:
        """Skip to Monday market open. Only valid on Friday after close or weekend."""
        results = []
        current = state

        # First advance past Friday if we're still in market hours
        if not state.is_weekend:
            close_results = TimeEngine.advance_to_market_close(current)
            results.extend(close_results)
            if close_results:
                current = close_results[-1].new_state

        # Now skip to Monday
        while current.is_weekend or current.game_date.weekday() == 0 and current.game_hour < MARKET_OPEN_HOUR:
            result = TimeEngine.advance_one_hour(current)
            results.append(result)
            current = result.new_state
            if not current.is_weekend and current.game_hour == MARKET_OPEN_HOUR:
                break

        return results

    @staticmethod
    def take_leave(state: TimeState, days: int) -> tuple[list[AdvanceResult], str]:
        """Take N days of paid leave. Returns results and error message if invalid."""
        if days <= 0:
            return [], "Leave duration must be at least 1 day."
        if days > state.leave_balance:
            return [], f"Insufficient leave balance. You have {state.leave_balance} days remaining."

        results = []
        current = state

        for _ in range(days):
            # Advance to next business day
            day_results = TimeEngine.advance_to_next_business_day(current)
            results.extend(day_results)
            if day_results:
                current = day_results[-1].new_state

        # Update leave tracking
        if results:
            final_state = results[-1].new_state
            final_state.leave_used = state.leave_used + days
            final_state.leave_balance = state.leave_balance - days
            results[-1].new_state = final_state

        return results, ""

    @staticmethod
    def get_quarter(career_day: int) -> int:
        return ((career_day - 1) // 30) + 1

    @staticmethod
    def tick_index(career_day: int, game_hour: int) -> int:
        """Convert career day + hour to a unique tick index."""
        hour_offset = game_hour - MARKET_OPEN_HOUR
        return (career_day - 1) * len(WORKING_HOURS) + max(0, hour_offset)
