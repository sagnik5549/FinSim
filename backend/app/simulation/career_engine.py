"""
Career engine — targets, reputation, XP, warnings and the quarterly review.

The review judges several dimensions, not just profit:
  return vs target, drawdown vs mandate, risk-policy conduct, reputation and
  decision quality (research-backed theses that proved right).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from app.simulation import portfolio_engine as pe
from app.simulation.constants import CAREER_LEVELS, CRORE, MAX_LEVEL, QUARTER_DAYS, TERMINATION_DRAWDOWN, XP_PER_LEVEL
from app.simulation.state import Career, GameState, ReviewRecord

MILESTONES = (0.25, 0.5, 0.75, 0.9, 1.0)


def new_career(start: datetime, capital: float, reputation: float) -> Career:
    lvl = CAREER_LEVELS[1]
    return Career(
        level=1, title=lvl["title"], reputation=reputation, quarter_index=1, quarter_start=start,
        quarter_end=start + timedelta(days=QUARTER_DAYS), target_value=capital * (1 + lvl["target_return"]),
        target_return=lvl["target_return"], max_drawdown_limit=lvl["max_drawdown"], reputation_at_quarter_start=reputation,
    )


def target_progress(state: GameState) -> float:
    c = state.career
    start = state.portfolio.quarter_start_value
    need = c.target_value - start
    return (pe.nav(state) - start) / need if need else 0.0


def time_progress(state: GameState) -> float:
    c = state.career
    return min(1.0, max(0.0, (state.now - c.quarter_start) / (c.quarter_end - c.quarter_start)))


def add_rep(state: GameState, delta: float, reason: str = "") -> float:
    c = state.career
    before = c.reputation
    c.reputation = float(np.clip(c.reputation + delta, 0, 100))
    return c.reputation - before


def add_xp(state: GameState, xp: int) -> None:
    state.career.xp = max(0, state.career.xp + int(xp))


def xp_bounds(level: int) -> tuple[int, int]:
    return XP_PER_LEVEL[level - 1], XP_PER_LEVEL[min(level, len(XP_PER_LEVEL) - 1)]


def log_decision(state: GameState, kind: str, text: str, impact: str = "") -> None:
    state.career.decisions.append({"t": state.now.isoformat(), "kind": kind, "text": text, "impact": impact})
    state.career.decisions = state.career.decisions[-60:]


def daily_reputation(state: GameState, day_ret: float, bench_ret: float, ignored_recent: int) -> float:
    """Small daily drift: beating the benchmark builds credibility; freshly ignored breaches erode it."""
    excess = (day_ret - bench_ret) * 100
    delta = float(np.clip(excess * 0.35, -0.8, 0.8)) - min(1.0, 0.5 * ignored_recent)
    return add_rep(state, delta)


def check_milestones(state: GameState) -> list[float]:
    prog = target_progress(state)
    hit = []
    for m in MILESTONES:
        key = f"Q{state.career.quarter_index}-{int(m * 100)}"
        if prog >= m and key not in state.career.milestones_hit:
            state.career.milestones_hit.append(key)
            hit.append(m)
            add_xp(state, 60 if m < 1 else 250)
            if m >= 1:
                add_rep(state, 3)
    return hit


def drawdown_check(state: GameState) -> str | None:
    """Returns 'TERMINATE', 'WARN' or None."""
    dd = pe.current_drawdown(state)
    c = state.career
    if dd >= TERMINATION_DRAWDOWN:
        return "TERMINATE"
    if dd > c.max_drawdown_limit and not c.dd_breach_warned:
        c.dd_breach_warned = True
        return "WARN"
    return None


def escalate_warning(state: GameState) -> str:
    c = state.career
    c.warning_level += 1
    if c.warning_level >= 3:
        c.status = "TERMINATED"
        return "TERMINATED"
    return "FINAL WARNING" if c.warning_level == 2 else "WARNING"


# --------------------------------------------------------------------------- #
# Decision quality
# --------------------------------------------------------------------------- #
def thesis_accuracy(state: GameState) -> dict[str, Any]:
    q_start = state.career.quarter_start
    items = [t for t in state.theses if t.time >= q_start and t.stance != "NEUTRAL"]
    right = 0
    for t in items:
        move = state.stocks[t.symbol].price / t.price_at - 1
        if (t.stance == "BULLISH" and move > 0.01) or (t.stance == "BEARISH" and move < -0.01):
            right += 1
    return {"count": len(items), "correct": right, "accuracy": right / len(items) if items else None}


def best_and_worst(state: GameState) -> tuple[dict | None, dict | None]:
    q_start = state.career.quarter_start.isoformat()
    closed = [t for t in state.stats.closed_trades if t["t"] >= q_start]
    open_pos = [{"symbol": h.symbol, "pnl": round(h.qty * (state.stocks[h.symbol].price - h.avg_cost), 2),
                 "pct": round(state.stocks[h.symbol].price / h.avg_cost - 1, 4), "open": True}
                for h in state.portfolio.holdings.values()]
    agg: dict[str, dict] = {}
    for t in closed + open_pos:
        a = agg.setdefault(t["symbol"], {"symbol": t["symbol"], "pnl": 0.0})
        a["pnl"] += t["pnl"]
    if not agg:
        return None, None
    ranked = sorted(agg.values(), key=lambda x: x["pnl"])
    for r in ranked:
        r["name"] = state.stocks[r["symbol"]].name
        r["pnl"] = round(r["pnl"], 2)
    return ranked[-1], ranked[0]


# --------------------------------------------------------------------------- #
# Quarterly review
# --------------------------------------------------------------------------- #
def quarterly_review(state: GameState) -> dict[str, Any]:
    c = state.career
    p = state.portfolio
    end_value = pe.nav(state)
    ret = end_value / p.quarter_start_value - 1
    bench_ret = state.indices["BH50"].value / p.quarter_start_bench - 1
    target = c.target_return
    mdd = p.max_drawdown
    ignored = c.ignored_violations
    dq = thesis_accuracy(state)
    best, worst = best_and_worst(state)

    # Scorecard: each dimension 0..100
    s_return = float(np.clip(50 + (ret / target) * 50 if target else 50, 0, 100))
    s_risk = float(np.clip(100 - (mdd / c.max_drawdown_limit) * 60 - ignored * 12 - c.compliance_strikes * 8, 0, 100))
    s_rep = c.reputation
    s_alpha = float(np.clip(50 + (ret - bench_ret) * 500, 0, 100))
    s_dq = 50.0 if dq["accuracy"] is None else float(np.clip(dq["accuracy"] * 100, 0, 100))
    overall = 0.40 * s_return + 0.25 * s_risk + 0.15 * s_rep + 0.12 * s_alpha + 0.08 * s_dq

    hit_target = ret >= target - 1e-9
    dd_ok = mdd <= c.max_drawdown_limit
    conduct_ok = ignored <= 1 and c.compliance_strikes <= 2

    if mdd >= TERMINATION_DRAWDOWN or c.reputation < 20:
        outcome = "TERMINATED"
    elif hit_target and dd_ok and conduct_ok and c.reputation >= 55:
        outcome = "PROMOTED" if c.level < MAX_LEVEL else "TARGET ACHIEVED"
    elif hit_target:
        outcome = "TARGET ACHIEVED"
    elif overall >= 55 and ret > 0:
        outcome = "WARNING"
    elif overall >= 40:
        outcome = "WARNING"
    else:
        outcome = "FAILED"

    # Warning ladder: WARNING -> FINAL WARNING -> TERMINATED (FAILED also costs more reputation).
    ladder_note = None
    if outcome in ("WARNING", "FAILED"):
        c.warning_level += 1
        if c.warning_level >= 3:
            outcome, ladder_note = "TERMINATED", "Previous warnings exhausted."
        elif c.warning_level == 2:
            ladder_note = "FINAL WARNING — one more miss and the board will let you go."
    elif outcome in ("PROMOTED", "TARGET ACHIEVED"):
        c.warning_level = max(0, c.warning_level - 1)

    rep_delta = {"PROMOTED": 8, "TARGET ACHIEVED": 4, "WARNING": -4, "FAILED": -10, "TERMINATED": -15}[outcome]
    rep_delta += float(np.clip((ret - bench_ret) * 40, -4, 4))
    rep_before = c.reputation
    add_rep(state, rep_delta)
    xp_gain = {"PROMOTED": 800, "TARGET ACHIEVED": 500, "WARNING": 150, "FAILED": 50, "TERMINATED": 0}[outcome]
    add_xp(state, xp_gain)

    ceo_lines = _ceo_verdict(outcome, ret, target, mdd, c.max_drawdown_limit)
    if outcome in ("TERMINATED", "FAILED", "WARNING", "TARGET ACHIEVED") and (ignored > 1 or c.compliance_strikes > 2 or rep_before < 30):
        why = []
        if ignored > 1:
            why.append(f"you overruled the risk desk {ignored} times")
        if c.compliance_strikes > 2:
            why.append(f"compliance filed {c.compliance_strikes} strikes")
        if rep_before < 30:
            why.append("your standing with the board collapsed")
        ceo_lines = ceo_lines[:1] + [("The numbers aren't the whole story: " + ", ".join(why) + ".").capitalize()] + ceo_lines[1:]
    cfo_line = (f"Return {ret * 100:+.2f}% against a {target * 100:.0f}% target; benchmark {bench_ret * 100:+.2f}%. "
                f"Fees paid ₹{p.fees_paid / 1e5:,.1f} lakh.")
    risk_line = (f"Peak-to-trough drawdown {mdd * 100:.2f}% vs {c.max_drawdown_limit * 100:.0f}% limit. "
                 f"{c.risk_violations} policy breaches, {ignored} ignored, {c.exceptions_granted} exceptions granted.")

    review = {
        "quarter": c.quarter_index, "level": c.level, "title": c.title, "outcome": outcome,
        "start_value": p.quarter_start_value, "end_value": end_value, "return_pct": ret, "target_pct": target,
        "target_value": c.target_value, "benchmark_pct": bench_ret, "max_drawdown": mdd,
        "drawdown_limit": c.max_drawdown_limit, "risk_violations": c.risk_violations, "ignored_violations": ignored,
        "compliance_strikes": c.compliance_strikes, "reputation_before": rep_before, "reputation_after": c.reputation,
        "reputation_change": c.reputation - rep_before, "xp_gain": xp_gain,
        "scores": {"return": round(s_return), "risk": round(s_risk), "reputation": round(s_rep),
                   "alpha": round(s_alpha), "decision_quality": round(s_dq), "overall": round(overall)},
        "decision_quality": dq, "best_decision": best, "worst_decision": worst,
        "ceo": ceo_lines, "cfo": cfo_line, "risk_manager": risk_line, "ladder_note": ladder_note,
        "warning_level": c.warning_level,
        "next_level": (CAREER_LEVELS[c.level + 1]["title"] if outcome == "PROMOTED" else None),
        "unlocks": (CAREER_LEVELS[c.level + 1]["unlocks"] if outcome == "PROMOTED" else []),
    }
    c.history.append(ReviewRecord(
        quarter=c.quarter_index, level=c.level, title=c.title, outcome=outcome, start_value=p.quarter_start_value,
        end_value=end_value, return_pct=ret, target_pct=target, max_drawdown=mdd,
        reputation_change=c.reputation - rep_before, date=state.now.date().isoformat()))
    c.last_review = review
    c.status = "TERMINATED" if outcome == "TERMINATED" else "REVIEW"
    if outcome == "PROMOTED":
        c.achievements.append(f"Promoted to {CAREER_LEVELS[c.level + 1]['title']} (Q{c.quarter_index})")
    if hit_target and f"target-q{c.quarter_index}" not in c.achievements:
        c.achievements.append(f"Quarterly target achieved (Q{c.quarter_index})")
    return review


def _ceo_verdict(outcome, ret, target, mdd, limit) -> list[str]:
    if outcome == "PROMOTED":
        return ["Outstanding quarter.", f"{ret * 100:.1f}% with the risk book under control. That's what I hired you for.",
                "The board has approved your promotion."]
    if outcome == "TARGET ACHIEVED":
        return ["You hit the number.", "But I need to see cleaner risk management before I put more capital behind you."]
    if outcome == "WARNING":
        return ["We missed the target.", f"{ret * 100:.1f}% against {target * 100:.0f}%. I expected more.",
                "Consider this a formal warning."]
    if outcome == "FAILED":
        return ["This quarter was not acceptable.", "Performance was well short of mandate.",
                "You are on a final warning."]
    return ["I'm sorry. The board has lost confidence.", "Your mandate at Apex Capital is terminated, effective today."]


def begin_next_quarter(state: GameState) -> None:
    """After a non-terminal review: roll targets forward (and apply promotion)."""
    c = state.career
    review = c.last_review or {}
    if review.get("outcome") == "PROMOTED" and c.level < MAX_LEVEL:
        c.level += 1
        lvl = CAREER_LEVELS[c.level]
        c.title = lvl["title"]
        state.portfolio.cash += lvl["capital_add"]
    lvl = CAREER_LEVELS[c.level]
    start_value = pe.nav(state)
    c.quarter_index += 1
    c.quarter_start = state.now
    c.quarter_end = state.now + timedelta(days=QUARTER_DAYS)
    c.target_return = lvl["target_return"]
    c.target_value = start_value * (1 + lvl["target_return"])
    c.max_drawdown_limit = lvl["max_drawdown"]
    c.risk_violations = 0
    c.ignored_violations = 0
    c.exceptions_granted = 0
    c.compliance_strikes = 0
    c.dd_breach_warned = False
    c.reputation_at_quarter_start = c.reputation
    c.status = "ACTIVE"
    p = state.portfolio
    p.quarter_start_value = start_value
    p.quarter_start_bench = state.indices["BH50"].value
    p.peak_value = start_value
    p.max_drawdown = 0.0


def capital_label(v: float) -> str:
    return f"₹{v / CRORE:,.2f} Cr"
