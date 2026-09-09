from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from app.simulation.constants import (
    MARKET_OPEN_HOUR,
    MARKET_CLOSE_HOUR,
    WORKING_HOURS,
    CAREER_DAYS,
)


@dataclass
class TimeState:
    game_date: date
    game_hour: int
    career_day: int
    quarter: int
    career_year: int
    market_status: str
    on_leave: bool = False
    leave_balance: int = 60
    leave_used: int = 0

    @property
    def day_of_week(self) -> str:
        return self.game_date.strftime("%A")

    @property
    def is_weekend(self) -> bool:
        return self.game_date.weekday() >= 5

    @property
    def working_day(self) -> bool:
        return not self.is_weekend

    @property
    def is_market_open(self) -> bool:
        return (
            self.working_day
            and MARKET_OPEN_HOUR <= self.game_hour < MARKET_CLOSE_HOUR
        )

    @property
    def is_market_closed(self) -> bool:
        return self.market_status in ("CLOSED", "WEEKEND")

    @property
    def is_on_leave(self) -> bool:
        return self.on_leave


@dataclass
class AdvanceResult:
    new_state: TimeState
    crossed_day_boundary: bool = False
    crossed_weekend: bool = False
    market_was_open: bool = False
    hours_processed: int = 1
    new_career_day: bool = False


class TimeEngine:

    @staticmethod
    def build_initial_state(start_date: Optional[date] = None) -> TimeState:
        if start_date is None:
            start_date = date.today()

        while start_date.weekday() >= 5:
            start_date += timedelta(days=1)

        return TimeState(
            game_date=start_date,
            game_hour=MARKET_OPEN_HOUR,
            career_day=1,
            quarter=1,
            career_year=1,
            market_status=TimeEngine.get_market_status(
                start_date,
                MARKET_OPEN_HOUR,
            ),
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
    def _copy_state(
        state: TimeState,
        *,
        game_date: Optional[date] = None,
        game_hour: Optional[int] = None,
        career_day: Optional[int] = None,
        quarter: Optional[int] = None,
        career_year: Optional[int] = None,
        on_leave: Optional[bool] = None,
        leave_balance: Optional[int] = None,
        leave_used: Optional[int] = None,
    ) -> TimeState:
        new_date = game_date or state.game_date
        new_hour = state.game_hour if game_hour is None else game_hour

        return TimeState(
            game_date=new_date,
            game_hour=new_hour,
            career_day=(
                state.career_day
                if career_day is None
                else career_day
            ),
            quarter=(
                state.quarter
                if quarter is None
                else quarter
            ),
            career_year=(
                state.career_year
                if career_year is None
                else career_year
            ),
            market_status=TimeEngine.get_market_status(
                new_date,
                new_hour,
            ),
            on_leave=(
                state.on_leave
                if on_leave is None
                else on_leave
            ),
            leave_balance=(
                state.leave_balance
                if leave_balance is None
                else leave_balance
            ),
            leave_used=(
                state.leave_used
                if leave_used is None
                else leave_used
            ),
        )

    @staticmethod
    def advance_one_hour(state: TimeState) -> AdvanceResult:
        current_date = state.game_date
        current_hour = state.game_hour

        new_date = current_date
        new_hour = current_hour + 1
        new_career_day = state.career_day

        crossed_day = False
        crossed_weekend = False
        new_career_day = False

        if new_hour < MARKET_CLOSE_HOUR:
            new_state = TimeEngine._copy_state(
                state,
                game_hour=new_hour,
            )

            return AdvanceResult(
                new_state=new_state,
                crossed_day_boundary=False,
                crossed_weekend=False,
                market_was_open=state.is_market_open,
                hours_processed=1,
                new_career_day=False,
            )

        new_date = current_date + timedelta(days=1)

        if new_date.weekday() >= 5:
            crossed_weekend = True

        while new_date.weekday() >= 5:
            new_date += timedelta(days=1)

        new_hour = MARKET_OPEN_HOUR
        new_career_day += 1
        crossed_day = True
        new_career_day = True

        new_quarter = TimeEngine.get_quarter(new_career_day)

        new_year = state.career_year
        if new_quarter < state.quarter:
            new_year += 1

        new_state = TimeEngine._copy_state(
            state,
            game_date=new_date,
            game_hour=new_hour,
            career_day=new_career_day,
            quarter=new_quarter,
            career_year=new_year,
        )

        return AdvanceResult(
            new_state=new_state,
            crossed_day_boundary=crossed_day,
            crossed_weekend=crossed_weekend,
            market_was_open=state.is_market_open,
            hours_processed=1,
            new_career_day=new_career_day,
        )

    @staticmethod
    def advance_hours(state: TimeState, n: int) -> list[AdvanceResult]:
        if n < 0:
            raise ValueError("Hours cannot be negative.")

        results: list[AdvanceResult] = []
        current = state

        for _ in range(n):
            result = TimeEngine.advance_one_hour(current)
            results.append(result)
            current = result.new_state

        return results

    @staticmethod
    def advance_to_market_close(state: TimeState) -> list[AdvanceResult]:
        if state.is_weekend:
            return []

        if state.game_hour >= MARKET_CLOSE_HOUR:
            return []

        hours = MARKET_CLOSE_HOUR - state.game_hour
        return TimeEngine.advance_hours(state, hours)

    @staticmethod
    def advance_to_next_business_day(
        state: TimeState,
    ) -> list[AdvanceResult]:
        results: list[AdvanceResult] = []
        current = state

        if current.is_market_open:
            close_results = TimeEngine.advance_to_market_close(current)
            results.extend(close_results)

            if close_results:
                current = close_results[-1].new_state

        if current.is_weekend:
            return TimeEngine.skip_weekend(current)

        if current.game_hour < MARKET_OPEN_HOUR:
            hours = MARKET_OPEN_HOUR - current.game_hour
            day_results = TimeEngine.advance_hours(current, hours)
            results.extend(day_results)
            return results

        if current.game_hour >= MARKET_CLOSE_HOUR:
            next_date = current.game_date + timedelta(days=1)

            while next_date.weekday() >= 5:
                next_date += timedelta(days=1)

            next_state = TimeEngine._copy_state(
                current,
                game_date=next_date,
                game_hour=MARKET_OPEN_HOUR,
                career_day=current.career_day + 1,
                quarter=TimeEngine.get_quarter(
                    current.career_day + 1
                ),
            )

            results.append(
                AdvanceResult(
                    new_state=next_state,
                    crossed_day_boundary=True,
                    crossed_weekend=current.game_date.weekday() == 4,
                    market_was_open=False,
                    hours_processed=1,
                    new_career_day=True,
                )
            )

        return results

    @staticmethod
    def skip_weekend(state: TimeState) -> list[AdvanceResult]:
        results: list[AdvanceResult] = []
        current = state

        if not current.is_weekend:
            close_results = TimeEngine.advance_to_market_close(current)
            results.extend(close_results)

            if close_results:
                current = close_results[-1].new_state

        next_monday = current.game_date

        while next_monday.weekday() >= 5:
            next_monday += timedelta(days=1)

        if next_monday == current.game_date:
            return results

        target_day = current.career_day

        while current.game_date < next_monday:
            next_date = current.game_date + timedelta(days=1)

            if next_date.weekday() < 5:
                target_day += 1

            is_monday = next_date == next_monday

            next_hour = (
                MARKET_OPEN_HOUR
                if is_monday
                else MARKET_CLOSE_HOUR
            )

            next_state = TimeEngine._copy_state(
                current,
                game_date=next_date,
                game_hour=next_hour,
                career_day=target_day,
                quarter=TimeEngine.get_quarter(target_day),
            )

            result = AdvanceResult(
                new_state=next_state,
                crossed_day_boundary=True,
                crossed_weekend=True,
                market_was_open=False,
                hours_processed=1,
                new_career_day=next_date.weekday() < 5,
            )

            results.append(result)
            current = next_state

        return results

    @staticmethod
    def start_leave(
        state: TimeState,
        days: int,
    ) -> tuple[TimeState, str]:
        if days <= 0:
            return state, "Leave duration must be at least 1 day."

        if state.on_leave:
            return state, "Player is already on leave."

        if days > state.leave_balance:
            return (
                state,
                f"Insufficient leave balance. "
                f"You have {state.leave_balance} days remaining.",
            )

        new_state = TimeEngine._copy_state(
            state,
            on_leave=True,
        )

        return new_state, ""

    @staticmethod
    def end_leave(state: TimeState) -> TimeState:
        if not state.on_leave:
            return state

        return TimeEngine._copy_state(
            state,
            on_leave=False,
        )

    @staticmethod
    def take_leave(
        state: TimeState,
        days: int,
    ) -> tuple[list[AdvanceResult], str]:
        new_state, error = TimeEngine.start_leave(state, days)

        if error:
            return [], error

        results: list[AdvanceResult] = []
        current = new_state

        for _ in range(days):
            day_results = TimeEngine.advance_to_next_business_day(
                current
            )

            if not day_results:
                break

            results.extend(day_results)
            current = day_results[-1].new_state

        if not results:
            return [], "Unable to advance the game calendar."

        final_state = TimeEngine._copy_state(
            current,
            on_leave=False,
            leave_balance=state.leave_balance - days,
            leave_used=state.leave_used + days,
        )

        results[-1].new_state = final_state

        return results, ""

    @staticmethod
    def get_quarter(career_day: int) -> int:
        if career_day <= 0:
            return 1

        return min(
            3,
            ((career_day - 1) // 30) + 1,
        )

    @staticmethod
    def tick_index(
        career_day: int,
        game_hour: int,
    ) -> int:
        if career_day <= 0:
            return 0

        if game_hour < MARKET_OPEN_HOUR:
            hour_offset = 0
        else:
            hour_offset = min(
                game_hour - MARKET_OPEN_HOUR,
                len(WORKING_HOURS) - 1,
            )

        return (
            (career_day - 1) * len(WORKING_HOURS)
            + hour_offset
        )