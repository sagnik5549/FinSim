"""
NewsEngine — generates contextual financial news from actual game events.
All news is driven by real game state, not random lorem ipsum.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class NewsResult:
    category: str       # COMPANY, MACRO, MARKET, CEO
    priority: str       # BREAKING, HIGH, NORMAL, LOW
    headline: str
    body: Optional[str]
    affected_symbol: Optional[str]
    affected_sector: Optional[str]
    market_impact: float  # -1 to 1


class NewsEngine:
    """Generates news strings from game events and market state."""

    @staticmethod
    def news_from_event(event) -> NewsResult:
        """Convert an EventResult or GameEvent to a news item."""
        evt_type = event.event_type if hasattr(event, "event_type") else event.get("event_type", "")
        severity = event.severity if hasattr(event, "severity") else event.get("severity", "MEDIUM")
        symbol = event.affected_symbol if hasattr(event, "affected_symbol") else event.get("affected_symbol")
        sector = event.affected_sector if hasattr(event, "affected_sector") else event.get("affected_sector")
        narrative = event.narrative if hasattr(event, "narrative") else event.get("narrative", "Market event occurred.")
        impact = event.price_impact if hasattr(event, "price_impact") else event.get("price_impact", 0.0)

        # Determine category
        macro_types = {
            "RATE_HIKE", "RATE_CUT", "INFLATION_SURPRISE",
            "GDP_SURPRISE_POSITIVE", "CURRENCY_SHOCK", "COMMODITY_SHOCK", "GLOBAL_RISK_OFF"
        }
        is_macro = evt_type in macro_types

        category = "MACRO" if is_macro else "COMPANY"
        priority = "BREAKING" if severity == "CRITICAL" else "HIGH" if severity == "HIGH" else "NORMAL"

        return NewsResult(
            category=category,
            priority=priority,
            headline=narrative,
            body=NewsEngine._generate_body(evt_type, symbol, sector, impact),
            affected_symbol=symbol,
            affected_sector=sector,
            market_impact=max(-1.0, min(1.0, impact * 10)),
        )

    @staticmethod
    def _generate_body(evt_type: str, symbol: Optional[str], sector: Optional[str], impact: float) -> Optional[str]:
        bodies = {
            "EARNINGS_BEAT": f"Shares of {symbol} surged in early trade following better-than-expected quarterly results. Fund managers and institutional investors are revising their price targets upward.",
            "EARNINGS_MISS": f"Shares of {symbol} fell sharply after the company disappointed investors with below-consensus earnings. Management guidance was cautious.",
            "CEO_RESIGNATION": f"The sudden departure of {symbol}'s CEO has raised governance concerns. The board has formed a search committee to identify a successor.",
            "PRODUCT_LAUNCH": f"{symbol}'s new product line has been well-received by early reviewers. Market share expansion is anticipated in the next quarter.",
            "PRODUCT_FAILURE": f"Reports of quality defects in {symbol}'s key product are circulating. The company faces potential recall costs and reputational damage.",
            "MAJOR_CONTRACT": f"{symbol} has secured a long-term contract that adds significant backlog visibility. Analysts have upgraded the stock citing improved revenue visibility.",
            "ACQUISITION_ANNOUNCED": f"{symbol}'s acquisition strategy signals ambition but raises questions about integration risk and debt. Arb desks are pricing in deal risk.",
            "REGULATORY_INVESTIGATION": f"Regulators have opened a formal probe into {symbol}'s practices. The company has said it will cooperate fully.",
            "RATE_HIKE": "The monetary policy committee voted to raise the benchmark rate. The move is expected to dampen loan growth and compress NIMs for banks. Rate-sensitive sectors are under pressure.",
            "RATE_CUT": "RBI's surprise rate cut aims to stimulate economic activity. Banking and NBFC stocks are under pressure as NIMs compress, but capital-intensive sectors may benefit.",
            "GLOBAL_RISK_OFF": "Foreign institutional investors are pulling back from emerging markets amid global uncertainty. India's FII flows have turned negative for the week.",
            "COMMODITY_SHOCK": "A supply disruption has sent commodity prices sharply higher. Input-cost-sensitive companies face margin pressure in the near term.",
        }
        return bodies.get(evt_type)

    @staticmethod
    def generate_market_color(
        nifty_change: float,
        regime: str,
        best_sector: Optional[str],
        worst_sector: Optional[str],
        career_day: int,
        rng: np.random.Generator,
    ) -> NewsResult:
        """Generate a daily market summary news item."""
        direction = "rally" if nifty_change > 0 else "decline"
        pct = abs(round(nifty_change * 100, 2))

        regime_colors = {
            "BULL": "Bulls remain in control",
            "STABLE": "Markets trade in a narrow range",
            "VOLATILE": "Volatility dominates trade",
            "BEAR": "Selling pressure intensifies",
            "CRISIS": "Panic grips Dalal Street",
        }
        color = regime_colors.get(regime, "Markets show mixed signals")

        headline = f"NIFTY 50 posts {pct}% {direction} — {color}"
        body_parts = []
        if best_sector:
            body_parts.append(f"{best_sector} leads gains.")
        if worst_sector:
            body_parts.append(f"{worst_sector} underperforms.")
        body_parts.append(f"Market sentiment: {regime}.")

        return NewsResult(
            category="MARKET",
            priority="NORMAL",
            headline=headline,
            body=" ".join(body_parts),
            affected_symbol=None,
            affected_sector=None,
            market_impact=nifty_change,
        )

    @staticmethod
    def generate_ceo_message(
        portfolio_return: float,
        career_day: int,
        target_progress: float,
        rng: np.random.Generator,
    ) -> Optional[NewsResult]:
        """Occasional CEO messages based on performance."""
        if career_day % 15 != 0 and rng.random() > 0.05:
            return None

        if target_progress >= 0.9:
            msg = "Excellent progress. We're close to the target. Stay disciplined."
        elif target_progress >= 0.7:
            msg = "Good momentum. Keep risk in check as we push toward the quarter-end target."
        elif target_progress >= 0.5:
            msg = "We're at the halfway mark but below pace. I need you to find opportunities."
        elif target_progress >= 0.3:
            msg = "I'm concerned about our pace. The board is watching. What's your plan?"
        else:
            msg = f"Day {career_day}: Target is at {int(target_progress*100)}%. This is not acceptable. Results needed."

        return NewsResult(
            category="CEO",
            priority="HIGH",
            headline=f'CEO: "{msg}"',
            body=None,
            affected_symbol=None,
            affected_sector=None,
            market_impact=0.0,
        )
