"""
GameEngine — orchestrates every simulation system through TimeEngine hooks and
exposes the player actions. The engine mutates a GameState; persistence is
handled by the service layer.
"""
from __future__ import annotations

import math
import secrets
from datetime import date, datetime, timedelta
from typing import Any, Optional

import numpy as np

from app.ml import game_director
from app.simulation import (
    career_engine as ce,
    economy_engine,
    market_engine as me,
    opportunity_engine,
    player_engine,
    portfolio_engine as pe,
    research_engine,
    risk_engine as re_,
    team_engine,
)
from app.simulation.constants import (
    CAREER_LEVELS,
    CRORE,
    MARKET_CLOSE_HOUR,
    LIVE_MAX_CATCHUP_SECONDS,
    MARKET_OPEN_HOUR,
    PAID_LEAVE_PER_YEAR,
    TRADING_MINUTES_PER_DAY,
    SECTORS,
    STARTING_CAPITAL,
    STARTING_REPUTATION,
    WARMUP_BUSINESS_DAYS,
)
from app.simulation.event_engine import EventEngine
from app.simulation.state import (
    DailyRecord,
    GameState,
    IndexState,
    LeaveRecord,
    Message,
    NewsItem,
    Notification,
    Order,
    Popup,
    Portfolio,
    PriceAlert,
    ResearchJob,
    Thesis,
)
from app.simulation.time_engine import (
    TimeEngine,
    TimeError,
    business_days_between,
    clock_view,
    is_business_day,
    market_status,
    minutes_to_close,
    next_business_day,
)

GAME_START = datetime(2026, 1, 5, MARKET_OPEN_HOUR)  # a Monday


class ActionError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


REGIME_HINTS = {
    "BULL": "Breadth is strong and dips are being bought quickly.",
    "STABLE": "Conditions look orderly; I see no major stress signals.",
    "VOLATILE": "Cross-asset volatility is picking up. Expect whipsaws.",
    "BEAR": "Risk appetite is fading. Defensive positioning makes sense.",
    "CRISIS": "Funding markets are stressed. This is a capital-preservation environment.",
}
REGIME_NEIGHBOURS = {"BULL": "STABLE", "STABLE": "BULL", "VOLATILE": "BEAR", "BEAR": "VOLATILE", "CRISIS": "BEAR"}


class GameEngine:
    def __init__(self, state: GameState):
        self.state = state
        self.rng = np.random.default_rng()
        self.rng.bit_generator.state = state.rng_state
        self.events = EventEngine(state, self.rng)
        self.time = TimeEngine(state, self)
        self.warmup = False
        self.live_mode = False
        self.interrupts: list[str] = []

    # ================================================================== #
    # Creation
    # ================================================================== #
    @classmethod
    def new_game(cls, game_id: str, seed: Optional[int] = None) -> "GameEngine":
        seed = int(seed if seed is not None else secrets.randbits(31))
        rng = np.random.default_rng(seed)
        market = me.create_market(rng)
        stocks = me.create_stocks(rng)
        warm_start = GAME_START.date()
        for _ in range(WARMUP_BUSINESS_DAYS):
            warm_start -= timedelta(days=1)
            while not is_business_day(warm_start):
                warm_start -= timedelta(days=1)
        warm_dt = datetime.combine(warm_start, datetime.min.time()).replace(hour=MARKET_OPEN_HOUR)
        state = GameState(
            id=game_id, seed=seed, rng_state=rng.bit_generator.state, created_at=datetime.utcnow(),
            start_time=GAME_START, now=warm_dt, market=market, stocks=stocks, indices={},
            portfolio=Portfolio(cash=STARTING_CAPITAL, quarter_start_value=STARTING_CAPITAL, quarter_start_bench=1.0,
                                peak_value=STARTING_CAPITAL, day_start_value=STARTING_CAPITAL),
            career=ce.new_career(GAME_START, STARTING_CAPITAL, STARTING_REPUTATION),
        )
        state.indices = me.create_indices(state, rng)
        state.team = team_engine.create_team(rng)
        state.leave.allowance = PAID_LEAVE_PER_YEAR
        state.rng_state = rng.bit_generator.state
        eng = cls(state)
        eng._run_warmup()
        eng._start_career()
        eng.save_rng()
        return eng

    def _run_warmup(self) -> None:
        self.warmup = True
        s = self.state
        while s.now.date() < GAME_START.date():
            self.time.advance_to_next_business_day()
        self.warmup = False
        s.popups.clear()
        s.notifications.clear()
        s.messages.clear()
        s.news = s.news[-25:]
        s.events = [e for e in s.events if e.active]
        s.scheduled = [x for x in s.scheduled if not x.processed]

    def _start_career(self) -> None:
        s = self.state
        p = s.portfolio
        p.quarter_start_value = p.cash
        p.quarter_start_bench = s.indices["BH50"].value
        p.peak_value = p.cash
        p.day_start_value = p.cash
        p.hourly_nav = []
        pe.record_hour(s)
        s.flags["day_bench_open"] = s.indices["BH50"].value
        economy_engine.schedule_quarter(s, self.rng, s.career.quarter_start)
        self.message("ceo", "Welcome to Apex Capital", [
            "Welcome aboard. The board has approved a ₹100 Cr mandate for you.",
            "Your target is ₹112 Cr by the end of the quarter. Keep drawdown under 10%.",
            "My door is open, but I judge on results.",
        ], "HIGH")
        self.message("risk_manager", "Firm risk policy — MEDIUM profile", [
            "Single stock: max 15% of the portfolio.", "Single sector: max 40%.",
            "Maximum drawdown: 10% from peak. Beyond 20% the board acts immediately.",
            "Breaches come to me. Ignore them and it will show in your review.",
        ])
        self.message("research_director", "Research desk at your disposal", [
            "Send me any name for a quick look (1 hour) or a deep dive (3 hours).",
            "Deep dives catch things the tape doesn't show. Results season starts in about two weeks.",
        ])
        self._economist_brief()
        self.notify("TARGET_UPDATE", "Mandate received", "₹100 Cr to deploy. Target ₹112 Cr in 90 days.")
        self._telemetry("NEW_GAME")

    # ================================================================== #
    # Helpers
    # ================================================================== #
    def save_rng(self) -> None:
        self.state.rng_state = self.rng.bit_generator.state

    def notify(self, kind: str, title: str, body: str) -> None:
        if self.warmup:
            return
        s = self.state
        s.notifications.append(Notification(id=s.next_id("NTF"), time=s.now, kind=kind, title=title, body=body))
        s.notifications = s.notifications[-80:]

    def message(self, sender: str, subject: str, lines: list[str], priority: str = "NORMAL") -> None:
        if self.warmup:
            return
        s = self.state
        s.messages.append(Message(id=s.next_id("MSG"), time=s.now, sender=sender, subject=subject, lines=lines,
                                  priority=priority))
        s.messages = s.messages[-60:]

    def popup(self, ptype: str, payload: dict, blocking: bool = False, replace: bool = False) -> None:
        if self.warmup:
            return
        s = self.state
        if replace:
            s.popups = [p for p in s.popups if p.type != ptype]
        s.popups.append(Popup(id=s.next_id("POP"), type=ptype, created=s.now, blocking=blocking, payload=payload))

    def dialogue(self, title: str, lines: list[tuple[str, str]], tone: str = "neutral") -> None:
        if self.warmup or self.state.leave.is_on_leave:
            return
        self.popup("DIALOGUE", {"title": title, "tone": tone,
                                "lines": [{"speaker": sp, "text": tx} for sp, tx in lines]})

    def _cr(self, v: float) -> str:
        return f"₹{v / CRORE:,.2f} Cr"

    # ================================================================== #
    # TimeEngine hooks
    # ================================================================== #
    def can_advance(self) -> bool:
        s = self.state
        if s.career.status != "ACTIVE":
            return False
        if s.leave.is_on_leave or self.warmup:
            return True
        # The live market never waits for a risk decision; only the board review stops the clock.
        return not any(p.blocking and not (self.live_mode and p.type == "RISK_WARNING") for p in s.popups)

    def quarter_should_end(self, next_bd: date) -> bool:
        if self.warmup or self.state.flags.get("rollover"):
            return False
        return next_bd >= self.state.career.quarter_end.date()

    def on_quarter_end(self) -> None:
        s = self.state
        review = ce.quarterly_review(s)
        self.popup("REVIEW", review, blocking=True)
        self.interrupts.append("QUARTERLY_REVIEW")
        self.notify("CEO_MESSAGE", "Quarterly review", f"Outcome: {review['outcome']}")
        ce.log_decision(s, "REVIEW", f"Q{review['quarter']} review: {review['outcome']}")
        self._telemetry("REVIEW")

    def on_hour_begin(self, start: datetime) -> None:
        s = self.state
        jumps: dict[str, float] = s.flags.pop("pending_jumps", {})
        # Spontaneous events break at the top of the hour; prices react over the following minutes.
        new_events = self.events.hourly_random(jumps)
        drift, vboost, mboost = self.events.active_effects()
        me.begin_hour(s, start, drift, vboost, mboost, jumps)
        if self.warmup:
            return
        for ev in new_events:
            if ev.severity >= 3:
                held = [x for x in ev.affected_symbols if x in s.portfolio.holdings]
                tag = " (you hold this)" if held and ev.category == "company" else ""
                self.notify("BREAKING", ev.title, ev.narrative[:140] + tag)

    def _process_due(self) -> None:
        """Release scheduled items (results, data, policy, story chains) whose time has come."""
        s = self.state
        due = [x for x in s.scheduled if not x.processed and x.time <= s.now]
        if not due:
            return
        jumps = s.hour.jumps if s.hour is not None else s.flags.setdefault("pending_jumps", {})
        for sch in due:
            if sch.kind == "CEO_MEETING":
                sch.processed = True
                if not self.warmup:
                    self._ceo_meeting(sch.payload.get("topic", ""))
                continue
            res = self.events.process_scheduled(sch, True, jumps)
            if res.get("kind") == "EARNINGS" and not self.warmup:
                sym = res["symbol"]
                if sym in s.portfolio.holdings:
                    self.notify("BREAKING", f"Results: {s.stocks[sym].name}",
                                f"{res['outcome'].replace('_', ' ')} — you hold this stock.")

    def _minute_history_wanted(self) -> bool:
        # Warm-up only keeps the last two sessions of 1-minute bars (enough for intraday charts).
        if not self.warmup:
            return True
        return business_days_between(self.state.now.date(), GAME_START.date()) <= 2

    def on_minutes(self, k: int) -> None:
        """Simulate k minutes, stopping at each scheduled release so it lands on time."""
        s = self.state
        end = s.now + timedelta(minutes=k)
        record = self._minute_history_wanted()
        while s.now < end:
            self._process_due()
            nxt = min((x.time for x in s.scheduled if not x.processed and s.now < x.time < end), default=end)
            m = max(1, int((nxt - s.now) / timedelta(minutes=1)))
            t0 = s.now
            bars = me.step_minutes(s, self.rng, m, record)
            s.now = t0 + timedelta(minutes=m)
            if not self.warmup:
                self._check_resting(bars, t0)
        if not self.warmup:
            self._finish_research()

    def on_hour_end(self, start: datetime, end: datetime) -> None:
        s = self.state
        self._process_due()
        rets = me.end_hour(s, self.rng)
        if self.warmup:
            return
        self._post_hour(rets)

    def _post_hour(self, rets: dict[str, float]) -> None:
        s = self.state
        pe.record_hour(s)
        # Opportunities
        for o in opportunity_engine.expire(s):
            self.notify("OPPORTUNITY", "Opportunity expired", f"Block deal in {o.symbol} is no longer available.")
        if not s.leave.is_on_leave:
            opp = opportunity_engine.maybe_create(s, self.rng, self.events, s.flags.get("opp_rate", 1.0))
            if opp:
                st = s.stocks[opp.symbol]
                self.notify("OPPORTUNITY", f"Block deal: {st.name}",
                            f"{opp.qty:,} shares at ₹{opp.price:,.2f} ({opp.discount * 100:.1f}% discount). "
                            f"Expires {opp.expires_at.strftime('%H:%M')}.")
                self.message("trader", f"Block on offer — {st.name}", [
                    f"{opp.seller.capitalize()} wants out of {opp.qty:,} {opp.symbol} at ₹{opp.price:,.2f}, "
                    f"{opp.discount * 100:.1f}% below the screen.",
                    f"Offer closes at {opp.expires_at.strftime('%H:%M')}. Your call.",
                ], "HIGH")
        else:
            opportunity_engine.expire(s)
        # Holding alerts
        for sym, h in s.portfolio.holdings.items():
            st = s.stocks[sym]
            day_move = st.price / st.prev_close - 1
            key = f"alert-{sym}-{s.now.date()}"
            if abs(day_move) >= 0.05 and key not in s.flags:
                s.flags[key] = True
                verb = "jumped" if day_move > 0 else "dropped"
                self.notify("MARKET_ALERT", f"{st.name} {verb} {abs(day_move) * 100:.1f}%",
                            f"Your position is worth {self._cr(h.qty * st.price)}.")
        # Delegation while on leave
        if s.leave.is_on_leave:
            self._delegate_hour()
        # Risk
        self._risk_check()
        # Career: drawdown and milestones
        self._drawdown_check()
        for m in ce.check_milestones(s):
            self.notify("TARGET_UPDATE", "Target progress",
                        f"You are {int(m * 100)}% of the way to your quarterly target.")
        # Behaviour tracking
        player_engine.track_hour(s)
        s.flags["hours_in_quarter"] = s.flags.get("hours_in_quarter", 0) + 1
        self._telemetry("HOUR")

    def _risk_check(self) -> None:
        s = self.state
        report = re_.assess(s)
        new = re_.detect_new_breaches(s, report)
        for w in new:
            self._raise_warning(w)
        # Near-limit early warning from the risk manager (once per subject per day)
        rm_skill = s.team["risk_manager"].skills.get("risk", 60)
        if rm_skill >= 60 and not s.leave.is_on_leave:
            for n in report.near_limits:
                if n["rule"] == "DRAWDOWN":
                    continue
                key = f"near-{n['rule']}-{n['subject']}-{s.now.date()}"
                if key not in s.flags:
                    s.flags[key] = True
                    self.notify("RISK_WARNING", "Approaching limit",
                                f"{n['subject']} at {n['value'] * 100:.1f}% (limit {n['limit'] * 100:.0f}%).")

    def _raise_warning(self, w) -> None:
        s = self.state
        label = {"SINGLE_STOCK": f"{w.subject} position", "SECTOR": f"{w.subject} exposure",
                 "DRAWDOWN": "Portfolio drawdown"}.get(w.rule, w.subject)
        self.notify("RISK_WARNING", "RISK WARNING", f"{label} at {w.value * 100:.1f}% — firm policy {w.limit * 100:.0f}%.")
        if s.leave.is_on_leave:
            return
        self.popup("RISK_WARNING", self._warning_payload(w), blocking=True)
        self.interrupts.append("RISK_WARNING")

    def _warning_payload(self, w) -> dict:
        s = self.state
        label = {"SINGLE_STOCK": f"{s.stocks[w.subject].name} position" if w.subject in s.stocks else w.subject,
                 "SECTOR": f"{w.subject} exposure", "DRAWDOWN": "Drawdown from peak"}.get(w.rule, w.subject)
        options = ["REDUCE_EXPOSURE", "IGNORE"]
        if w.rule != "DRAWDOWN" and not w.exception_requested:
            options.insert(1, "REQUEST_EXCEPTION")
        orders = re_.reduction_orders(s, w)
        rm = s.team["risk_manager"]
        if w.rule == "DRAWDOWN":
            comment = "We're through the drawdown limit. I recommend cutting every position by a quarter."
        elif w.exception_requested:
            comment = "Exception declined. Reduce the position, or it goes on your record."
        elif rm.trust < 40:
            comment = "Again? Bring it back inside policy. I won't keep signing exceptions."
        else:
            comment = "This is outside policy. Bring it back in line, or make the case for an exception."
        return {"warning_id": w.id, "rule": w.rule, "subject": w.subject, "label": label, "value": w.value,
                "limit": w.limit, "options": options, "comment": comment,
                "reduce_orders": [{"symbol": a, "qty": b} for a, b in orders], "during_leave": w.during_leave}

    def _drawdown_check(self) -> None:
        s = self.state
        res = ce.drawdown_check(s)
        if res == "TERMINATE":
            review = ce.quarterly_review(s)
            review["outcome"] = "TERMINATED"
            review["ceo"] = ["The losses are unacceptable.",
                             f"We're down {pe.current_drawdown(s) * 100:.1f}% from peak. The board has acted.",
                             "Your mandate is terminated, effective immediately."]
            s.career.status = "TERMINATED"
            s.career.last_review = review
            s.career.history[-1].outcome = "TERMINATED"
            self.popup("REVIEW", review, blocking=True)
            self.interrupts.append("TERMINATED")
        elif res == "WARN":
            level = ce.escalate_warning(s)
            ce.add_rep(s, -4)
            team_engine.adjust(s, "ceo", trust=-10)
            ce.log_decision(s, "WARNING", f"Drawdown limit breached — {level}")
            if s.career.status == "TERMINATED":
                review = ce.quarterly_review(s)
                self.popup("REVIEW", review, blocking=True)
                self.interrupts.append("TERMINATED")
                return
            lines = [("ceo", "Come to my office. We need to discuss the portfolio."),
                     ("ceo", f"We're {pe.current_drawdown(s) * 100:.1f}% below peak. The mandate says 10%."),
                     ("ceo", f"This is a formal {level.lower()}."),
                     ("risk_manager", "I'd cut gross exposure now and rebuild from a smaller base.")]
            self.message("ceo", f"Formal {level.lower()} — drawdown", [t for _, t in lines], "CRITICAL")
            self.dialogue(f"CEO — {level}", lines, tone="danger")
            self.notify("CEO_MESSAGE", "CEO MESSAGE", "\"Come to my office. We need to discuss the portfolio.\"")

    def on_market_close(self, day: date) -> None:
        s = self.state
        # Close out remaining opportunities
        for o in s.opportunities:
            if o.status == "OPEN":
                o.status = "EXPIRED"
        me.daily_stock_step(s)
        regime_bias = s.flags.get("regime_bias") if not self.warmup else None
        me.daily_regime_step(s, self.rng, regime_bias)
        if self.warmup:
            me.close_session(s)
            return
        self._expire_day_orders()
        p = s.portfolio
        close_nav = pe.nav(s)
        bench_open = s.flags.get("day_bench_open", s.indices["BH50"].prev_close)
        bench_close = s.indices["BH50"].value
        bench_prev = s.indices["BH50"].prev_close
        day_ret = close_nav / p.day_start_value - 1 if p.day_start_value else 0.0
        bench_ret = bench_close / bench_prev - 1 if bench_prev else 0.0
        day_events = [e for e in s.events if e.started_at.date() == day]
        p.daily.append(DailyRecord(date=day.isoformat(), open_nav=p.day_start_value, close_nav=close_nav,
                                   bench_open=bench_prev, bench_close=bench_close, events=len(day_events)))
        p.daily = p.daily[-400:]
        s.outbox("game_days").append({"date": day.isoformat(), "open_nav": p.day_start_value, "close_nav": close_nav,
                                      "bench_close": bench_close, "regime": s.market.regime,
                                      "events": len(day_events), "reputation": s.career.reputation})
        # Reputation drift + ignored breach penalties
        ignored_open = [w for w in s.risk_warnings if w.status == "IGNORED"]
        # The board notices an ignored breach for about a week; after that it lives on in the review.
        ignored_recent = [w for w in ignored_open if w.resolved_at and (s.now - w.resolved_at).days <= 7]
        if p.holdings or ignored_open:
            ce.daily_reputation(s, day_ret, bench_ret, len(ignored_recent))
        for w in ignored_open:
            team_engine.adjust(s, "risk_manager", trust=-1.5)
        report = re_.assess(s)
        team_engine.daily_update(s, report.drawdown, len(re_.open_warnings(s)) + len(ignored_open))
        rep_flag = f"rep-warning-q{s.career.quarter_index}"
        if s.career.reputation < 30 and rep_flag not in s.flags:
            s.flags[rep_flag] = True
            lines = [("ceo", "The board is asking questions about you."),
                     ("ceo", f"Your standing has dropped to {s.career.reputation:.0f}. Below 20 at review, I can't protect you."),
                     ("risk_manager", "Start by resolving the open breaches. Document your large positions."),
                     ("compliance", "And please — research on file before you size up.")]
            self.message("ceo", "Your standing with the board", [t for _, t in lines], "CRITICAL")
            self.dialogue("CEO — Reputation warning", lines, tone="danger")
        self._market_wrap(day, bench_ret)
        # Daily report
        if not s.leave.is_on_leave:
            self.popup("DAILY_REPORT", self._daily_report(day, close_nav, day_ret, bench_ret, day_events, report),
                       replace=True)
        # Adaptive director + player model (daily cadence)
        player_engine.update_profile(s)
        decision = game_director.decide(s)
        s.market.event_intensity = decision["event_intensity"]
        s.flags["opp_rate"] = decision["opportunity_rate"]
        s.flags["regime_bias"] = decision["regime_bias"]
        s.director.last_decision = decision
        s.director.difficulty = decision["difficulty"]
        s.director.model_source = decision["source"]
        me.close_session(s)

    def _market_wrap(self, day: date, bench_ret: float) -> None:
        s = self.state
        sec_moves = {}
        for sec in SECTORS:
            members = [x for x in s.stocks.values() if x.sector == sec]
            sec_moves[sec] = sum(x.price / x.prev_close - 1 for x in members) / len(members)
        best = max(sec_moves, key=sec_moves.get)
        worst = min(sec_moves, key=sec_moves.get)
        direction = "higher" if bench_ret > 0.001 else "lower" if bench_ret < -0.001 else "flat"
        self.events.add_news(NewsItem(
            id=s.next_id("NEWS"), time=s.now, category="MARKET",
            tone="POSITIVE" if bench_ret > 0.001 else "NEGATIVE" if bench_ret < -0.001 else "NEUTRAL",
            headline=f"Markets close {direction}: BHARAT 50 {bench_ret * 100:+.2f}%",
            body=f"{best} led ({sec_moves[best] * 100:+.1f}%) while {worst} lagged ({sec_moves[worst] * 100:+.1f}%). "
                 f"BHARAT VOL at {s.indices['BVIX'].value:.1f}.",
            severity=1, sectors=[best, worst]))

    def _daily_report(self, day, close_nav, day_ret, bench_ret, day_events, report) -> dict:
        s = self.state
        holdings = []
        for sym, h in s.portfolio.holdings.items():
            st = s.stocks[sym]
            holdings.append({"symbol": sym, "name": st.name, "change": st.price / st.prev_close - 1})
        holdings.sort(key=lambda x: x["change"])
        return {
            "date": day.isoformat(), "benchmark_change": bench_ret,
            "indices": {k: s.indices[k].value / s.indices[k].prev_close - 1 for k in ("BH50", "DL30", "BKX", "BVIX")},
            "portfolio_value": close_nav, "portfolio_change": close_nav - s.portfolio.day_start_value,
            "portfolio_change_pct": day_ret,
            "best_holding": holdings[-1] if holdings else None, "worst_holding": holdings[0] if holdings else None,
            "new_events": len(day_events), "headlines": [e.title for e in day_events if e.severity >= 2][:4],
            "risk_level": report.level, "risk_score": report.score, "target_progress": ce.target_progress(s),
            "reputation": s.career.reputation,
        }

    def on_non_business_day(self, day: date) -> None:
        s = self.state
        economy_engine.daily_step(s, self.rng)
        evs = self.events.overnight_random(weekend=True)
        if not self.warmup:
            s.flags.setdefault("gap_events", []).extend([e.id for e in evs])

    def on_overnight(self, from_day: date, to_day: date) -> None:
        s = self.state
        if not self.warmup:
            s.flags["pre_gap_nav"] = pe.nav(s)
            s.flags["pre_gap_indices"] = {k: v.value for k, v in s.indices.items()}
            s.flags.setdefault("gap_events", [])
            s.flags["gap_from"] = from_day.isoformat()
        economy_engine.daily_step(s, self.rng)
        me.overnight(s, self.rng, from_day, to_day)
        evs = self.events.overnight_random(weekend=False)
        if not self.warmup:
            s.flags["gap_events"].extend([e.id for e in evs])
        self.events.pre_earnings_flow()

    def on_market_open(self, day: date) -> None:
        s = self.state
        me.open_session(s)
        s.flags["day_bench_open"] = s.indices["BH50"].value
        if day.weekday() == 0:
            me.weekly_reference(s)
        if self.warmup:
            s.flags.pop("gap_events", None)
            return
        p = s.portfolio
        p.day_start_value = pe.nav(s)
        pe.record_hour(s)
        # Leave allowance resets each career year
        cv = clock_view(s)
        if cv.career_year != s.leave.year:
            s.leave.year = cv.career_year
            s.leave.used = 0
        from_day = date.fromisoformat(s.flags.get("gap_from", day.isoformat()))
        weekend = (day - from_day).days > 1
        gap_events = [e for e in s.events if e.id in set(s.flags.get("gap_events", []))]
        pre_nav = s.flags.get("pre_gap_nav", p.day_start_value)
        pre_idx = s.flags.get("pre_gap_indices", {})
        gap = s.indices["BH50"].value / pre_idx.get("BH50", s.indices["BH50"].value) - 1
        if weekend and not s.leave.is_on_leave:
            sector_moves = {}
            for sec in SECTORS:
                mem = [x for x in s.stocks.values() if x.sector == sec]
                sector_moves[sec] = sum(x.price / x.prev_close - 1 for x in mem) / len(mem)
            self.popup("WEEKEND_REPORT", {
                "from": from_day.isoformat(), "to": day.isoformat(),
                "global": {k: s.indices[k].value / pre_idx.get(k, s.indices[k].value) - 1
                           for k in ("UST100", "US500", "GOLD", "USDINR")},
                "oil": s.market.economy.oil,
                "sectors": sector_moves, "headlines": [e.title for e in gap_events][:5],
                "friday_close": pre_nav, "monday_open": p.day_start_value, "change": p.day_start_value - pre_nav,
                "risk_level": re_.assess(s).level,
            }, replace=True)
        if abs(gap) > 0.006:
            self.events.add_news(NewsItem(
                id=s.next_id("NEWS"), time=s.now, category="MARKET", tone="POSITIVE" if gap > 0 else "NEGATIVE",
                headline=f"BHARAT 50 opens {'higher' if gap > 0 else 'lower'}, {gap * 100:+.2f}% at the bell",
                body=f"US 500 moved {(s.indices['US500'].value / pre_idx.get('US500', s.indices['US500'].value) - 1) * 100:+.2f}% "
                     f"overnight. {len(gap_events)} after-hours announcements.",
                severity=2 if abs(gap) > 0.012 else 1))
        s.flags["gap_events"] = []
        # Periodic team communications
        if day.weekday() == 0:
            self._economist_brief()
        if day.weekday() == 2:
            self._research_lead()
        qday = (day - s.career.quarter_start.date()).days + 1
        if 40 <= qday <= 44 and s.leave.used == 0 and "hr-leave" not in s.flags:
            s.flags["hr-leave"] = True
            self.message("hr", "A note on leave", [
                f"You have {s.leave.allowance - s.leave.used} paid leave days this year and haven't used any.",
                "The market doesn't stop while you're away — but burnt-out managers make worse calls.",
            ])
        self._risk_check()
        self._drawdown_check()
        self._telemetry("OPEN")

    # ================================================================== #
    # Team communications
    # ================================================================== #
    def _economist_brief(self) -> None:
        s = self.state
        e = s.market.economy
        skill = s.team["economist"].skills.get("macro", 60) / 100
        regime = s.market.regime
        read = regime if self.rng.random() < 0.45 + 0.45 * skill else REGIME_NEIGHBOURS[regime]
        nxt = [x for x in s.scheduled if x.kind in ("ECON_DATA", "POLICY") and not x.processed]
        lines = [f"Inflation {e.inflation:.1f}% · policy rate {e.policy_rate:.2f}% · GDP {e.gdp_growth:.1f}% · "
                 f"crude ${e.oil:.0f}.", REGIME_HINTS[read]]
        if nxt:
            n = nxt[0]
            extra = ""
            if n.kind == "ECON_DATA":
                extra = f" Consensus {n.payload['consensus']}%, our view {n.payload['desk_forecast']}%."
            lines.append(f"Next on the calendar: {n.title}, {n.time.strftime('%a %d %b %H:%M')}.{extra}")
        self.message("economist", "Weekly macro brief", lines)

    def _research_lead(self) -> None:
        s = self.state
        sk = team_engine.research_skill(s)
        best, best_up = None, -1.0
        for sym, st in s.stocks.items():
            est = st.fair_value * math.exp(self.rng.normal(0, 0.12 * (1.35 - sk)))
            up = est / st.price - 1
            if up > best_up:
                best, best_up = sym, up
        if best and best_up > 0.05:
            st = s.stocks[best]
            self.message("research_director", f"Idea: {st.name}", [
                "I've identified an opportunity worth reviewing.",
                f"{st.name} ({best}) screens ~{best_up * 100:.0f}% below our rough fair value.",
                "That's a screen, not a conclusion — a deep dive would firm it up.",
            ])

    def _ceo_meeting(self, topic: str) -> None:
        s = self.state
        prog = ce.target_progress(s)
        tprog = ce.time_progress(s)
        gap = s.career.target_value - pe.nav(s)
        dd = pe.current_drawdown(s)
        risk = re_.assess(s)
        lines: list[tuple[str, str]] = []
        tone = "neutral"
        if topic == "FINAL":
            lines.append(("ceo", "Final stretch. The board meets at quarter end."))
        if prog >= tprog + 0.15 and dd < 0.05:
            lines += [("ceo", "Strong work so far. You're ahead of pace."),
                      ("ceo", "Don't get greedy — the board hates surprises more than it loves returns.")]
            ce.add_rep(s, 1)
            tone = "positive"
        elif prog >= tprog - 0.1:
            lines += [("ceo", "You're roughly on pace."),
                      ("ceo", f"{self._cr(max(gap, 0))} still to go. Keep it disciplined.")]
        else:
            ask = max(1.0, round(min(gap, (tprog - max(prog, 0)) * (s.career.target_value - s.portfolio.quarter_start_value)) / CRORE))
            lines += [("ceo", "We're behind target."),
                      ("ceo", f"I want another ₹{ask:.0f} Cr before quarter end.")]
            tone = "warning"
            team_engine.adjust(s, "ceo", trust=-3)
        if risk.level in ("HIGH", "CRITICAL"):
            lines.append(("risk_manager", "For the record — that would increase portfolio risk significantly. "
                                          f"We're already at a {risk.level.lower()} risk score of {risk.score:.0f}."))
        lead = self._best_lead()
        if lead:
            lines.append(("research_director", f"I've identified an opportunity worth reviewing: {lead}."))
        self.message("ceo", "CEO check-in", [t for sp, t in lines if sp == "ceo"], "HIGH")
        self.dialogue("CEO CHECK-IN", lines, tone)
        self.notify("CEO_MESSAGE", "CEO MESSAGE", lines[0][1])
        self.interrupts.append("CEO_MEETING")

    def _best_lead(self) -> Optional[str]:
        s = self.state
        recent = [r for r in s.research if r.rating == "BUY" and (s.now - r.time).days < 20]
        if recent:
            r = recent[-1]
            return f"{s.stocks[r.symbol].name} — our estimate ₹{r.est_fair_value:,.0f} vs ₹{s.stocks[r.symbol].price:,.0f}"
        return None

    # ================================================================== #
    # Delegation (while on leave)
    # ================================================================== #
    def _delegate_hour(self) -> None:
        s = self.state
        delegate = CAREER_LEVELS[s.career.level]["delegate"]
        if not delegate:
            return
        actions = s.flags.setdefault("leave_team_actions", [])
        for sym, h in list(s.portfolio.holdings.items()):
            st = s.stocks[sym]
            if st.price < h.avg_cost * 0.90:
                tx = pe.execute_sell(s, sym, h.qty, source="DELEGATE")
                actions.append(f"Stop-loss: sold {tx.qty:,} {sym} at ₹{tx.price:,.2f}")
        report = re_.assess(s)
        for b in report.breaches:
            if b["rule"] in ("SINGLE_STOCK", "SECTOR") and not b["excepted"]:
                w = next((w for w in s.risk_warnings if w.rule == b["rule"] and w.subject == b["subject"]
                          and w.status in ("OPEN", "IGNORED")), None)
                if w:
                    for sym, qty in re_.reduction_orders(s, w):
                        pe.execute_sell(s, sym, qty, source="DELEGATE")
                        actions.append(f"Risk trim: sold {qty:,} {sym}")
                    w.status = "REDUCED"
                    w.resolved_at = s.now

    # ================================================================== #
    # Telemetry
    # ================================================================== #
    def _telemetry(self, trigger: str) -> None:
        if self.warmup:
            return
        s = self.state
        report = re_.assess(s)
        cv = clock_view(s)
        v = pe.nav(s)
        s.outbox("telemetry").append({
            "t": s.now.isoformat(), "trigger": trigger, "day": cv.career_day, "game_time": s.now.strftime("%H:%M"),
            "career_level": s.career.level, "cash": round(s.portfolio.cash, 2), "portfolio_value": round(v, 2),
            "portfolio_return": v / s.portfolio.quarter_start_value - 1, "drawdown": report.drawdown,
            "risk_score": report.score, "trade_count": s.stats.trades, "buy_count": s.stats.buys,
            "sell_count": s.stats.sells, "largest_position": report.largest_position.get("weight", 0.0),
            "sector_exposure": {k: round(v2, 4) for k, v2 in report.sector_weights.items()},
            "market_regime": s.market.regime, "active_events": sum(1 for e in s.events if e.active),
            "player_decisions": trigger, "target_progress": ce.target_progress(s), "reputation": s.career.reputation,
            "leave_status": s.leave.is_on_leave, "hours_worked": s.stats.hours_worked,
            "hours_skipped": s.stats.hours_skipped, "behavior_profile": s.stats.behavior_profile,
            "features": player_engine.features(s),
        })

    # ================================================================== #
    # Player actions
    # ================================================================== #
    def _begin_action(self) -> None:
        s = self.state
        self.interrupts = []
        # Informational popups are dismissed once the player moves on.
        s.popups = [p for p in s.popups if p.blocking]

    def _require_active(self) -> None:
        s = self.state
        if s.career.status == "TERMINATED":
            raise ActionError("CAREER_OVER", "Your career at Apex Capital has ended. Start a new career.", 409)
        if s.career.status == "REVIEW":
            raise ActionError("REVIEW_PENDING", "The quarterly review is waiting for you.", 409)
        if s.leave.is_on_leave:
            raise ActionError("ON_LEAVE", "You are on leave.", 409)

    def _require_unblocked(self) -> None:
        blocking = [p for p in self.state.popups if p.blocking]
        if blocking:
            raise ActionError("DECISION_REQUIRED", f"Resolve the pending {blocking[0].type.replace('_', ' ').lower()} first.", 409)

    def advance(self, kind: str, hours: int = 1) -> dict[str, Any]:
        self._require_active()
        self._require_unblocked()
        self._begin_action()
        s = self.state
        before = s.now
        try:
            if kind == "hour":
                done = self.time.advance_hour()
            elif kind == "hours":
                done = self.time.advance_hours(hours)
            elif kind == "close":
                done = self.time.advance_to_market_close()
            elif kind == "next_day":
                done = self.time.advance_to_next_business_day()
            elif kind == "weekend":
                done = self.time.skip_weekend()
            elif kind == "week":
                done = self.time.advance_to_next_week()
            else:
                raise ActionError("INVALID_ACTION", f"Unknown time action '{kind}'.")
        except TimeError as e:
            raise ActionError("INVALID_TIME", str(e)) from e
        if kind == "hour":
            s.stats.hours_worked += done
        else:
            s.stats.hours_skipped += done
        self.save_rng()
        return {"hours_simulated": done, "from": before.isoformat(), "to": s.now.isoformat(),
                "interrupted_by": self.interrupts}

    def _require_market_open(self) -> None:
        if market_status(self.state.now) != "OPEN":
            raise ActionError("MARKET_CLOSED", "The market is closed. Orders can be placed 09:00–17:00 on business days.")

    def quote(self, side: str, symbol: str, qty: int) -> dict:
        try:
            q = pe.quote(self.state, side, symbol, qty)
        except pe.TradeError as e:
            raise ActionError(e.code, e.message) from e
        d = q.dict()
        s = self.state
        lim = re_.policy(s)
        if side == "BUY":
            if q.total > s.portfolio.cash:
                d["warnings"].append("Insufficient cash for this order.")
            if q.weight_after > lim["max_single_stock"]:
                d["warnings"].append(f"Position would be {q.weight_after * 100:.1f}% of the portfolio — "
                                     f"above the {lim['max_single_stock'] * 100:.0f}% single-stock limit.")
            sec = s.stocks[symbol].sector
            _, sw = re_.exposures(s)
            sec_after = sw.get(sec, 0) + q.value / max(pe.nav(s), 1)
            if sec_after > lim["max_sector"]:
                d["warnings"].append(f"{sec} exposure would reach {sec_after * 100:.1f}% — above the "
                                     f"{lim['max_sector'] * 100:.0f}% sector limit.")
            d["sector_after"] = sec_after
        else:
            h = s.portfolio.holdings.get(symbol)
            if not h or qty > h.qty:
                d["warnings"].append(f"You hold {h.qty if h else 0:,} shares.")
        return d

    def trade(self, side: str, symbol: str, qty: int) -> dict:
        self._require_active()
        self._require_market_open()
        self._begin_action()
        s = self.state
        symbol = (symbol or "").upper()
        day_pnl_pct = pe.nav(s) / s.portfolio.day_start_value - 1 if s.portfolio.day_start_value else 0
        try:
            if side == "BUY":
                tx = pe.execute_buy(s, symbol, qty)
                s.stats.buys += 1
            elif side == "SELL":
                tx = pe.execute_sell(s, symbol, qty)
                s.stats.sells += 1
                if tx.realized_pnl > 0:
                    ce.add_xp(s, min(200, int(tx.realized_pnl / 1_000_000)))
            else:
                raise ActionError("INVALID_SIDE", "Side must be BUY or SELL.")
        except pe.TradeError as e:
            raise ActionError(e.code, e.message) from e
        s.stats.trades += 1
        if day_pnl_pct < -0.01:
            s.stats.trades_after_loss += 1
        if any(symbol in n.symbols and (s.now - n.time) <= timedelta(hours=2) for n in s.news[-30:]):
            s.stats.trades_after_news += 1
        self._compliance_check(tx)
        self._research_trust(tx)
        st = s.stocks[symbol]
        self.notify("TRADE", "TRADE EXECUTED",
                    f"{tx.side} {tx.qty:,} {symbol} @ ₹{tx.price:,.2f} · {self._cr(tx.value)}"
                    + (f" · P&L {self._cr(tx.realized_pnl)}" if tx.side == "SELL" else ""))
        if tx.value >= 0.08 * pe.nav(s):
            ce.log_decision(s, "TRADE", f"{tx.side} {tx.qty:,} {st.name} ({self._cr(tx.value)})")
        self._risk_check()
        self._telemetry(f"TRADE_{side}")
        self.save_rng()
        return {"transaction": tx.model_dump(mode="json"), "interrupted_by": self.interrupts}

    def _compliance_check(self, tx) -> None:
        s = self.state
        if tx.side != "BUY" or tx.value < 0.08 * pe.nav(s):
            return
        cutoff = s.now - timedelta(days=7)
        documented = any(r.symbol == tx.symbol and r.time >= cutoff for r in s.research) or \
            any(t.symbol == tx.symbol and t.time >= cutoff for t in s.theses)
        if documented:
            return
        # One strike per stock per week: repeated top-ups of the same undocumented name don't stack.
        last = s.flags.get(f"doc-{tx.symbol}")
        if last and (s.now - datetime.fromisoformat(last)).days < 7:
            return
        s.flags[f"doc-{tx.symbol}"] = s.now.isoformat()
        lapses = s.flags.get("doc_lapses", 0) + 1
        s.flags["doc_lapses"] = lapses
        if lapses == 1:
            self.message("compliance", "Pre-trade documentation", [
                f"Your {tx.symbol} order was {tx.value / pe.nav(s) * 100:.1f}% of the book with no research or thesis on file.",
                "Please document large positions. Next time it goes on the record.",
            ])
        else:
            s.career.compliance_strikes += 1
            lenient = s.team["compliance"].skills.get("compliance", 70) >= 80 and lapses == 2
            ce.add_rep(s, -0.5 if lenient else -1.0)
            self.message("compliance", "Compliance note filed", [
                f"Large {tx.symbol} purchase without documented research. Strike {s.career.compliance_strikes} recorded.",
            ], "HIGH")
            self.notify("RISK_WARNING", "Compliance strike", f"Undocumented large trade in {tx.symbol}.")

    def _research_trust(self, tx) -> None:
        s = self.state
        recent = [r for r in s.research if r.symbol == tx.symbol and (s.now - r.time).days < 10]
        if not recent:
            return
        r = recent[-1]
        agrees = (tx.side == "BUY" and r.rating == "BUY") or (tx.side == "SELL" and r.rating == "SELL")
        team_engine.adjust(s, "research_director", trust=2 if agrees else -1)

    def research(self, symbol: str, depth: str) -> dict:
        self._require_active()
        self._require_unblocked()
        self._require_market_open()
        symbol = (symbol or "").upper()
        depth = (depth or "").upper()
        if symbol not in self.state.stocks:
            raise ActionError("INVALID_SYMBOL", f"Unknown symbol '{symbol}'.")
        if depth not in research_engine.RESEARCH_HOURS:
            raise ActionError("INVALID_DEPTH", "Depth must be QUICK or DEEP.")
        need = research_engine.RESEARCH_HOURS[depth]
        s = self.state
        left = minutes_to_close(s.now)
        if left < need * 60:
            raise ActionError("NOT_ENOUGH_TIME", f"A {depth.lower()} review takes {need}h; only "
                                                 f"{left // 60}h {left % 60:02d}m left before the close.")
        if any(j.symbol == symbol for j in s.research_jobs):
            raise ActionError("RESEARCH_PENDING", f"The desk is already working on {symbol}.")
        self._begin_action()
        # The analysts work while the market keeps moving; the report lands when they are done.
        job = ResearchJob(id=s.next_id("RJ"), symbol=symbol, depth=depth, started=s.now,
                          ready_at=s.now + timedelta(hours=need))
        s.research_jobs.append(job)
        self._telemetry("RESEARCH")
        self.save_rng()
        return {"job": job.model_dump(mode="json"), "interrupted_by": self.interrupts}

    def record_thesis(self, symbol: str, stance: str, text: str) -> dict:
        s = self.state
        symbol = (symbol or "").upper()
        stance = (stance or "").upper()
        if symbol not in s.stocks:
            raise ActionError("INVALID_SYMBOL", f"Unknown symbol '{symbol}'.")
        if stance not in ("BULLISH", "BEARISH", "NEUTRAL"):
            raise ActionError("INVALID_STANCE", "Stance must be BULLISH, BEARISH or NEUTRAL.")
        text = (text or "").strip()[:500]
        if len(text) < 3:
            raise ActionError("INVALID_TEXT", "Write a short thesis.")
        t = Thesis(id=s.next_id("THS"), symbol=symbol, stance=stance, text=text, time=s.now, price_at=s.stocks[symbol].price)
        s.theses.append(t)
        s.theses = s.theses[-100:]
        ce.add_xp(s, 5)
        return {"thesis": t.model_dump(mode="json")}

    def resolve_risk(self, warning_id: str, action: str) -> dict:
        s = self.state
        if s.career.status != "ACTIVE":
            raise ActionError("CAREER_OVER", "No active mandate.", 409)
        w = next((w for w in s.risk_warnings if w.id == warning_id), None)
        if not w or w.status != "OPEN":
            raise ActionError("INVALID_WARNING", "That warning is not open.")
        action = (action or "").upper()
        popup = next((p for p in s.popups if p.type == "RISK_WARNING" and p.payload.get("warning_id") == w.id), None)
        result: dict[str, Any] = {"action": action}
        if action == "REDUCE_EXPOSURE":
            sold = []
            # Risk reductions may also execute in the 17:00 closing auction.
            closing_auction = is_business_day(s.now.date()) and s.now.hour == MARKET_CLOSE_HOUR
            if market_status(s.now) != "OPEN" and not closing_auction:
                raise ActionError("MARKET_CLOSED", "The market is closed; orders will have to wait for the open.")
            for sym, qty in re_.reduction_orders(s, w):
                tx = pe.execute_sell(s, sym, qty, source="RISK_REDUCTION")
                sold.append(tx.model_dump(mode="json"))
                s.stats.sells += 1
                s.stats.trades += 1
            w.status = "REDUCED"
            w.resolved_at = s.now
            team_engine.adjust(s, "risk_manager", trust=3)
            ce.add_rep(s, 0.5)
            ce.log_decision(s, "RISK", f"Reduced {w.subject} after {w.rule.lower().replace('_', ' ')} breach")
            result["transactions"] = sold
        elif action == "REQUEST_EXCEPTION":
            if w.rule == "DRAWDOWN" or w.exception_requested:
                raise ActionError("NOT_ALLOWED", "An exception cannot be requested for this breach.")
            w.exception_requested = True
            p = re_.exception_probability(s, w)
            granted = bool(self.rng.random() < p)
            if granted:
                w.status = "EXCEPTION_GRANTED"
                w.resolved_at = s.now
                s.career.exceptions_granted += 1
                re_.grant_exception(s, w)
                ce.add_rep(s, -0.5)
                team_engine.adjust(s, "risk_manager", trust=-2)
                self.message("risk_manager", "Exception granted — 7 days", [
                    f"I've signed a temporary exception for {w.subject}. Seven days.",
                    "It's on the record. Don't make me regret it.",
                ])
            else:
                team_engine.adjust(s, "risk_manager", trust=-1)
            ce.log_decision(s, "RISK", f"Requested exception for {w.subject}: {'granted' if granted else 'declined'}")
            result["granted"] = granted
        elif action == "IGNORE":
            w.status = "IGNORED"
            w.resolved_at = s.now
            s.career.ignored_violations += 1
            ce.add_rep(s, -3)
            team_engine.adjust(s, "risk_manager", trust=-8)
            team_engine.adjust(s, "compliance", trust=-4)
            self.message("risk_manager", f"Breach ignored — {w.subject}", [
                "Noted. The breach stays on your record until it is resolved.",
                "Every day it stays open costs you credibility with the board.",
            ], "HIGH")
            ce.log_decision(s, "RISK", f"Ignored {w.rule.lower().replace('_', ' ')} breach on {w.subject}")
        else:
            raise ActionError("INVALID_ACTION", "Action must be REDUCE_EXPOSURE, REQUEST_EXCEPTION or IGNORE.")
        if popup:
            s.popups.remove(popup)
            if w.status == "OPEN":  # exception declined: ask again with the remaining options
                s.popups.append(Popup(id=s.next_id("POP"), type="RISK_WARNING", created=s.now, blocking=True,
                                      payload=self._warning_payload(w)))
        self._telemetry(f"RISK_{action}")
        self.save_rng()
        return result

    def accept_opportunity(self, opp_id: str, qty: Optional[int] = None) -> dict:
        self._require_active()
        self._require_market_open()
        s = self.state
        o = next((o for o in s.opportunities if o.id == opp_id), None)
        if not o:
            raise ActionError("INVALID_OPPORTUNITY", "Unknown opportunity.")
        if o.status != "OPEN" or s.now >= o.expires_at:
            raise ActionError("OPPORTUNITY_EXPIRED", "OPPORTUNITY EXPIRED")
        qty = o.qty if qty is None else qty
        if not isinstance(qty, int) or qty <= 0 or qty > o.qty:
            raise ActionError("INVALID_QUANTITY", f"Quantity must be between 1 and {o.qty:,}.")
        self._begin_action()
        try:
            tx = pe.execute_buy(s, o.symbol, qty, source="BLOCK_DEAL", price_override=o.price)
        except pe.TradeError as e:
            raise ActionError(e.code, e.message) from e
        o.status = "ACCEPTED"
        s.stats.trades += 1
        s.stats.buys += 1
        s.stats.block_deals += 1
        ce.log_decision(s, "DEAL", f"Took block of {qty:,} {o.symbol} at {o.discount * 100:.1f}% discount")
        self.notify("TRADE", "BLOCK DEAL EXECUTED", f"Bought {qty:,} {o.symbol} @ ₹{o.price:,.2f}")
        self._risk_check()
        self._telemetry("BLOCK_DEAL")
        self.save_rng()
        return {"transaction": tx.model_dump(mode="json"), "interrupted_by": self.interrupts}

    def decline_opportunity(self, opp_id: str) -> dict:
        o = next((o for o in self.state.opportunities if o.id == opp_id), None)
        if not o or o.status != "OPEN":
            raise ActionError("INVALID_OPPORTUNITY", "That opportunity is not open.")
        o.status = "DECLINED"
        return {"declined": opp_id}

    def take_leave(self, days: int) -> dict:
        self._require_active()
        self._require_unblocked()
        s = self.state
        if not isinstance(days, int) or days < 1:
            raise ActionError("INVALID_LEAVE", "Leave must be at least one business day.")
        remaining = s.leave.allowance - s.leave.used
        if days > remaining:
            raise ActionError("LEAVE_EXCEEDED", f"You only have {remaining} paid leave days remaining this year.")
        if days > 30:
            raise ActionError("INVALID_LEAVE", "Maximum 30 consecutive business days.")
        self._begin_action()
        start = s.now
        start_nav = pe.nav(s)
        start_bench = s.indices["BH50"].value
        first_event = s.counters.get("EVT", 0)
        s.flags["leave_team_actions"] = []
        self.time.start_leave(days)
        try:
            taken = self.time.run_leave_days(days)
        finally:
            self.time.end_leave()
        s.leave.used += taken
        s.leave.records.append(LeaveRecord(start=start, end=s.now, business_days=taken))
        s.outbox("leave_records").append({"start": start.isoformat(), "end": s.now.isoformat(), "days": taken})
        new_events = [e for e in s.events if int(e.id.split("-")[1]) > first_event]
        end_nav = pe.nav(s)
        report = re_.assess(s)
        delegate = CAREER_LEVELS[s.career.level]["delegate"]
        actions = s.flags.pop("leave_team_actions", [])
        if not delegate:
            actions = ["No dedicated portfolio manager at your level — positions were left untouched."]
        payload = {
            "days_away": taken, "from": start.isoformat(), "to": s.now.isoformat(),
            "market_move": s.indices["BH50"].value / start_bench - 1,
            "portfolio_before": start_nav, "portfolio_after": end_nav,
            "new_events": len(new_events), "headlines": [e.title for e in new_events if e.severity >= 3][:5],
            "team_actions": actions, "risk_level": report.level, "risk_score": report.score,
            "leave_remaining": s.leave.allowance - s.leave.used,
        }
        if s.career.status == "ACTIVE":
            self.popup("LEAVE_REPORT", payload)
            for w in re_.open_warnings(s):
                self.popup("RISK_WARNING", self._warning_payload(w), blocking=True)
        ce.log_decision(s, "LEAVE", f"Took {taken} day(s) of leave")
        self._telemetry("LEAVE")
        self.save_rng()
        return {"leave": payload, "interrupted_by": self.interrupts}

    def ack_popup(self, popup_id: str) -> dict:
        s = self.state
        p = next((p for p in s.popups if p.id == popup_id), None)
        if not p:
            raise ActionError("INVALID_POPUP", "Nothing to acknowledge.")
        if p.type == "RISK_WARNING":
            raise ActionError("DECISION_REQUIRED", "Choose how to handle the risk warning.")
        s.popups.remove(p)
        if p.type == "REVIEW":
            s.live.anchor = None  # the clock restarts from now, without catching up the review time
        if p.type == "REVIEW" and s.career.status == "REVIEW":
            self._next_quarter()
        return {"acknowledged": popup_id}

    def _next_quarter(self) -> None:
        s = self.state
        s.career.status = "ACTIVE"
        s.flags["rollover"] = True
        try:
            if market_status(s.now) == "OPEN":
                self.time.advance_to_market_close()
            self.time._roll_to_next_business_day()
        finally:
            s.flags.pop("rollover", None)
        ce.begin_next_quarter(s)
        s.scheduled = [x for x in s.scheduled if not x.processed and x.kind in ("CHAIN", "HIDDEN")]
        economy_engine.schedule_quarter(s, self.rng, s.career.quarter_start)
        lvl = CAREER_LEVELS[s.career.level]
        self.message("ceo", f"Quarter {s.career.quarter_index} mandate", [
            f"New quarter. Starting value {self._cr(s.portfolio.quarter_start_value)}.",
            f"Target {self._cr(s.career.target_value)} (+{s.career.target_return * 100:.0f}%). "
            f"Drawdown limit {s.career.max_drawdown_limit * 100:.1f}%.",
        ], "HIGH")
        if s.career.level > 1:
            self.message("hr", "Your expanded team", [f"As {lvl['title']} you now have: " + ", ".join(lvl["unlocks"]) + "."])
        self.save_rng()

    def hire(self, candidate_id: str) -> dict:
        s = self.state
        if s.career.level < 2:
            raise ActionError("LOCKED", "Recruitment unlocks at Level 2 (Investment Director).", 403)
        cand = next((c for c in team_engine.candidates(s) if c["id"] == candidate_id), None)
        if not cand:
            raise ActionError("INVALID_CANDIDATE", "Unknown candidate.")
        if any(c.id == candidate_id for c in s.team.values()):
            raise ActionError("ALREADY_HIRED", "Already on the team.")
        hired = sum(1 for c in s.team.values() if not c.core)
        if hired >= 2 * (s.career.level - 1):
            raise ActionError("TEAM_FULL", "Headcount budget reached for your level.")
        from app.simulation.state import Character
        s.team[candidate_id] = Character(id=candidate_id, name=cand["name"], role=cand["role"], avatar=cand["avatar"],
                                         skills=cand["skills"], loyalty=cand["loyalty"], salary_lakh=cand["salary_lakh"],
                                         core=False, personality=f"{cand['experience']} years experience.")
        return {"hired": candidate_id}

    def mark_read(self, kind: str, ids: list[str] | None) -> dict:
        items = self.state.messages if kind == "messages" else self.state.notifications
        for it in items:
            if ids is None or it.id in ids:
                it.read = True
        return {"ok": True}

    # ================================================================== #
    # Live clock
    # ================================================================== #
    def sync_live(self, wall: float, session_seconds: float, closed_seconds: float) -> bool:
        """Advance the market by the real time elapsed since the last sync.

        At speed 1 one game minute passes every `session_seconds / 480` real seconds. When the
        session is over the market stays closed for `closed_seconds / speed` and then opens the
        next business day. Returns True when the state changed and must be saved."""
        s = self.state
        lv = s.live
        speed = max(1, lv.speed)
        if lv.anchor is None:
            lv.anchor = wall
            return True
        changed = False
        elapsed = wall - lv.anchor
        if elapsed > LIVE_MAX_CATCHUP_SECONDS or elapsed < 0:
            # Nobody was at the desk (tab closed, laptop asleep, a save loaded): resume from now
            # instead of fast-forwarding through time nobody watched.
            lv.anchor = wall
            return True
        if s.career.status != "ACTIVE" or s.leave.is_on_leave:
            lv.anchor = wall
            return changed
        self.live_mode = True
        try:
            if not self.can_advance():
                lv.anchor = wall
                return changed
            status = market_status(s.now)
            if status == "OPEN":
                per_minute = session_seconds / TRADING_MINUTES_PER_DAY / speed
                n = int(elapsed // per_minute)
                if n <= 0:
                    return changed
                self.interrupts = []
                s.stats.hours_worked += self.time.advance_minutes(n)
                lv.anchor += n * per_minute
                if market_status(s.now) != "OPEN":
                    lv.anchor = wall  # the closing bell starts the between-sessions pause
            else:
                if elapsed < closed_seconds / speed:
                    return changed
                self.interrupts = []
                if status == "PRE_MARKET":
                    self.time.advance_hour()
                else:
                    self.time.advance_to_next_business_day()
                lv.anchor = wall
            self.save_rng()
            return True
        finally:
            self.live_mode = False

    def live_view(self, wall: float, session_seconds: float, closed_seconds: float, speeds: list[int]) -> dict:
        s = self.state
        speed = max(1, s.live.speed)
        per_minute = session_seconds / TRADING_MINUTES_PER_DAY / speed
        since = wall - s.live.anchor if s.live.anchor is not None else 0.0
        status = market_status(s.now)
        if status == "OPEN":
            wait = per_minute - since
        else:
            wait = closed_seconds / speed - since
        return {"speed": speed, "speeds": speeds, "seconds_per_minute": round(per_minute, 3),
                "next_tick_in": round(max(0.25, wait), 2), "running": s.career.status == "ACTIVE",
                "session_seconds": session_seconds}

    def set_speed(self, speed: int, speeds: list[int]) -> dict:
        if speed not in speeds:
            raise ActionError("INVALID_SPEED", f"Speed must be one of {', '.join(f'{x}x' for x in speeds)}.")
        self.state.live.speed = speed
        return {"speed": speed}

    # ================================================================== #
    # Orders: market, limit, stop-loss (SL) and stop-loss market (SL-M), with
    # optional bracket legs (target + stop-loss, one cancels the other)
    # ================================================================== #
    def _tx_stats(self, tx) -> None:
        s = self.state
        s.stats.trades += 1
        if tx.side == "BUY":
            s.stats.buys += 1
        else:
            s.stats.sells += 1
            if tx.realized_pnl > 0:
                ce.add_xp(s, min(200, int(tx.realized_pnl / 1_000_000)))

    def place_order(self, symbol: str, side: str, otype: str, qty: int, price: Optional[float] = None,
                    trigger: Optional[float] = None, validity: str = "DAY", target: Optional[float] = None,
                    stoploss: Optional[float] = None) -> dict:
        self._require_active()
        s = self.state
        symbol, side, otype, validity = (symbol or "").upper(), (side or "").upper(), (otype or "").upper(), (validity or "DAY").upper()
        if symbol not in s.stocks:
            raise ActionError("INVALID_SYMBOL", f"Unknown symbol '{symbol}'.")
        if side not in ("BUY", "SELL"):
            raise ActionError("INVALID_SIDE", "Side must be BUY or SELL.")
        if otype not in ("MARKET", "LIMIT", "SL", "SL-M"):
            raise ActionError("INVALID_ORDER_TYPE", "Order type must be MARKET, LIMIT, SL or SL-M.")
        if validity not in ("DAY", "GTC"):
            raise ActionError("INVALID_VALIDITY", "Validity must be DAY or GTC.")
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ActionError("INVALID_QUANTITY", "Quantity must be a positive whole number.")
        ltp = s.stocks[symbol].price
        ref = price if otype in ("LIMIT", "SL") and price else trigger if trigger else ltp
        if otype in ("LIMIT", "SL") and not (price and price > 0):
            raise ActionError("INVALID_PRICE", "Enter a limit price.")
        if otype in ("SL", "SL-M") and not (trigger and trigger > 0):
            raise ActionError("INVALID_TRIGGER", "Enter a trigger price.")
        for v, label in ((price, "Limit price"), (trigger, "Trigger price")):
            if v and not (0.8 * ltp <= v <= 1.2 * ltp):
                raise ActionError("PRICE_OUT_OF_RANGE", f"{label} must be within 20% of the last traded price (₹{ltp:,.2f}).")
        if otype in ("SL", "SL-M"):
            if side == "BUY" and trigger <= ltp:
                raise ActionError("INVALID_TRIGGER", "A buy stop's trigger must be above the last traded price.")
            if side == "SELL" and trigger >= ltp:
                raise ActionError("INVALID_TRIGGER", "A sell stop's trigger must be below the last traded price.")
            if otype == "SL" and side == "BUY" and price < trigger:
                raise ActionError("INVALID_PRICE", "For a buy stop-limit the limit price must be at or above the trigger.")
            if otype == "SL" and side == "SELL" and price > trigger:
                raise ActionError("INVALID_PRICE", "For a sell stop-limit the limit price must be at or below the trigger.")
        if side == "SELL":
            h = s.portfolio.holdings.get(symbol)
            if not h:
                raise ActionError("NO_POSITION", f"You do not hold any {symbol}. Short selling is not allowed by the mandate.")
            if qty > h.qty:
                raise ActionError("INSUFFICIENT_SHARES", f"Cannot sell {qty:,} shares; you only hold {h.qty:,}.")
            target = stoploss = None
        if target is not None and target <= ref:
            raise ActionError("INVALID_TARGET", "The target must be above the entry price.")
        if stoploss is not None and stoploss >= ref:
            raise ActionError("INVALID_STOPLOSS", "The stop-loss must be below the entry price.")
        now = s.now
        order = Order(id=s.next_id("ORD"), symbol=symbol, side=side, type=otype, qty=qty,
                      price=round(price, 2) if price and otype in ("LIMIT", "SL") else None,
                      trigger=round(trigger, 2) if trigger and otype in ("SL", "SL-M") else None,
                      validity=validity, created=now, updated=now,
                      target=round(target, 2) if target else None, stoploss=round(stoploss, 2) if stoploss else None)
        if otype == "MARKET":
            res = self.trade(side, symbol, qty)
            tx = s.transactions[-1]
            order.status, order.fill_price, order.tx_id = "EXECUTED", tx.price, tx.id
            self._add_order(order)
            self._bracket(order)
            return {"order": order.model_dump(mode="json"), "transaction": res["transaction"],
                    "interrupted_by": res["interrupted_by"]}
        self._begin_action()
        self._add_order(order)
        # A limit priced through the market fills straight away at the market (never worse than the limit).
        if otype == "LIMIT" and market_status(now) == "OPEN" and (
                (side == "BUY" and price >= ltp) or (side == "SELL" and price <= ltp)):
            px = min(price, ltp * (1 + pe._impact(s, symbol, qty))) if side == "BUY" else max(price, ltp * (1 - pe._impact(s, symbol, qty)))
            self._fill(order, px)
        self.save_rng()
        return {"order": order.model_dump(mode="json"), "interrupted_by": self.interrupts}

    def _add_order(self, order: Order) -> None:
        s = self.state
        s.orders.append(order)
        if len(s.orders) > 250:
            live = [o for o in s.orders if o.status in ("OPEN", "TRIGGERED")]
            done = [o for o in s.orders if o.status not in ("OPEN", "TRIGGERED")][-200:]
            s.orders = sorted(live + done, key=lambda o: o.created)

    def _bracket(self, parent: Order) -> None:
        """After a bracketed BUY fills, rest a target (sell limit) and a stop (sell SL-M) on the filled quantity."""
        s = self.state
        if parent.side != "BUY" or parent.status != "EXECUTED" or not (parent.target or parent.stoploss):
            return
        group = s.next_id("OCO") if parent.target and parent.stoploss else None
        if parent.target:
            self._add_order(Order(id=s.next_id("ORD"), symbol=parent.symbol, side="SELL", type="LIMIT", qty=parent.qty,
                                  price=parent.target, validity="GTC", created=s.now, updated=s.now, tag="TARGET",
                                  group=group))
        if parent.stoploss:
            self._add_order(Order(id=s.next_id("ORD"), symbol=parent.symbol, side="SELL", type="SL-M", qty=parent.qty,
                                  trigger=parent.stoploss, validity="GTC", created=s.now, updated=s.now, tag="STOPLOSS",
                                  group=group))

    def _fill(self, o: Order, px: float) -> bool:
        s = self.state
        px = round(px, 2)
        try:
            if o.side == "BUY":
                tx = pe.execute_buy(s, o.symbol, o.qty, source="ORDER", price_override=px)
            else:
                h = s.portfolio.holdings.get(o.symbol)
                if h and o.tag in ("TARGET", "STOPLOSS") and h.qty < o.qty:
                    o.qty = h.qty  # part of the position was sold by hand: close what is left
                if o.qty <= 0:
                    raise pe.TradeError("NO_POSITION", f"You no longer hold {o.symbol}.")
                tx = pe.execute_sell(s, o.symbol, o.qty, source="ORDER", price_override=px)
        except pe.TradeError as e:
            o.status, o.reason, o.updated = "REJECTED", e.message, s.now
            self.notify("TRADE", "Order rejected", f"{o.side} {o.qty:,} {o.symbol}: {e.message}")
            if o.group:
                self._cancel_group(o)
            return False
        o.status, o.fill_price, o.tx_id, o.updated = "EXECUTED", tx.price, tx.id, s.now
        self._tx_stats(tx)
        label = {"TARGET": "Target hit", "STOPLOSS": "Stop-loss hit"}.get(o.tag, f"{o.type} order executed")
        self.notify("TRADE", label, f"{tx.side} {tx.qty:,} {o.symbol} @ ₹{tx.price:,.2f} · {self._cr(tx.value)}"
                    + (f" · P&L {self._cr(tx.realized_pnl)}" if tx.side == "SELL" else ""))
        if o.group:
            self._cancel_group(o)
        self._bracket(o)
        self._compliance_check(tx)
        self._risk_check()
        return True

    def _cancel_group(self, o: Order) -> None:
        for other in self.state.orders:
            if other.group == o.group and other.id != o.id and other.status in ("OPEN", "TRIGGERED"):
                other.status, other.reason, other.updated = "CANCELLED", "Other leg of the bracket closed", self.state.now

    @staticmethod
    def _first(mask: np.ndarray, start: int = 0) -> Optional[int]:
        idx = np.flatnonzero(mask[start:])
        return int(idx[0]) + start if len(idx) else None

    def _order_fire(self, o: Order, b: np.ndarray) -> tuple[Optional[int], float]:
        """First minute (row of b = [open, high, low, close]) at which a resting order fills, and its price."""
        op, hi, lo = b[:, 0], b[:, 1], b[:, 2]
        buy = o.side == "BUY"
        start = 0
        if o.type == "SL-M":
            i = self._first(hi >= o.trigger) if buy else self._first(lo <= o.trigger)
            if i is None:
                return None, 0.0
            slip = pe._impact(self.state, o.symbol, o.qty)
            px = max(o.trigger, op[i]) * (1 + slip) if buy else min(o.trigger, op[i]) * (1 - slip)
            return i, float(px)
        if o.type == "SL" and o.status == "OPEN":
            i = self._first(hi >= o.trigger) if buy else self._first(lo <= o.trigger)
            if i is None:
                return None, 0.0
            o.status, o.updated = "TRIGGERED", self.state.now
            start = i
        # LIMIT, or a triggered stop-limit resting as a limit
        j = self._first(lo <= o.price, start) if buy else self._first(hi >= o.price, start)
        if j is None:
            return None, 0.0
        ref = op[j] if j > start or o.type == "LIMIT" else (max(op[j], o.trigger) if buy else min(op[j], o.trigger))
        return j, float(min(o.price, ref) if buy else max(o.price, ref))

    def _check_resting(self, bars: dict[str, np.ndarray], t0: datetime) -> None:
        s = self.state
        orders = [o for o in s.orders if o.status in ("OPEN", "TRIGGERED")]
        alerts = [a for a in s.alerts if a.status == "ACTIVE"]
        if not orders and not alerts:
            return
        fires = []
        for o in orders:
            b = bars.get(o.symbol)
            if b is not None:
                i, px = self._order_fire(o, b)
                if i is not None:
                    fires.append((i, o.created, o, px))
        for i, _, o, px in sorted(fires, key=lambda f: (f[0], f[1])):
            if o.status in ("OPEN", "TRIGGERED"):  # a bracket sibling may have cancelled it
                self._fill(o, px)
        for a in alerts:
            b = bars.get(a.symbol)
            if b is None:
                continue
            hit = self._first(b[:, 1] >= a.price) if a.op == "ABOVE" else self._first(b[:, 2] <= a.price)
            if hit is not None:
                a.status, a.triggered_at = "TRIGGERED", t0 + timedelta(minutes=hit + 1)
                name = s.stocks[a.symbol].name if a.symbol in s.stocks else a.symbol
                self.notify("PRICE_ALERT", f"Alert: {a.symbol} {'above' if a.op == 'ABOVE' else 'below'} ₹{a.price:,.2f}",
                            f"{name} traded at ₹{float(b[hit, 3]):,.2f}." + (f" Note: {a.note}" if a.note else ""))

    def modify_order(self, order_id: str, qty: Optional[int] = None, price: Optional[float] = None,
                     trigger: Optional[float] = None) -> dict:
        self._require_active()
        s = self.state
        o = next((x for x in s.orders if x.id == order_id), None)
        if not o or o.status not in ("OPEN", "TRIGGERED"):
            raise ActionError("INVALID_ORDER", "That order is no longer open.")
        ltp = s.stocks[o.symbol].price
        if qty is not None:
            if not isinstance(qty, int) or qty <= 0:
                raise ActionError("INVALID_QUANTITY", "Quantity must be a positive whole number.")
            o.qty = qty
        for v, label in ((price, "Limit price"), (trigger, "Trigger price")):
            if v is not None and not (0.8 * ltp <= v <= 1.2 * ltp):
                raise ActionError("PRICE_OUT_OF_RANGE", f"{label} must be within 20% of the last traded price (₹{ltp:,.2f}).")
        if price is not None:
            if o.type not in ("LIMIT", "SL"):
                raise ActionError("INVALID_PRICE", "This order has no limit price.")
            o.price = round(price, 2)
        if trigger is not None:
            if o.type not in ("SL", "SL-M"):
                raise ActionError("INVALID_TRIGGER", "This order has no trigger price.")
            if o.status == "OPEN" and ((o.side == "BUY" and trigger <= ltp) or (o.side == "SELL" and trigger >= ltp)):
                raise ActionError("INVALID_TRIGGER", "That trigger would fire immediately. Use a market order instead.")
            o.trigger = round(trigger, 2)
        o.updated = s.now
        if o.type == "LIMIT" and market_status(s.now) == "OPEN" and (
                (o.side == "BUY" and o.price >= ltp) or (o.side == "SELL" and o.price <= ltp)):
            self._fill(o, ltp)
        return {"order": o.model_dump(mode="json")}

    def cancel_order(self, order_id: str) -> dict:
        s = self.state
        o = next((x for x in s.orders if x.id == order_id), None)
        if not o or o.status not in ("OPEN", "TRIGGERED"):
            raise ActionError("INVALID_ORDER", "That order is no longer open.")
        o.status, o.reason, o.updated = "CANCELLED", "Cancelled by you", s.now
        return {"order": o.model_dump(mode="json")}

    def _expire_day_orders(self) -> None:
        s = self.state
        for o in s.orders:
            if o.status in ("OPEN", "TRIGGERED") and o.validity == "DAY":
                o.status, o.reason, o.updated = "EXPIRED", "Day order expired at the close", s.now

    # ---------------------------------------------------------------- alerts
    def add_alert(self, symbol: str, price: float, note: str = "") -> dict:
        s = self.state
        symbol = (symbol or "").upper()
        if symbol not in s.stocks and symbol not in s.indices:
            raise ActionError("INVALID_SYMBOL", f"Unknown symbol '{symbol}'.")
        if not price or price <= 0:
            raise ActionError("INVALID_PRICE", "Enter an alert price.")
        ltp = s.stocks[symbol].price if symbol in s.stocks else s.indices[symbol].value
        if abs(price / ltp - 1) < 1e-6:
            raise ActionError("INVALID_PRICE", "The alert price equals the current price.")
        active = [a for a in s.alerts if a.status == "ACTIVE"]
        if len(active) >= 50:
            raise ActionError("TOO_MANY_ALERTS", "You can keep up to 50 active alerts.")
        a = PriceAlert(id=s.next_id("ALR"), symbol=symbol, op="ABOVE" if price > ltp else "BELOW", price=round(price, 2),
                       created=s.now, note=(note or "")[:120])
        s.alerts.append(a)
        s.alerts = [x for x in s.alerts if x.status == "ACTIVE"] + [x for x in s.alerts if x.status != "ACTIVE"][-50:]
        return {"alert": a.model_dump(mode="json")}

    def cancel_alert(self, alert_id: str) -> dict:
        a = next((x for x in self.state.alerts if x.id == alert_id), None)
        if not a or a.status != "ACTIVE":
            raise ActionError("INVALID_ALERT", "That alert is not active.")
        a.status = "CANCELLED"
        return {"alert": a.model_dump(mode="json")}

    # ---------------------------------------------------------------- research desk
    def _finish_research(self) -> None:
        s = self.state
        for job in [j for j in s.research_jobs if s.now >= j.ready_at]:
            s.research_jobs.remove(job)
            report = research_engine.run_research(s, self.rng, job.symbol, job.depth)
            ce.add_xp(s, 15 if job.depth == "QUICK" else 35)
            self.notify("RESEARCH", f"Research ready: {s.stocks[job.symbol].name}",
                        f"{report.rating} · est. fair value ₹{report.est_fair_value:,.0f}")
