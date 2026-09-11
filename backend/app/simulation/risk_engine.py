from dataclasses import dataclass
from typing import Optional

from app.simulation.constants import MAX_DRAWDOWN_LIMIT


SECTOR_LIMIT = 0.40
SINGLE_STOCK_LIMIT = 0.25
MIN_CASH_RATIO = 0.05

HIGH_RISK_THRESHOLD = 60.0
CRITICAL_RISK_THRESHOLD = 80.0

VOLATILITY_WARNING = 0.20
VOLATILITY_HIGH = 0.30


@dataclass
class RiskWarning:
    code: str
    level: str
    message: str
    value: float
    limit: float
    symbol: Optional[str] = None
    sector: Optional[str] = None


@dataclass
class RiskAssessment:
    overall_level: str
    risk_score: float
    warnings: list[RiskWarning]
    drawdown_pct: float
    cash_ratio: float
    largest_position_pct: float
    sector_concentration: dict[str, float]
    is_violation: bool
    portfolio_volatility: float


class RiskEngine:

    @staticmethod
    def _warning_level(
        excess_ratio: float,
    ) -> str:
        if excess_ratio >= 0.40:
            return "CRITICAL"

        if excess_ratio >= 0.20:
            return "HIGH"

        return "MEDIUM"

    @staticmethod
    def assess(
        total_value: float,
        cash: float,
        holdings_detail: list[dict],
        sector_exposure: dict[str, float],
        max_drawdown: float,
        portfolio_volatility: float,
        market_regime: str,
        max_drawdown_limit: float = MAX_DRAWDOWN_LIMIT,
    ) -> RiskAssessment:

        total_value = max(
            0.0,
            float(total_value),
        )

        cash = max(
            0.0,
            float(cash),
        )

        max_drawdown = max(
            0.0,
            float(max_drawdown),
        )

        portfolio_volatility = max(
            0.0,
            float(portfolio_volatility),
        )

        max_drawdown_limit = max(
            0.0,
            float(max_drawdown_limit),
        )

        warnings: list[RiskWarning] = []
        risk_score = 0.0

        cash_ratio = (
            cash / total_value
            if total_value > 0
            else 1.0
        )

        largest_position_pct = 0.0

        for holding in holdings_detail:
            current_value = max(
                0.0,
                float(
                    holding.get(
                        "market_value",
                        holding.get("current_value", 0.0),
                    )
                ),
            )

            position_ratio = (
                current_value / total_value
                if total_value > 0
                else 0.0
            )

            position_pct = (
                position_ratio * 100
            )

            largest_position_pct = max(
                largest_position_pct,
                position_pct,
            )

            if position_ratio > SINGLE_STOCK_LIMIT:
                excess = (
                    position_ratio
                    - SINGLE_STOCK_LIMIT
                )

                severity = (
                    RiskEngine._warning_level(
                        excess
                        / SINGLE_STOCK_LIMIT
                    )
                )

                warnings.append(
                    RiskWarning(
                        code="SINGLE_STOCK_CONCENTRATION",
                        level=severity,
                        message=(
                            f"{holding['symbol']} represents "
                            f"{position_pct:.1f}% of the portfolio. "
                            f"Policy limit: "
                            f"{SINGLE_STOCK_LIMIT * 100:.0f}%."
                        ),
                        value=round(
                            position_pct,
                            2,
                        ),
                        limit=(
                            SINGLE_STOCK_LIMIT
                            * 100
                        ),
                        symbol=holding["symbol"],
                    )
                )

                risk_score += min(
                    30.0,
                    excess * 100 * 1.2,
                )

        normalized_sector_exposure: dict[str, float] = {}

        for sector, exposure in (
            sector_exposure or {}
        ).items():

            exposure = float(exposure)

            if exposure > 1.0:
                exposure /= 100.0

            exposure = max(
                0.0,
                exposure,
            )

            normalized_sector_exposure[
                sector
            ] = exposure

            if exposure > SECTOR_LIMIT:
                excess = (
                    exposure
                    - SECTOR_LIMIT
                )

                severity = (
                    RiskEngine._warning_level(
                        excess
                        / SECTOR_LIMIT
                    )
                )

                warnings.append(
                    RiskWarning(
                        code="SECTOR_CONCENTRATION",
                        level=severity,
                        message=(
                            f"{sector} exposure is "
                            f"{exposure * 100:.1f}% "
                            f"of the portfolio. "
                            f"Policy limit: "
                            f"{SECTOR_LIMIT * 100:.0f}%."
                        ),
                        value=round(
                            exposure * 100,
                            2,
                        ),
                        limit=(
                            SECTOR_LIMIT * 100
                        ),
                        sector=sector,
                    )
                )

                risk_score += min(
                    25.0,
                    excess * 100 * 1.0,
                )

        if (
            total_value > 0
            and cash_ratio < MIN_CASH_RATIO
        ):
            cash_shortfall = (
                MIN_CASH_RATIO
                - cash_ratio
            )

            warnings.append(
                RiskWarning(
                    code="LOW_CASH",
                    level="MEDIUM",
                    message=(
                        f"Cash is only "
                        f"{cash_ratio * 100:.1f}% "
                        f"of the portfolio. "
                        f"Minimum buffer: "
                        f"{MIN_CASH_RATIO * 100:.0f}%."
                    ),
                    value=round(
                        cash_ratio * 100,
                        2,
                    ),
                    limit=(
                        MIN_CASH_RATIO * 100
                    ),
                )
            )

            risk_score += min(
                15.0,
                cash_shortfall * 100,
            )

        drawdown_warning_level = (
            max_drawdown_limit * 0.70
        )

        if (
            max_drawdown_limit > 0
            and max_drawdown >= max_drawdown_limit
        ):
            warnings.append(
                RiskWarning(
                    code="DRAWDOWN_BREACH",
                    level="CRITICAL",
                    message=(
                        f"Portfolio drawdown is "
                        f"{max_drawdown * 100:.1f}%, "
                        f"above the career limit of "
                        f"{max_drawdown_limit * 100:.1f}%."
                    ),
                    value=round(
                        max_drawdown * 100,
                        2,
                    ),
                    limit=round(
                        max_drawdown_limit * 100,
                        2,
                    ),
                )
            )

            risk_score += 35.0

        elif (
            max_drawdown_limit > 0
            and max_drawdown >= drawdown_warning_level
        ):
            progress_to_limit = (
                max_drawdown
                / max_drawdown_limit
            )

            warnings.append(
                RiskWarning(
                    code="DRAWDOWN_WARNING",
                    level="HIGH",
                    message=(
                        f"Portfolio drawdown is "
                        f"{max_drawdown * 100:.1f}%. "
                        f"Career limit: "
                        f"{max_drawdown_limit * 100:.1f}%."
                    ),
                    value=round(
                        max_drawdown * 100,
                        2,
                    ),
                    limit=round(
                        max_drawdown_limit * 100,
                        2,
                    ),
                )
            )

            risk_score += (
                10.0
                + progress_to_limit * 10.0
            )

        regime_risk = {
            "BULL": 0.0,
            "STABLE": 0.0,
            "VOLATILE": 10.0,
            "BEAR": 20.0,
            "CRISIS": 35.0,
        }

        risk_score += regime_risk.get(
            market_regime,
            0.0,
        )

        if portfolio_volatility >= VOLATILITY_HIGH:
            warnings.append(
                RiskWarning(
                    code="HIGH_PORTFOLIO_VOLATILITY",
                    level="HIGH",
                    message=(
                        f"Annualized portfolio volatility "
                        f"is {portfolio_volatility * 100:.1f}%. "
                        f"Risk threshold: "
                        f"{VOLATILITY_HIGH * 100:.0f}%."
                    ),
                    value=round(
                        portfolio_volatility * 100,
                        2,
                    ),
                    limit=(
                        VOLATILITY_HIGH * 100
                    ),
                )
            )

            risk_score += 15.0

        elif (
            portfolio_volatility
            >= VOLATILITY_WARNING
        ):
            warnings.append(
                RiskWarning(
                    code="PORTFOLIO_VOLATILITY_WARNING",
                    level="MEDIUM",
                    message=(
                        f"Annualized portfolio volatility "
                        f"is {portfolio_volatility * 100:.1f}%."
                    ),
                    value=round(
                        portfolio_volatility * 100,
                        2,
                    ),
                    limit=(
                        VOLATILITY_WARNING * 100
                    ),
                )
            )

            risk_score += 8.0

        risk_score = min(
            100.0,
            max(0.0, risk_score),
        )

        if risk_score >= CRITICAL_RISK_THRESHOLD:
            overall_level = "CRITICAL"
        elif risk_score >= HIGH_RISK_THRESHOLD:
            overall_level = "HIGH"
        elif risk_score >= 30.0:
            overall_level = "MEDIUM"
        else:
            overall_level = "LOW"

        is_violation = any(
            warning.level in {
                "HIGH",
                "CRITICAL",
            }
            for warning in warnings
        )

        return RiskAssessment(
            overall_level=overall_level,
            risk_score=round(
                risk_score,
                1,
            ),
            warnings=warnings,
            drawdown_pct=round(
                max_drawdown * 100,
                2,
            ),
            cash_ratio=round(
                cash_ratio * 100,
                2,
            ),
            largest_position_pct=round(
                largest_position_pct,
                2,
            ),
            sector_concentration={
                sector: round(
                    exposure * 100,
                    2,
                )
                for sector, exposure
                in normalized_sector_exposure.items()
            },
            is_violation=is_violation,
            portfolio_volatility=round(
                portfolio_volatility * 100,
                2,
            ),
        )