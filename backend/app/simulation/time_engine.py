"""
TimeEngine — the single authority over the game calendar.

Every other system only ever sees time move through the hooks invoked here, so
skipping time can never bypass the simulation: an N-hour skip is literally N
individually simulated market hours, a weekend skip simulates both weekend days
and the overnight gap, and leave runs whole business days of simulation.

Calendar rules
  * Business days are Monday-Friday. The market is open 09:00-17:00.
  * One working hour == one game hour.
  * When the clock sits at 17:00 the market is CLOSED; the next hour step rolls
    the calendar to 09:00 on the next business day (processing the overnight
    session and any weekend days in between).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

from app.simulation.constants import (
    CAREER_YEAR_DAYS,
    MARKET_CLOSE_HOUR,
    MARKET_OPEN_HOUR,
    QUARTER_DAYS,
)
from app.simulation.state import GameState


class TimeHooks(Protocol):
    def on_market_hour(self, start: datetime, end: datetime) -> None: ...
    def on_market_close(self, day: date) -> None: ...
    def on_non_business_day(self, day: date) -> None: ...
    def on_overnight(self, from_day: date, to_day: date) -> None: ...
    def on_market_open(self, day: date) -> None: ...
    def quarter_should_end(self, next_business_day: date) -> bool: ...
    def on_quarter_end(self) -> None: ...
    def can_advance(self) -> bool: ...


class TimeError(Exception):
    pass


def is_business_day(d: date) -> bool:
    return d.weekday() < 5


def next_business_day(d: date) -> date:
    n = d + timedelta(days=1)
    while not is_business_day(n):
        n += timedelta(days=1)
    return n


def business_days_between(a: date, b: date) -> int:
    """Business days in the half-open interval (a, b]."""
    count, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if is_business_day(d):
            count += 1
    return count


def market_status(now: datetime, on_leave: bool = False) -> str:
    if not is_business_day(now.date()):
        return "WEEKEND"
    if now.hour < MARKET_OPEN_HOUR:
        return "PRE_MARKET"
    if now.hour < MARKET_CLOSE_HOUR:
        return "OPEN"
    return "CLOSED"


@dataclass
class ClockView:
    game_date: str
    game_hour: int
    game_minute: int
    day_of_week: str
    market_status: str
    career_day: int
    quarter_day: int
    quarter_days: int
    quarter: int
    career_year: int
    working_day: bool
    is_on_leave: bool
    hours_to_close: int


def clock_view(state: GameState) -> ClockView:
    now = state.now
    career_day = (now.date() - state.start_time.date()).days + 1
    quarter_day = (now.date() - state.career.quarter_start.date()).days + 1
    status = market_status(now)
    return ClockView(
        game_date=now.date().isoformat(),
        game_hour=now.hour,
        game_minute=now.minute,
        day_of_week=now.strftime("%A").upper(),
        market_status=status,
        career_day=career_day,
        quarter_day=quarter_day,
        quarter_days=QUARTER_DAYS,
        quarter=((state.career.quarter_index - 1) % 4) + 1,
        career_year=((career_day - 1) // CAREER_YEAR_DAYS) + 1,
        working_day=is_business_day(now.date()),
        is_on_leave=state.leave.is_on_leave,
        hours_to_close=max(0, MARKET_CLOSE_HOUR - now.hour) if status == "OPEN" else 0,
    )


class TimeEngine:
    """Advances `state.now`, invoking simulation hooks for every elapsed unit of time."""

    def __init__(self, state: GameState, hooks: TimeHooks):
        self.state = state
        self.hooks = hooks

    # ------------------------------------------------------------------ #
    # Primitive steps
    # ------------------------------------------------------------------ #
    def _guard(self) -> None:
        if not self.hooks.can_advance():
            raise TimeError("Time cannot advance right now (career review pending or career over).")

    def _roll_to_next_business_day(self) -> bool:
        """From market close, simulate overnight/weekend and open the next session.

        Returns False if the quarter ended instead (review fired)."""
        today = self.state.now.date()
        nxt = next_business_day(today)
        if self.hooks.quarter_should_end(nxt):
            self.hooks.on_quarter_end()
            return False
        d = today + timedelta(days=1)
        while d < nxt:
            self.state.now = datetime.combine(d, datetime.min.time()).replace(hour=MARKET_OPEN_HOUR)
            self.hooks.on_non_business_day(d)
            d += timedelta(days=1)
        self.hooks.on_overnight(today, nxt)
        self.state.now = datetime.combine(nxt, datetime.min.time()).replace(hour=MARKET_OPEN_HOUR)
        self.hooks.on_market_open(nxt)
        return True

    def advance_hour(self) -> int:
        """Advance exactly one game hour. Returns trading hours simulated (0 or 1)."""
        self._guard()
        status = market_status(self.state.now)
        if status == "OPEN":
            start = self.state.now
            end = start + timedelta(hours=1)
            self.hooks.on_market_hour(start, end)
            self.state.now = end
            if end.hour >= MARKET_CLOSE_HOUR:
                self.hooks.on_market_close(end.date())
            return 1
        # Closed / weekend / pre-market: move to the next session's open.
        if status == "PRE_MARKET":
            self.state.now = self.state.now.replace(hour=MARKET_OPEN_HOUR)
            self.hooks.on_market_open(self.state.now.date())
            return 0
        self._roll_to_next_business_day()
        return 0

    # ------------------------------------------------------------------ #
    # Public operations
    # ------------------------------------------------------------------ #
    def advance_hours(self, n: int) -> int:
        """Advance up to n trading hours; stops at market close (never silently crosses a day)."""
        if n < 1 or n > 8:
            raise TimeError("Hours must be between 1 and 8.")
        self._guard()
        if market_status(self.state.now) != "OPEN":
            raise TimeError("The market is closed. Use NEXT BUSINESS DAY to continue.")
        done = 0
        while done < n and market_status(self.state.now) == "OPEN" and self.hooks.can_advance():
            done += self.advance_hour()
        return done

    def advance_to_market_close(self) -> int:
        self._guard()
        if market_status(self.state.now) != "OPEN":
            raise TimeError("The market is already closed.")
        done = 0
        while market_status(self.state.now) == "OPEN" and self.hooks.can_advance():
            done += self.advance_hour()
        return done

    def advance_to_next_business_day(self) -> int:
        self._guard()
        done = 0
        while market_status(self.state.now) == "OPEN" and self.hooks.can_advance():
            done += self.advance_hour()
        if self.hooks.can_advance():
            self._roll_to_next_business_day()
        return done

    def skip_weekend(self) -> int:
        self._guard()
        wd = self.state.now.weekday()
        if wd != 4 and wd < 5:
            raise TimeError("Skip weekend is only available on Fridays.")
        return self.advance_to_next_business_day()

    def advance_to_next_week(self) -> int:
        """Run business days until the next Monday 09:00."""
        self._guard()
        done = 0
        start_week = self.state.now.isocalendar()[:2]
        while self.hooks.can_advance():
            done += self.advance_to_next_business_day()
            if self.state.now.isocalendar()[:2] != start_week:
                break
        return done

    def start_leave(self, business_days: int) -> None:
        self.state.leave.is_on_leave = True
        self.state.leave.current_streak = 0

    def end_leave(self) -> None:
        self.state.leave.is_on_leave = False

    def _run_session(self) -> None:
        while market_status(self.state.now) == "OPEN" and self.hooks.can_advance():
            self.advance_hour()

    def run_leave_days(self, business_days: int) -> int:
        """Simulate whole business days while the player is away.

        If leave starts at the 09:00 open, today is the first leave day. Otherwise
        the rest of today passes (the player hands over the desk) and leave starts
        on the next business day. The player returns at 09:00 the business day after
        the last leave day. Returns the number of leave days actually consumed.
        """
        taken = 0
        starts_today = market_status(self.state.now) == "OPEN" and self.state.now.hour == MARKET_OPEN_HOUR
        if starts_today:
            self._run_session()
            taken = 1
            self.state.leave.current_streak = taken
        else:
            self._run_session()
        while taken < business_days and self.hooks.can_advance():
            if not self._roll_to_next_business_day():
                return taken
            taken += 1
            self.state.leave.current_streak = taken
            self._run_session()
        if self.hooks.can_advance():
            self._roll_to_next_business_day()
        return taken


def quarter_last_day(quarter_start: datetime) -> date:
    return quarter_start.date() + timedelta(days=QUARTER_DAYS - 1)
