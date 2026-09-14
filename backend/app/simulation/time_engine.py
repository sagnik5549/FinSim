from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from app.simulation.constants import (
    MARKET_OPEN_HOUR,
    MARKET_CLOSE_HOUR,
    WORKING_HOURS,
    CAREER_DAYS,
    DAYS_PER_QUARTER,
    PAID_LEAVE_PER_YEAR,
    get_career_year,
    get_quarter_from_career_day,
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
    leave_balance: int = PAID_LEAVE_PER_YEAR
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
            and self.game_hour in WORKING_HOURS
        )

    @property
    def is_market_closed(self) -> bool:
        return not self.is_market_open


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
    def build_initial_state(
        start_date: Optional[date] = None,
    ) -> TimeState:
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
            market_status="OPEN",
            on_leave=False,
            leave_balance=PAID_LEAVE_PER_YEAR,
            leave_used=0,
        )

    @staticmethod
    def get_market_status(
        game_date: date,
        game_hour: int,
    ) -> str:
        if game_date.weekday() >= 5:
            return "WEEKEND"

        if game_hour < MARKET_OPEN_HOUR:
            return "PRE_MARKET"

        if game_hour >= MARKET_CLOSE_HOUR:
            return "CLOSED"

        return "OPEN"

    @staticmethod
    def _make_state(
        state: TimeState,
        game_date: date,
        game_hour: int,
        career_day: int,
        on_leave: Optional[bool] = None,
        leave_balance: Optional[int] = None,
        leave_used: Optional[int] = None,
    ) -> TimeState:
        return TimeState(
            game_date=game_date,
            game_hour=game_hour,
            career_day=career_day,
            quarter=get_quarter_from_career_day(career_day),
            career_year=get_career_year(career_day),
            market_status=TimeEngine.get_market_status(
                game_date,
                game_hour,
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
    def advance_one_hour(
        state: TimeState,
    ) -> AdvanceResult:
        old_date = state.game_date
        old_hour = state.game_hour

        market_was_open = state.is_market_open

        if old_hour < MARKET_CLOSE_HOUR:
            new_hour = old_hour + 1

            new_state = TimeEngine._make_state(
                state=state,
                game_date=old_date,
                game_hour=new_hour,
                career_day=state.career_day,
            )

            return AdvanceResult(
                new_state=new_state,
                crossed_day_boundary=False,
                crossed_weekend=False,
                market_was_open=market_was_open,
                hours_processed=1,
                new_career_day=False,
            )

        next_date = old_date + timedelta(days=1)

        if next_date.weekday() >= 5:
            new_state = TimeEngine._make_state(
                state=state,
                game_date=next_date,
                game_hour=MARKET_CLOSE_HOUR,
                career_day=state.career_day,
            )

            return AdvanceResult(
                new_state=new_state,
                crossed_day_boundary=True,
                crossed_weekend=True,
                market_was_open=market_was_open,
                hours_processed=1,
                new_career_day=False,
            )

        new_career_day = state.career_day + 1

        new_state = TimeEngine._make_state(
            state=state,
            game_date=next_date,
            game_hour=MARKET_OPEN_HOUR,
            career_day=new_career_day,
        )

        return AdvanceResult(
            new_state=new_state,
            crossed_day_boundary=True,
            crossed_weekend=False,
            market_was_open=market_was_open,
            hours_processed=1,
            new_career_day=True,
        )

    @staticmethod
    def advance_hours(
        state: TimeState,
        hours: int,
    ) -> list[AdvanceResult]:
        if hours < 0:
            raise ValueError("Hours cannot be negative.")

        results: list[AdvanceResult] = []
        current = state

        for _ in range(hours):
            result = TimeEngine.advance_one_hour(current)
            results.append(result)
            current = result.new_state

        return results

    @staticmethod
    def advance_to_market_close(
        state: TimeState,
    ) -> list[AdvanceResult]:
        if state.is_weekend:
            return []

        if state.game_hour >= MARKET_CLOSE_HOUR:
            return []

        hours = MARKET_CLOSE_HOUR - state.game_hour

        return TimeEngine.advance_hours(
            state,
            hours,
        )

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

        while True:
            if (
                not current.is_weekend
                and current.game_hour >= MARKET_CLOSE_HOUR
            ):
                result = TimeEngine.advance_one_hour(current)
                results.append(result)
                current = result.new_state

            elif current.is_weekend:
                result = TimeEngine.advance_one_hour(current)
                results.append(result)
                current = result.new_state

            else:
                break

            if (
                not current.is_weekend
                and current.game_hour == MARKET_OPEN_HOUR
            ):
                break

        if (
            not results
            and not current.is_weekend
            and current.game_hour < MARKET_CLOSE_HOUR
        ):
            next_day_date = current.game_date + timedelta(days=1)
            while next_day_date.weekday() >= 5:
                next_day_date += timedelta(days=1)

            result = TimeEngine._make_state(
                state=current,
                game_date=next_day_date,
                game_hour=MARKET_OPEN_HOUR,
                career_day=current.career_day + 1,
            )
            results.append(
                AdvanceResult(
                    new_state=result,
                    crossed_day_boundary=True,
                    crossed_weekend=next_day_date.weekday() >= 5,
                    market_was_open=current.is_market_open,
                    hours_processed=1,
                    new_career_day=True,
                )
            )

        return results

    @staticmethod
    def skip_weekend(
        state: TimeState,
    ) -> list[AdvanceResult]:
        results: list[AdvanceResult] = []
        current = state

        if not current.is_weekend:
            close_results = TimeEngine.advance_to_market_close(current)
            results.extend(close_results)

            if close_results:
                current = close_results[-1].new_state

        while True:
            if not current.is_weekend:
                if (
                    current.game_date.weekday() == 0
                    and current.game_hour == MARKET_OPEN_HOUR
                ):
                    break

                result = TimeEngine.advance_one_hour(current)
                results.append(result)
                current = result.new_state
                continue

            result = TimeEngine.advance_one_hour(current)
            results.append(result)
            current = result.new_state

            if (
                not current.is_weekend
                and current.game_hour == MARKET_OPEN_HOUR
            ):
                break

        return results

    @staticmethod
    def start_leave(
        state: TimeState,
    ) -> tuple[TimeState, str]:
        if state.on_leave:
            return state, "Player is already on leave."

        if state.leave_balance <= 0:
            return state, "No paid leave remaining."

        new_state = TimeEngine._make_state(
            state=state,
            game_date=state.game_date,
            game_hour=state.game_hour,
            career_day=state.career_day,
            on_leave=True,
        )

        return new_state, ""

    @staticmethod
    def end_leave(
        state: TimeState,
    ) -> TimeState:
        return TimeEngine._make_state(
            state=state,
            game_date=state.game_date,
            game_hour=state.game_hour,
            career_day=state.career_day,
            on_leave=False,
        )

    @staticmethod
    def take_leave(
        state: TimeState,
        days: int,
    ) -> tuple[list[AdvanceResult], str]:
        if days <= 0:
            return [], "Leave duration must be at least 1 day."

        if state.on_leave:
            return [], "Player is already on leave."

        if days > state.leave_balance:
            return (
                [],
                f"Insufficient leave balance. "
                f"You have {state.leave_balance} days remaining.",
            )

        results: list[AdvanceResult] = []

        current = TimeEngine._make_state(
            state=state,
            game_date=state.game_date,
            game_hour=state.game_hour,
            career_day=state.career_day,
            on_leave=True,
        )

        for _ in range(days):
            day_results = TimeEngine.advance_to_next_business_day(
                current
            )

            if not day_results:
                return [], "Unable to advance leave period."

            results.extend(day_results)
            current = day_results[-1].new_state

        final_state = TimeEngine._make_state(
            state=current,
            game_date=current.game_date,
            game_hour=current.game_hour,
            career_day=current.career_day,
            on_leave=False,
            leave_balance=state.leave_balance - days,
            leave_used=state.leave_used + days,
        )

        results[-1].new_state = final_state

        return results, ""

    @staticmethod
    def get_quarter(
        career_day: int,
    ) -> int:
        return get_quarter_from_career_day(career_day)

    @staticmethod
    def get_career_year(
        career_day: int,
    ) -> int:
        return get_career_year(career_day)

    @staticmethod
    def tick_index(
        career_day: int,
        game_hour: int,
    ) -> int:
        if career_day < 1:
            raise ValueError("Career day must be at least 1.")

        if game_hour < MARKET_OPEN_HOUR:
            return (
                (career_day - 1) * len(WORKING_HOURS)
            )

        if game_hour >= MARKET_CLOSE_HOUR:
            return (
                (career_day - 1) * len(WORKING_HOURS)
                + len(WORKING_HOURS)
            )

        hour_offset = game_hour - MARKET_OPEN_HOUR

        return (
            (career_day - 1) * len(WORKING_HOURS)
            + hour_offset
        )

    @staticmethod
    def is_quarter_complete(
        career_day: int,
    ) -> bool:
        return (
            career_day >= CAREER_DAYS
            and career_day % DAYS_PER_QUARTER == 0
        )