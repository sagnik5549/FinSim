"""
EventEngine — generates, schedules, and processes game events.
Events drive market impact, news generation, and narrative.
"""
import random
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.simulation.constants import STOCK_UNIVERSE, SECTORS


@dataclass
class EventResult:
    event_type: str
    severity: str                     # LOW, MEDIUM, HIGH, CRITICAL
    affected_symbol: Optional[str]
    affected_sector: Optional[str]
    trigger_day: int
    trigger_hour: int
    duration_hours: int
    price_impact: float               # fractional; applied each hour during event
    narrative: str
    follow_up_event_type: Optional[str]
    follow_up_day: Optional[int]


# ─── Event Template Definitions ──────────────────────────────────────────────
COMPANY_EVENTS = [
    {
        "type": "EARNINGS_BEAT",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (0.015, 0.045),
        "duration_hours": 8,
        "narrative_template": "{name} reports quarterly earnings significantly above analyst estimates. Revenue growth of {pct}% surprises the street.",
        "follow_up": None,
    },
    {
        "type": "EARNINGS_MISS",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (-0.04, -0.015),
        "duration_hours": 8,
        "narrative_template": "{name} misses earnings estimates by a wide margin. Management warns of challenging conditions ahead.",
        "follow_up": ("CREDIT_CONCERNS", 3),
    },
    {
        "type": "CEO_RESIGNATION",
        "severity_range": ["HIGH", "CRITICAL"],
        "impact_range": (-0.06, -0.02),
        "duration_hours": 16,
        "narrative_template": "{name} CEO abruptly resigns amid board disagreements. Board launches search for replacement.",
        "follow_up": None,
    },
    {
        "type": "PRODUCT_LAUNCH",
        "severity_range": ["LOW", "MEDIUM"],
        "impact_range": (0.01, 0.035),
        "duration_hours": 8,
        "narrative_template": "{name} launches its next-generation product line. Analyst reactions are broadly positive.",
        "follow_up": None,
    },
    {
        "type": "PRODUCT_FAILURE",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (-0.03, -0.01),
        "duration_hours": 8,
        "narrative_template": "{name}'s flagship product faces quality issues. Company recalls units; reputation impact expected.",
        "follow_up": None,
    },
    {
        "type": "MAJOR_CONTRACT",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (0.02, 0.05),
        "duration_hours": 8,
        "narrative_template": "{name} announces a landmark contract worth ₹{cr} Cr. Largest deal in company history.",
        "follow_up": None,
    },
    {
        "type": "ACQUISITION_ANNOUNCED",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (0.015, 0.04),
        "duration_hours": 16,
        "narrative_template": "{name} announces acquisition of a strategic rival. Analysts debate synergy valuations.",
        "follow_up": ("ACQUISITION_CONCERNS", 5),
    },
    {
        "type": "ACQUISITION_CONCERNS",
        "severity_range": ["LOW", "MEDIUM"],
        "impact_range": (-0.025, -0.005),
        "duration_hours": 8,
        "narrative_template": "Analysts raise concerns about {name}'s acquisition price. Debt levels will increase significantly.",
        "follow_up": None,
    },
    {
        "type": "REGULATORY_INVESTIGATION",
        "severity_range": ["HIGH", "CRITICAL"],
        "impact_range": (-0.05, -0.02),
        "duration_hours": 24,
        "narrative_template": "{name} faces regulatory investigation into its market practices. Stock placed under review.",
        "follow_up": None,
    },
    {
        "type": "CREDIT_CONCERNS",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (-0.02, -0.005),
        "duration_hours": 16,
        "narrative_template": "Rating agencies place {name} on negative watch. Rising debt-to-equity ratio raises concern.",
        "follow_up": None,
    },
    {
        "type": "BREAKTHROUGH_TECH",
        "severity_range": ["HIGH", "CRITICAL"],
        "impact_range": (0.03, 0.08),
        "duration_hours": 8,
        "narrative_template": "{name} announces a breakthrough that could reshape the {sector} sector. Patent filed.",
        "follow_up": None,
    },
    {
        "type": "MANAGEMENT_SCANDAL",
        "severity_range": ["HIGH", "CRITICAL"],
        "impact_range": (-0.05, -0.02),
        "duration_hours": 16,
        "narrative_template": "Media reports allege financial irregularities at {name}. Board convenes emergency meeting.",
        "follow_up": ("REGULATORY_INVESTIGATION", 4),
    },
]

MACRO_EVENTS = [
    {
        "type": "RATE_HIKE",
        "severity_range": ["HIGH", "CRITICAL"],
        "sector_impact": {"Banking": 0.02, "Finance": -0.01, "Technology": -0.015, "FMCG": -0.005},
        "narrative": "RBI raises repo rate by 25 basis points, citing persistent inflation. Markets reprice rate-sensitive assets.",
        "follow_up": None,
    },
    {
        "type": "RATE_CUT",
        "severity_range": ["HIGH", "CRITICAL"],
        "sector_impact": {"Banking": -0.01, "Finance": 0.015, "Technology": 0.02, "FMCG": 0.01},
        "narrative": "RBI surprises markets with a rate cut, signaling growth concerns. Rate-sensitive sectors rally.",
        "follow_up": None,
    },
    {
        "type": "INFLATION_SURPRISE",
        "severity_range": ["MEDIUM", "HIGH"],
        "sector_impact": {"FMCG": -0.01, "Energy": 0.015, "Technology": -0.008},
        "narrative": "CPI inflation comes in higher than expected at {pct}%. Market pricing adjusts for RBI response.",
        "follow_up": None,
    },
    {
        "type": "GDP_SURPRISE_POSITIVE",
        "severity_range": ["MEDIUM", "HIGH"],
        "sector_impact": {"Technology": 0.01, "Banking": 0.012, "Automobile": 0.015, "Infrastructure": 0.02},
        "narrative": "Q{q} GDP growth beats consensus at {pct}%. Broad market rally as economic confidence improves.",
        "follow_up": None,
    },
    {
        "type": "CURRENCY_SHOCK",
        "severity_range": ["MEDIUM", "HIGH"],
        "sector_impact": {"Technology": 0.015, "Telecom": -0.008, "Energy": -0.012},
        "narrative": "USD/INR moves sharply. Export-oriented sectors benefit while importers face margin pressure.",
        "follow_up": None,
    },
    {
        "type": "COMMODITY_SHOCK",
        "severity_range": ["MEDIUM", "HIGH"],
        "sector_impact": {"Energy": 0.02, "Automobile": -0.01, "FMCG": -0.008, "Logistics": -0.012},
        "narrative": "Crude oil prices spike on supply disruption. Energy complex benefits; high-cost industries face pressure.",
        "follow_up": None,
    },
    {
        "type": "GLOBAL_RISK_OFF",
        "severity_range": ["HIGH", "CRITICAL"],
        "sector_impact": {s: -0.015 for s in ["Technology", "Banking", "Automobile"]},
        "narrative": "Global risk sentiment deteriorates sharply. FIIs reduce India exposure. Broad selloff across sectors.",
        "follow_up": None,
    },
]


class EventEngine:
    """Generates and processes market events."""

    @staticmethod
    def generate_daily_events(
        career_day: int,
        game_hour: int,
        stocks: list,
        game,
        rng: np.random.Generator,
    ) -> list[EventResult]:
        """
        Generate events for this tick based on probability and game state.
        Called once per hour during market hours.
        """
        results = []
        regime = game.market_regime

        # Adjust base event probability per regime
        base_company_prob = {"BULL": 0.04, "STABLE": 0.03, "VOLATILE": 0.07, "BEAR": 0.06, "CRISIS": 0.10}
        base_macro_prob = {"BULL": 0.01, "STABLE": 0.015, "VOLATILE": 0.03, "BEAR": 0.04, "CRISIS": 0.06}

        # ── Company events ──
        for stock in stocks:
            sym = stock.symbol if hasattr(stock, "symbol") else stock["symbol"]
            name = stock.name if hasattr(stock, "name") else stock["name"]
            sector = stock.sector if hasattr(stock, "sector") else stock["sector"]
            evt_sens = stock.event_sensitivity if hasattr(stock, "event_sensitivity") else stock.get("event_sensitivity", 0.5)

            prob = base_company_prob.get(regime, 0.03) * evt_sens
            if rng.random() < prob:
                template = rng.choice(COMPANY_EVENTS)
                severity = rng.choice(template["severity_range"])
                impact = float(rng.uniform(*template["impact_range"]))
                narrative = template["narrative_template"].format(
                    name=name,
                    sector=sector,
                    pct=round(rng.uniform(5, 30), 1),
                    cr=int(rng.uniform(100, 5000)),
                )
                follow_up_type = template.get("follow_up")
                results.append(EventResult(
                    event_type=template["type"],
                    severity=severity,
                    affected_symbol=sym,
                    affected_sector=sector,
                    trigger_day=career_day,
                    trigger_hour=game_hour,
                    duration_hours=template["duration_hours"],
                    price_impact=impact / template["duration_hours"],  # spread over duration
                    narrative=narrative,
                    follow_up_event_type=follow_up_type[0] if follow_up_type else None,
                    follow_up_day=career_day + follow_up_type[1] if follow_up_type else None,
                ))

        # ── Macro events (once per day max) ──
        if game_hour == 9:
            macro_prob = base_macro_prob.get(regime, 0.015)
            if rng.random() < macro_prob:
                macro = rng.choice(MACRO_EVENTS)
                results.append(EventResult(
                    event_type=macro["type"],
                    severity=rng.choice(macro["severity_range"]),
                    affected_symbol=None,
                    affected_sector=None,
                    trigger_day=career_day,
                    trigger_hour=game_hour,
                    duration_hours=8,
                    price_impact=0.0,  # macro events affect via sector factors
                    narrative=macro["narrative"].format(
                        pct=round(rng.uniform(4.5, 7.5), 1),
                        q=((career_day - 1) // 30) + 1,
                    ),
                    follow_up_event_type=None,
                    follow_up_day=None,
                ))

        return results

    @staticmethod
    def get_event_shocks(active_events: list) -> dict[str, float]:
        """Build per-symbol price shock map from active events."""
        shocks: dict[str, float] = {}
        for evt in active_events:
            sym = evt.affected_symbol if hasattr(evt, "affected_symbol") else evt.get("affected_symbol")
            impact = evt.price_impact if hasattr(evt, "price_impact") else evt.get("price_impact", 0.0)
            if sym and impact:
                shocks[sym] = shocks.get(sym, 0.0) + float(impact)
        return shocks

    @staticmethod
    def get_macro_sector_shocks(active_events: list) -> dict[str, float]:
        """Return sector-level shocks from macro events."""
        sector_shocks: dict[str, float] = {}
        macro_types = {e["type"]: e for e in MACRO_EVENTS}
        for evt in active_events:
            evt_type = evt.event_type if hasattr(evt, "event_type") else evt.get("event_type", "")
            if evt_type in macro_types:
                for sector, impact in macro_types[evt_type].get("sector_impact", {}).items():
                    sector_shocks[sector] = sector_shocks.get(sector, 0.0) + impact / 8
        return sector_shocks
