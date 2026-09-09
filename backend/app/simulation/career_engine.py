"""
CareerEngine — XP, reputation, level progression, and quarterly review logic.
"""
from dataclasses import dataclass
from typing import Optional

from app.simulation.constants import CAREER_LEVELS, CAREER_DAYS


@dataclass
class CareerUpdate:
    xp_gained: int
    reputation_change: float
    level_up: bool
    new_level: Optional[int]
    notification: Optional[str]


@dataclass
class QuarterlyReviewResult:
    outcome: str            # PROMOTED, TARGET_ACHIEVED, WARNING, FAILED, TERMINATED
    final_return: float     # %
    target_return: float    # %
    max_drawdown: float     # %
    reputation: float
    xp: int
    summary: str
    ceo_message: str
    next_capital: Optional[float]
    xp_awarded: int
    reputation_change: float
    can_advance: bool = False
    next_level: Optional[int] = None
    next_role_title: Optional[str] = None
    capital_injection: Optional[float] = 0.0
    capital_injection_cr: Optional[float] = 0.0
    next_target_return: Optional[float] = None
    next_drawdown_limit: Optional[float] = None
    next_perks: Optional[list[str]] = None



class CareerEngine:

    @staticmethod
    def update_per_tick(
        career_level: int,
        xp: int,
        reputation: float,
        total_return_pct: float,
        risk_assessment,
        target_progress: float,
    ) -> CareerUpdate:
        """Small per-tick XP and reputation adjustments."""
        xp_gain = 0
        rep_change = 0.0
        notification = None

        # XP for just staying invested and working
        xp_gain += 1

        # XP based on performance direction
        if total_return_pct > 0:
            xp_gain += min(5, int(total_return_pct * 0.5))

        # Reputation: slight decay each tick unless performing well
        if total_return_pct > 0.1:
            rep_change += 0.02
        elif total_return_pct < -0.5:
            rep_change -= 0.05

        # Risk violations reduce reputation
        if risk_assessment and risk_assessment.is_violation:
            rep_change -= 0.1
            xp_gain = max(0, xp_gain - 2)

        new_rep = max(0.0, min(100.0, reputation + rep_change))
        new_xp = xp + xp_gain

        # Check level up
        current_level_data = CAREER_LEVELS.get(career_level, {})
        next_xp = current_level_data.get("xp_to_next", 9999)
        next_level = career_level + 1
        level_up = False

        if new_xp >= next_xp and next_level in CAREER_LEVELS:
            level_up = True
            notification = f"PROMOTION: You have advanced to {CAREER_LEVELS[next_level]['title']}!"

        return CareerUpdate(
            xp_gained=xp_gain,
            reputation_change=rep_change,
            level_up=level_up,
            new_level=next_level if level_up else None,
            notification=notification,
        )

    @staticmethod
    def quarterly_review(
        career_level: int,
        reputation: float,
        xp: int,
        total_return_pct: float,
        quarterly_target_return: float,  # e.g. 12.0 for 12%
        max_drawdown: float,
        max_drawdown_limit: float,
        risk_violations_count: int,
    ) -> QuarterlyReviewResult:
        """Evaluate end-of-quarter performance and determine career outcome."""
        target_met = total_return_pct >= quarterly_target_return
        drawdown_ok = max_drawdown <= max_drawdown_limit * 100
        rep_ok = reputation >= 30

        xp_award = 0
        rep_change = 0.0
        outcome = ""
        summary = ""
        ceo_msg = ""
        next_capital = None

        if not rep_ok:
            outcome = "TERMINATED"
            summary = "Reputation fell below the minimum acceptable threshold. The board has lost confidence."
            ceo_msg = "I'm sorry. It's time to move on. The firm needs leadership it can trust."
            rep_change = -20.0
            xp_award = 0
        elif max_drawdown > max_drawdown_limit * 100 * 1.5:
            outcome = "TERMINATED"
            summary = f"Drawdown of {max_drawdown:.1f}% far exceeded the firm's {max_drawdown_limit*100:.0f}% policy limit."
            ceo_msg = "Your risk management was unacceptable. We cannot retain you after this."
            rep_change = -15.0
            xp_award = 50
        elif target_met and drawdown_ok:
            outcome = "PROMOTED"
            summary = f"Outstanding performance. Return of {total_return_pct:.1f}% exceeded the {quarterly_target_return:.1f}% target within risk limits."
            ceo_msg = "Exceptional work. You exceeded our target and managed risk well. You're ready for the next level."
            rep_change = 15.0
            xp_award = 500
            next_capital = None  # escalated at Level 2
        elif target_met and not drawdown_ok:
            outcome = "TARGET_ACHIEVED"
            summary = f"Target achieved at {total_return_pct:.1f}% return, but drawdown of {max_drawdown:.1f}% exceeded policy."
            ceo_msg = "You hit the number, but the risk was too high. We'll be watching more carefully next quarter."
            rep_change = 5.0
            xp_award = 300
        elif not target_met and total_return_pct > 0 and drawdown_ok:
            outcome = "WARNING"
            summary = f"Return of {total_return_pct:.1f}% fell short of the {quarterly_target_return:.1f}% target."
            ceo_msg = "You preserved capital, but the board expected more. One more chance."
            rep_change = -5.0
            xp_award = 150
        else:
            outcome = "FAILED"
            summary = f"Return of {total_return_pct:.1f}% missed the target and drawdown was at {max_drawdown:.1f}%."
            ceo_msg = "This was a disappointing quarter. I need to see a serious improvement or we'll have difficult conversations."
            rep_change = -10.0
            xp_award = 50

        can_advance = outcome in ("PROMOTED", "TARGET_ACHIEVED") and (career_level + 1) in CAREER_LEVELS
        next_lvl = career_level + 1 if can_advance else career_level
        lvl_info = CAREER_LEVELS.get(next_lvl, {})
        capital_inj = lvl_info.get("capital_injection", 0.0) if can_advance else 0.0

        return QuarterlyReviewResult(
            outcome=outcome,
            final_return=round(total_return_pct, 2),
            target_return=quarterly_target_return,
            max_drawdown=round(max_drawdown, 2),
            reputation=reputation,
            xp=xp,
            summary=summary,
            ceo_message=ceo_msg,
            next_capital=lvl_info.get("starting_capital"),
            xp_awarded=xp_award,
            reputation_change=rep_change,
            can_advance=can_advance,
            next_level=next_lvl if can_advance else None,
            next_role_title=lvl_info.get("title") if can_advance else None,
            capital_injection=capital_inj,
            capital_injection_cr=round(capital_inj / 10_000_000, 2),
            next_target_return=lvl_info.get("target_return_pct"),
            next_drawdown_limit=round(lvl_info.get("max_drawdown_limit", 0.10) * 100, 2),
            next_perks=lvl_info.get("perks", []),
        )


    @staticmethod
    def get_role_title(level: int) -> str:
        data = CAREER_LEVELS.get(level, {})
        return data.get("title", "Investment Professional")
