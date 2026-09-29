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
    MARKET_OPEN_HOUR,
    PAID_LEAVE_PER_YEAR,
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
    Popup,
    Portfolio,
    Thesis,
)
from app.simulation.time_engine import (
    TimeEngine,
    TimeError,
    business_days_between,
    clock_view,
    is_business_day,
    market_status,
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
        return not any(p.blocking for p in s.popups)

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

    def on_market_hour(self, start: datetime, end: datetime) -> None:
        s = self.state
        s.now = end  # events and bookkeeping in this hook are stamped at the end of the hour
        jumps: dict[str, float] = {}
        # 1. Scheduled events inside (start, end]
        for sch in [x for x in s.scheduled if not x.processed and start < x.time <= end]:
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
        # 2. Spontaneous events
        new_events = self.events.hourly_random(jumps)
        # 3. Active event dynamics
        drift, vboost, mboost = self.events.active_effects()
        # 4. Price simulation
        rets = me.simulate_hour(s, self.rng, start, jumps, drift, vboost, mboost)
        if self.warmup:
            return
        self._post_hour(new_events, rets)

    def _post_hour(self, new_events, rets: dict[str, float]) -> None:
        s = self.state
        pe.record_hour(s)
        for ev in new_events:
            if ev.severity >= 3:
                held = [x for x in ev.affected_symbols if x in s.portfolio.holdings]
                tag = " (you hold this)" if held and ev.category == "company" else ""
                self.notify("BREAKING", ev.title, ev.narrative[:140] + tag)
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
        if clock_view(s).hours_to_close < need:
            raise ActionError("NOT_ENOUGH_TIME", f"A {depth.lower()} review needs {need}h; only "
                                                 f"{clock_view(s).hours_to_close}h left before the close.")
        self._begin_action()
        done = 0
        while done < need and self.can_advance():
            done += self.time.advance_hour()
        s.stats.hours_worked += done
        report = research_engine.run_research(s, self.rng, symbol, depth)
        ce.add_xp(s, 15 if depth == "QUICK" else 35)
        self.notify("MARKET_ALERT", f"Research ready: {s.stocks[symbol].name}",
                    f"{report.rating} · est. fair value ₹{report.est_fair_value:,.0f}")
        self._telemetry("RESEARCH")
        self.save_rng()
        return {"report": report.model_dump(mode="json"), "hours_used": done, "interrupted_by": self.interrupts}

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
