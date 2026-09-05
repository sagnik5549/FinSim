"""
RiskEngine — computes risk metrics and generates warnings.
Risk is a first-class game mechanic with real consequences.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RiskWarning:
    code: str           # e.g. SECTOR_CONCENTRATION
    level: str          # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    value: float        # the actual metric value
    limit: float        # the policy limit
    symbol: Optional[str] = None
    sector: Optional[str] = None


@dataclass
class RiskAssessment:
    overall_level: str          # LOW, MEDIUM, HIGH, CRITICAL
    risk_score: float           # 0–100
    warnings: list[RiskWarning]
    drawdown_pct: float
    cash_ratio: float
    largest_position_pct: float
    sector_concentration: dict[str, float]
    is_violation: bool
    portfolio_volatility: float


# ─── Policy limits ────────────────────────────────────────────────────────────
SECTOR_LIMIT = 0.40          # 40% max in any one sector
SINGLE_STOCK_LIMIT = 0.25    # 25% max in any one stock
MIN_CASH_RATIO = 0.05        # 5% minimum cash
MAX_DRAWDOWN_LIMIT = 0.10    # 10% max drawdown
HIGH_RISK_THRESHOLD = 60     # score > 60 = HIGH
CRITICAL_RISK_THRESHOLD = 80 # score > 80 = CRITICAL


class RiskEngine:

    @staticmethod
    def assess(
        total_value: float,
        cash: float,
        holdings_detail: list[dict],
        sector_exposure: dict[str, float],
        max_drawdown: float,
        portfolio_volatility: float,
        market_regime: str,
    ) -> RiskAssessment:
        """
        Compute risk score and generate warnings.
        All inputs are plain Python types for statelessness.
        """
        warnings: list[RiskWarning] = []
        risk_score = 0.0

        cash_ratio = cash / total_value if total_value > 0 else 1.0

        # ── Single stock concentration ──
        largest_position_pct = 0.0
        for h in holdings_detail:
            pos_pct = (h["current_value"] / total_value * 100) if total_value > 0 else 0
            if pos_pct > largest_position_pct:
                largest_position_pct = pos_pct
            if pos_pct > SINGLE_STOCK_LIMIT * 100:
                warnings.append(RiskWarning(
                    code="SINGLE_STOCK_CONCENTRATION",
                    level="HIGH" if pos_pct > 35 else "MEDIUM",
                    message=f"{h['symbol']} represents {pos_pct:.1f}% of portfolio. Policy limit: {SINGLE_STOCK_LIMIT*100:.0f}%.",
                    value=pos_pct,
                    limit=SINGLE_STOCK_LIMIT * 100,
                    symbol=h["symbol"],
                ))
                risk_score += (pos_pct - SINGLE_STOCK_LIMIT * 100) * 0.8

        # ── Sector concentration ──
        for sector, pct in sector_exposure.items():
            if pct > SECTOR_LIMIT * 100:
                warnings.append(RiskWarning(
                    code="SECTOR_CONCENTRATION",
                    level="HIGH" if pct > 50 else "MEDIUM",
                    message=f"{sector} exposure at {pct:.1f}%. Firm policy limit: {SECTOR_LIMIT*100:.0f}%.",
                    value=pct,
                    limit=SECTOR_LIMIT * 100,
                    sector=sector,
                ))
                risk_score += (pct - SECTOR_LIMIT * 100) * 0.5

        # ── Cash ratio ──
        if cash_ratio < MIN_CASH_RATIO and total_value > 0:
            warnings.append(RiskWarning(
                code="LOW_CASH",
                level="MEDIUM",
                message=f"Cash at {cash_ratio*100:.1f}% of portfolio. Minimum buffer: {MIN_CASH_RATIO*100:.0f}%.",
                value=cash_ratio * 100,
                limit=MIN_CASH_RATIO * 100,
            ))
            risk_score += 10

        # ── Drawdown ──
        if max_drawdown > MAX_DRAWDOWN_LIMIT:
            warnings.append(RiskWarning(
                code="DRAWDOWN_BREACH",
                level="CRITICAL",
                message=f"Drawdown of {max_drawdown*100:.1f}% exceeds firm limit of {MAX_DRAWDOWN_LIMIT*100:.0f}%. Immediate action required.",
                value=max_drawdown * 100,
                limit=MAX_DRAWDOWN_LIMIT * 100,
            ))
            risk_score += 30
        elif max_drawdown > MAX_DRAWDOWN_LIMIT * 0.7:
            warnings.append(RiskWarning(
                code="DRAWDOWN_WARNING",
                level="HIGH",
                message=f"Drawdown approaching limit at {max_drawdown*100:.1f}%. Limit: {MAX_DRAWDOWN_LIMIT*100:.0f}%.",
                value=max_drawdown * 100,
                limit=MAX_DRAWDOWN_LIMIT * 100,
            ))
            risk_score += 15

        # ── Regime risk ──
        regime_risk = {"BULL": 0, "STABLE": 0, "VOLATILE": 10, "BEAR": 20, "CRISIS": 40}
        risk_score += regime_risk.get(market_regime, 0)

        # ── Portfolio volatility ──
        if portfolio_volatility > 0.30:
            risk_score += 15
            warnings.append(RiskWarning(
                code="HIGH_PORTFOLIO_VOLATILITY",
                level="HIGH",
                message=f"Annualized portfolio volatility at {portfolio_volatility*100:.1f}%. Consider diversification.",
                value=portfolio_volatility * 100,
                limit=30.0,
            ))
        elif portfolio_volatility > 0.20:
            risk_score += 8

        risk_score = min(100.0, risk_score)

        overall_level = (
            "CRITICAL" if risk_score >= CRITICAL_RISK_THRESHOLD
            else "HIGH" if risk_score >= HIGH_RISK_THRESHOLD
            else "MEDIUM" if risk_score >= 30
            else "LOW"
        )

        is_violation = any(w.level in ("HIGH", "CRITICAL") for w in warnings)

        return RiskAssessment(
            overall_level=overall_level,
            risk_score=round(risk_score, 1),
            warnings=warnings,
            drawdown_pct=round(max_drawdown * 100, 2),
            cash_ratio=round(cash_ratio * 100, 2),
            largest_position_pct=round(largest_position_pct, 2),
            sector_concentration=sector_exposure,
            is_violation=is_violation,
            portfolio_volatility=round(portfolio_volatility * 100, 2),
        )
