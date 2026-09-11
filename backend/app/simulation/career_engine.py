from dataclasses import dataclass
from typing import Optional

from app.simulation.constants import CAREER_LEVELS


@dataclass
class CareerUpdate:
    xp_gained: int
    reputation_change: float
    level_up: bool
    new_level: Optional[int]
    notification: Optional[str]


@dataclass
class QuarterlyReviewResult:
    outcome: str
    final_return: float
    target_return: float
    max_drawdown: float
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
    failure_count: int = 0
    demoted: bool = False
    terminated: bool = False


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
        xp_gain = 1
        reputation_change = 0.0

        if total_return_pct > 0:
            xp_gain += min(5, int(total_return_pct * 0.5))

        if target_progress >= 1.0:
            xp_gain += 1

        if total_return_pct > 0.1:
            reputation_change += 0.02
        elif total_return_pct < -0.5:
            reputation_change -= 0.05

        if risk_assessment and risk_assessment.is_violation:
            xp_gain = max(0, xp_gain - 2)
            reputation_change -= 0.1

        return CareerUpdate(
            xp_gained=xp_gain,
            reputation_change=reputation_change,
            level_up=False,
            new_level=None,
            notification=None,
        )

    @staticmethod
    def quarterly_review(
        career_level: int,
        reputation: float,
        xp: int,
        total_return_pct: float,
        quarterly_target_return: float,
        max_drawdown: float,
        max_drawdown_limit: float,
        risk_violations_count: int,
        failure_count: int = 0,
    ) -> QuarterlyReviewResult:

        current_level = CAREER_LEVELS.get(career_level, CAREER_LEVELS[1])
        max_level = max(CAREER_LEVELS)

        target_met = total_return_pct >= quarterly_target_return
        drawdown_ok = max_drawdown <= max_drawdown_limit * 100
        risk_ok = risk_violations_count == 0
        reputation_ok = reputation >= 30

        performance_score = CareerEngine._performance_score(
            total_return_pct=total_return_pct,
            target_return=quarterly_target_return,
            max_drawdown=max_drawdown,
            max_drawdown_limit=max_drawdown_limit,
            risk_violations_count=risk_violations_count,
            reputation=reputation,
        )

        passed = (
            target_met
            and drawdown_ok
            and risk_ok
            and reputation_ok
            and performance_score >= 70
        )

        xp_awarded = 0
        reputation_change = 0.0

        if passed:
            new_failure_count = 0
            xp_awarded = 500
            reputation_change = 15.0

            if career_level >= max_level:
                return QuarterlyReviewResult(
                    outcome="TARGET_ACHIEVED",
                    final_return=round(total_return_pct, 2),
                    target_return=quarterly_target_return,
                    max_drawdown=round(max_drawdown, 2),
                    reputation=reputation,
                    xp=xp,
                    summary=(
                        f"Exceptional performance. You achieved "
                        f"{total_return_pct:.1f}% against the "
                        f"{quarterly_target_return:.1f}% target while "
                        f"maintaining acceptable risk."
                    ),
                    ceo_message=(
                        "You've reached the highest level. "
                        "Now the expectation is to defend the franchise."
                    ),
                    next_capital=None,
                    xp_awarded=xp_awarded,
                    reputation_change=reputation_change,
                    can_advance=False,
                    next_level=None,
                    next_role_title=None,
                    capital_injection=0.0,
                    capital_injection_cr=0.0,
                    next_target_return=None,
                    next_drawdown_limit=None,
                    next_perks=current_level.get("perks", []),
                    failure_count=new_failure_count,
                )

            next_level = career_level + 1
            next_data = CAREER_LEVELS[next_level]
            capital_injection = next_data.get("capital_injection", 0.0)

            return QuarterlyReviewResult(
                outcome="PROMOTED",
                final_return=round(total_return_pct, 2),
                target_return=quarterly_target_return,
                max_drawdown=round(max_drawdown, 2),
                reputation=reputation,
                xp=xp,
                summary=(
                    f"Target achieved with a performance score of "
                    f"{performance_score:.1f}. You have earned promotion "
                    f"to Level {next_level}."
                ),
                ceo_message=(
                    f"Excellent work. You've earned your promotion to "
                    f"{next_data['title']}."
                ),
                next_capital=next_data.get("starting_capital"),
                xp_awarded=xp_awarded,
                reputation_change=reputation_change,
                can_advance=True,
                next_level=next_level,
                next_role_title=next_data.get("title"),
                capital_injection=capital_injection,
                capital_injection_cr=round(
                    capital_injection / 10_000_000,
                    2,
                ),
                next_target_return=next_data.get("target_return_pct"),
                next_drawdown_limit=round(
                    next_data.get("max_drawdown_limit", 0.10) * 100,
                    2,
                ),
                next_perks=next_data.get("perks", []),
                failure_count=new_failure_count,
            )

        new_failure_count = failure_count + 1

        if new_failure_count == 1:
            xp_awarded = 150
            reputation_change = -5.0

            return QuarterlyReviewResult(
                outcome="WARNING",
                final_return=round(total_return_pct, 2),
                target_return=quarterly_target_return,
                max_drawdown=round(max_drawdown, 2),
                reputation=reputation,
                xp=xp,
                summary=CareerEngine._failure_summary(
                    total_return_pct,
                    quarterly_target_return,
                    max_drawdown,
                    max_drawdown_limit,
                    risk_violations_count,
                    performance_score,
                ),
                ceo_message=(
                    "This quarter fell short of expectations. "
                    "This is your first warning. You have one more chance "
                    "to demonstrate that you can perform at this level."
                ),
                next_capital=None,
                xp_awarded=xp_awarded,
                reputation_change=reputation_change,
                can_advance=False,
                next_level=None,
                next_role_title=None,
                capital_injection=0.0,
                capital_injection_cr=0.0,
                next_target_return=quarterly_target_return,
                next_drawdown_limit=round(
                    max_drawdown_limit * 100,
                    2,
                ),
                next_perks=current_level.get("perks", []),
                failure_count=new_failure_count,
            )

        if career_level == 1:
            return QuarterlyReviewResult(
                outcome="TERMINATED",
                final_return=round(total_return_pct, 2),
                target_return=quarterly_target_return,
                max_drawdown=round(max_drawdown, 2),
                reputation=reputation,
                xp=xp,
                summary=(
                    "Performance remained below the required standard "
                    "after a previous warning."
                ),
                ceo_message=(
                    "We gave you another opportunity, but the required "
                    "improvement did not materialize. Your employment is "
                    "terminated."
                ),
                next_capital=None,
                xp_awarded=50,
                reputation_change=-20.0,
                can_advance=False,
                next_level=None,
                next_role_title=None,
                capital_injection=0.0,
                capital_injection_cr=0.0,
                next_target_return=None,
                next_drawdown_limit=None,
                next_perks=[],
                failure_count=new_failure_count,
                terminated=True,
            )

        previous_level = career_level
        next_level = career_level - 1
        next_data = CAREER_LEVELS[next_level]

        return QuarterlyReviewResult(
            outcome="FAILED",
            final_return=round(total_return_pct, 2),
            target_return=quarterly_target_return,
            max_drawdown=round(max_drawdown, 2),
            reputation=reputation,
            xp=xp,
            summary=(
                f"Performance remained below the Level {previous_level} "
                f"standard after a previous warning. You have been "
                f"demoted to Level {next_level}."
            ),
            ceo_message=(
                f"This is your second consecutive failure. "
                f"You will remain with the firm, but you are being "
                f"demoted to {next_data['title']}."
            ),
            next_capital=next_data.get("starting_capital"),
            xp_awarded=50,
            reputation_change=-10.0,
            can_advance=False,
            next_level=next_level,
            next_role_title=next_data.get("title"),
            capital_injection=0.0,
            capital_injection_cr=0.0,
            next_target_return=next_data.get("target_return_pct"),
            next_drawdown_limit=round(
                next_data.get("max_drawdown_limit", 0.10) * 100,
                2,
            ),
            next_perks=next_data.get("perks", []),
            failure_count=0,
            demoted=True,
        )

    @staticmethod
    def _performance_score(
        total_return_pct: float,
        target_return: float,
        max_drawdown: float,
        max_drawdown_limit: float,
        risk_violations_count: int,
        reputation: float,
    ) -> float:
        if target_return <= 0:
            return 0.0

        return_score = min(
            100.0,
            max(0.0, (total_return_pct / target_return) * 100),
        )

        drawdown_limit_pct = max_drawdown_limit * 100

        if drawdown_limit_pct <= 0:
            risk_score = 0.0
        elif max_drawdown <= drawdown_limit_pct:
            risk_score = 100.0
        else:
            excess = max_drawdown - drawdown_limit_pct
            risk_score = max(
                0.0,
                100.0 - (excess / drawdown_limit_pct) * 100,
            )

        violation_score = max(
            0.0,
            100.0 - (risk_violations_count * 20.0),
        )

        reputation_score = min(
            100.0,
            max(0.0, reputation),
        )

        return (
            return_score * 0.45
            + risk_score * 0.25
            + violation_score * 0.15
            + reputation_score * 0.15
        )

    @staticmethod
    def _failure_summary(
        total_return_pct: float,
        target_return: float,
        max_drawdown: float,
        max_drawdown_limit: float,
        risk_violations_count: int,
        performance_score: float,
    ) -> str:
        reasons = []

        if total_return_pct < target_return:
            reasons.append(
                f"return {total_return_pct:.1f}% was below "
                f"the {target_return:.1f}% target"
            )

        if max_drawdown > max_drawdown_limit * 100:
            reasons.append(
                f"drawdown {max_drawdown:.1f}% exceeded the "
                f"{max_drawdown_limit * 100:.1f}% limit"
            )

        if risk_violations_count > 0:
            reasons.append(
                f"{risk_violations_count} risk violation(s) occurred"
            )

        if not reasons:
            reasons.append("overall performance was below the required standard")

        return (
            f"Quarterly performance score: {performance_score:.1f}. "
            + "; ".join(reasons)
            + "."
        )

    @staticmethod
    def get_role_title(level: int) -> str:
        return CAREER_LEVELS.get(
            level,
            CAREER_LEVELS[1],
        ).get(
            "title",
            "Investment Professional",
        )