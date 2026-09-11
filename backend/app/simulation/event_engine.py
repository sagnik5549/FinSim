from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.simulation.constants import WORKING_HOURS


@dataclass
class EventResult:
    event_type: str
    severity: str
    affected_symbol: Optional[str]
    affected_sector: Optional[str]
    trigger_day: int
    trigger_hour: int
    duration_hours: int
    price_impact: float
    narrative: str
    follow_up_event_type: Optional[str]
    follow_up_day: Optional[int]


COMPANY_EVENTS = [
    {
        "type": "EARNINGS_BEAT",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (0.015, 0.045),
        "duration_hours": 8,
        "narrative_template": (
            "{name} reports quarterly earnings significantly "
            "above analyst estimates. Revenue growth of {pct}% "
            "surprises the street."
        ),
        "follow_up": None,
    },
    {
        "type": "EARNINGS_MISS",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (-0.040, -0.015),
        "duration_hours": 8,
        "narrative_template": (
            "{name} misses earnings estimates by a wide margin. "
            "Management warns of challenging conditions ahead."
        ),
        "follow_up": ("CREDIT_CONCERNS", 3),
    },
    {
        "type": "CEO_RESIGNATION",
        "severity_range": ["HIGH", "CRITICAL"],
        "impact_range": (-0.060, -0.020),
        "duration_hours": 16,
        "narrative_template": (
            "{name} CEO abruptly resigns amid board disagreements. "
            "Board launches search for replacement."
        ),
        "follow_up": None,
    },
    {
        "type": "PRODUCT_LAUNCH",
        "severity_range": ["LOW", "MEDIUM"],
        "impact_range": (0.010, 0.035),
        "duration_hours": 8,
        "narrative_template": (
            "{name} launches its next-generation product line. "
            "Analyst reactions are broadly positive."
        ),
        "follow_up": None,
    },
    {
        "type": "PRODUCT_FAILURE",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (-0.030, -0.010),
        "duration_hours": 8,
        "narrative_template": (
            "{name}'s flagship product faces quality issues. "
            "Company recalls units; reputation impact expected."
        ),
        "follow_up": None,
    },
    {
        "type": "MAJOR_CONTRACT",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (0.020, 0.050),
        "duration_hours": 8,
        "narrative_template": (
            "{name} announces a landmark contract worth "
            "₹{cr} Cr. Largest deal in company history."
        ),
        "follow_up": None,
    },
    {
        "type": "ACQUISITION_ANNOUNCED",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (0.015, 0.040),
        "duration_hours": 16,
        "narrative_template": (
            "{name} announces acquisition of a strategic rival. "
            "Analysts debate synergy valuations."
        ),
        "follow_up": ("ACQUISITION_CONCERNS", 5),
    },
    {
        "type": "ACQUISITION_CONCERNS",
        "severity_range": ["LOW", "MEDIUM"],
        "impact_range": (-0.025, -0.005),
        "duration_hours": 8,
        "narrative_template": (
            "Analysts raise concerns about {name}'s acquisition "
            "price. Debt levels will increase significantly."
        ),
        "follow_up": None,
    },
    {
        "type": "REGULATORY_INVESTIGATION",
        "severity_range": ["HIGH", "CRITICAL"],
        "impact_range": (-0.050, -0.020),
        "duration_hours": 24,
        "narrative_template": (
            "{name} faces regulatory investigation into its "
            "market practices. Stock placed under review."
        ),
        "follow_up": None,
    },
    {
        "type": "CREDIT_CONCERNS",
        "severity_range": ["MEDIUM", "HIGH"],
        "impact_range": (-0.020, -0.005),
        "duration_hours": 16,
        "narrative_template": (
            "Rating agencies place {name} on negative watch. "
            "Rising debt-to-equity ratio raises concern."
        ),
        "follow_up": None,
    },
    {
        "type": "BREAKTHROUGH_TECH",
        "severity_range": ["HIGH", "CRITICAL"],
        "impact_range": (0.030, 0.080),
        "duration_hours": 8,
        "narrative_template": (
            "{name} announces a breakthrough that could reshape "
            "the {sector} sector. Patent filed."
        ),
        "follow_up": None,
    },
    {
        "type": "MANAGEMENT_SCANDAL",
        "severity_range": ["HIGH", "CRITICAL"],
        "impact_range": (-0.050, -0.020),
        "duration_hours": 16,
        "narrative_template": (
            "Media reports allege financial irregularities at "
            "{name}. Board convenes emergency meeting."
        ),
        "follow_up": ("REGULATORY_INVESTIGATION", 4),
    },
]


MACRO_EVENTS = [
    {
        "type": "RATE_HIKE",
        "severity_range": ["HIGH", "CRITICAL"],
        "sector_impact": {
            "Banking": 0.020,
            "Finance": -0.010,
            "Technology": -0.015,
            "FMCG": -0.005,
        },
        "narrative": (
            "RBI raises repo rate by 25 basis points, citing "
            "persistent inflation. Markets reprice rate-sensitive assets."
        ),
    },
    {
        "type": "RATE_CUT",
        "severity_range": ["HIGH", "CRITICAL"],
        "sector_impact": {
            "Banking": -0.010,
            "Finance": 0.015,
            "Technology": 0.020,
            "FMCG": 0.010,
        },
        "narrative": (
            "RBI surprises markets with a rate cut, signaling "
            "growth concerns. Rate-sensitive sectors rally."
        ),
    },
    {
        "type": "INFLATION_SURPRISE",
        "severity_range": ["MEDIUM", "HIGH"],
        "sector_impact": {
            "FMCG": -0.010,
            "Energy": 0.015,
            "Technology": -0.008,
        },
        "narrative": (
            "CPI inflation comes in higher than expected at "
            "{pct}%. Market pricing adjusts for RBI response."
        ),
    },
    {
        "type": "GDP_SURPRISE_POSITIVE",
        "severity_range": ["MEDIUM", "HIGH"],
        "sector_impact": {
            "Technology": 0.010,
            "Banking": 0.012,
            "Automobile": 0.015,
            "Infrastructure": 0.020,
        },
        "narrative": (
            "Q{q} GDP growth beats consensus at {pct}%. "
            "Broad market rally as economic confidence improves."
        ),
    },
    {
        "type": "CURRENCY_SHOCK",
        "severity_range": ["MEDIUM", "HIGH"],
        "sector_impact": {
            "Technology": 0.015,
            "Telecom": -0.008,
            "Energy": -0.012,
        },
        "narrative": (
            "USD/INR moves sharply. Export-oriented sectors benefit "
            "while importers face margin pressure."
        ),
    },
    {
        "type": "COMMODITY_SHOCK",
        "severity_range": ["MEDIUM", "HIGH"],
        "sector_impact": {
            "Energy": 0.020,
            "Automobile": -0.010,
            "FMCG": -0.008,
            "Logistics": -0.012,
        },
        "narrative": (
            "Crude oil prices spike on supply disruption. Energy "
            "complex benefits; high-cost industries face pressure."
        ),
    },
    {
        "type": "GLOBAL_RISK_OFF",
        "severity_range": ["HIGH", "CRITICAL"],
        "sector_impact": {
            "Technology": -0.015,
            "Banking": -0.015,
            "Automobile": -0.015,
        },
        "narrative": (
            "Global risk sentiment deteriorates sharply. FIIs "
            "reduce India exposure. Broad selloff across sectors."
        ),
    },
]


BASE_COMPANY_PROBABILITY = {
    "BULL": 0.040,
    "STABLE": 0.030,
    "VOLATILE": 0.070,
    "BEAR": 0.060,
    "CRISIS": 0.100,
}


BASE_MACRO_PROBABILITY = {
    "BULL": 0.010,
    "STABLE": 0.015,
    "VOLATILE": 0.030,
    "BEAR": 0.040,
    "CRISIS": 0.060,
}


SEVERITY_MULTIPLIER = {
    "LOW": 0.75,
    "MEDIUM": 1.00,
    "HIGH": 1.15,
    "CRITICAL": 1.30,
}


class EventEngine:

    @staticmethod
    def _value(
        obj,
        key: str,
        default=None,
    ):
        if hasattr(obj, key):
            return getattr(obj, key)

        if isinstance(obj, dict):
            return obj.get(key, default)

        return default

    @staticmethod
    def _is_market_hour(
        game_hour: int,
    ) -> bool:
        return game_hour in WORKING_HOURS

    @staticmethod
    def _create_event(
        template: dict,
        career_day: int,
        game_hour: int,
        symbol: Optional[str],
        name: Optional[str],
        sector: Optional[str],
        rng: np.random.Generator,
    ) -> EventResult:

        severity = str(
            rng.choice(
                template["severity_range"]
            )
        )

        raw_impact = float(
            rng.uniform(
                *template["impact_range"]
            )
        )

        duration = max(
            1,
            int(template["duration_hours"]),
        )

        per_tick_impact = (
            raw_impact / duration
        )

        narrative = template[
            "narrative_template"
        ].format(
            name=name or "The company",
            sector=sector or "market",
            pct=round(
                rng.uniform(5, 30),
                1,
            ),
            cr=int(
                rng.uniform(100, 5000)
            ),
        )

        follow_up = template.get(
            "follow_up"
        )

        return EventResult(
            event_type=template["type"],
            severity=severity,
            affected_symbol=symbol,
            affected_sector=sector,
            trigger_day=career_day,
            trigger_hour=game_hour,
            duration_hours=duration,
            price_impact=per_tick_impact,
            narrative=narrative,
            follow_up_event_type=(
                follow_up[0]
                if follow_up
                else None
            ),
            follow_up_day=(
                career_day + follow_up[1]
                if follow_up
                else None
            ),
        )

    @staticmethod
    def generate_daily_events(
        career_day: int,
        game_hour: int,
        stocks: list,
        game,
        rng: np.random.Generator,
        probability_multiplier: float = 1.0,
    ) -> list[EventResult]:

        if not EventEngine._is_market_hour(
            game_hour
        ):
            return []

        probability_multiplier = float(
            np.clip(
                probability_multiplier,
                0.0,
                2.0,
            )
        )

        regime = str(
            getattr(
                game,
                "market_regime",
                "STABLE",
            )
        ).upper()

        company_probability = (
            BASE_COMPANY_PROBABILITY.get(
                regime,
                BASE_COMPANY_PROBABILITY["STABLE"],
            )
            * probability_multiplier
        )

        macro_probability = (
            BASE_MACRO_PROBABILITY.get(
                regime,
                BASE_MACRO_PROBABILITY["STABLE"],
            )
            * probability_multiplier
        )

        events: list[EventResult] = []

        for stock in stocks:
            symbol = EventEngine._value(
                stock,
                "symbol",
            )

            name = EventEngine._value(
                stock,
                "name",
                symbol,
            )

            sector = EventEngine._value(
                stock,
                "sector",
            )

            sensitivity = float(
                EventEngine._value(
                    stock,
                    "event_sensitivity",
                    0.5,
                )
            )

            sensitivity = float(
                np.clip(
                    sensitivity,
                    0.0,
                    1.5,
                )
            )

            probability = (
                company_probability
                * sensitivity
            )

            if rng.random() >= probability:
                continue

            template = COMPANY_EVENTS[
                int(
                    rng.integers(
                        0,
                        len(COMPANY_EVENTS),
                    )
                )
            ]

            events.append(
                EventEngine._create_event(
                    template=template,
                    career_day=career_day,
                    game_hour=game_hour,
                    symbol=symbol,
                    name=name,
                    sector=sector,
                    rng=rng,
                )
            )

        if game_hour == min(WORKING_HOURS):
            if rng.random() < macro_probability:
                template = MACRO_EVENTS[
                    int(
                        rng.integers(
                            0,
                            len(MACRO_EVENTS),
                        )
                    )
                ]

                narrative = template[
                    "narrative"
                ].format(
                    pct=round(
                        rng.uniform(4.5, 7.5),
                        1,
                    ),
                    q=max(
                        1,
                        ((career_day - 1) // 90) + 1,
                    ),
                )

                events.append(
                    EventResult(
                        event_type=template["type"],
                        severity=str(
                            rng.choice(
                                template[
                                    "severity_range"
                                ]
                            )
                        ),
                        affected_symbol=None,
                        affected_sector=None,
                        trigger_day=career_day,
                        trigger_hour=game_hour,
                        duration_hours=8,
                        price_impact=0.0,
                        narrative=narrative,
                        follow_up_event_type=None,
                        follow_up_day=None,
                    )
                )

        return events

    @staticmethod
    def generate_follow_up_event(
        parent_event,
        career_day: int,
        game_hour: int,
        stocks: list,
        rng: np.random.Generator,
    ) -> Optional[EventResult]:

        event_type = EventEngine._value(
            parent_event,
            "follow_up_event_type",
        )

        if not event_type:
            return None

        template = next(
            (
                item
                for item in COMPANY_EVENTS
                if item["type"] == event_type
            ),
            None,
        )

        if template is None:
            return None

        symbol = EventEngine._value(
            parent_event,
            "affected_symbol",
        )

        sector = EventEngine._value(
            parent_event,
            "affected_sector",
        )

        name = symbol

        for stock in stocks:
            stock_symbol = EventEngine._value(
                stock,
                "symbol",
            )

            if stock_symbol == symbol:
                name = EventEngine._value(
                    stock,
                    "name",
                    symbol,
                )
                break

        return EventEngine._create_event(
            template=template,
            career_day=career_day,
            game_hour=game_hour,
            symbol=symbol,
            name=name,
            sector=sector,
            rng=rng,
        )

    @staticmethod
    def get_active_events(
        events: list,
        career_day: Optional[int] = None,
        game_hour: Optional[int] = None,
    ) -> list:

        if career_day is None or game_hour is None:
            return [
                event
                for event in events
                if bool(
                    EventEngine._value(
                        event,
                        "is_active",
                        True,
                    )
                )
            ]

        current_tick = (
            (career_day - 1)
            * len(WORKING_HOURS)
            + max(
                0,
                game_hour
                - min(WORKING_HOURS),
            )
        )

        active = []

        for event in events:
            if not bool(
                EventEngine._value(
                    event,
                    "is_active",
                    True,
                )
            ):
                continue

            trigger_day = int(
                EventEngine._value(
                    event,
                    "trigger_day",
                    career_day,
                )
            )

            trigger_hour = int(
                EventEngine._value(
                    event,
                    "trigger_hour",
                    min(WORKING_HOURS),
                )
            )

            trigger_tick = (
                (trigger_day - 1)
                * len(WORKING_HOURS)
                + max(
                    0,
                    trigger_hour
                    - min(WORKING_HOURS),
                )
            )

            duration = max(
                1,
                int(
                    EventEngine._value(
                        event,
                        "duration_hours",
                        1,
                    )
                ),
            )

            if (
                trigger_tick
                <= current_tick
                < trigger_tick + duration
            ):
                active.append(event)

        return active

    @staticmethod
    def get_event_shocks(
        active_events: list,
        career_day: Optional[int] = None,
        game_hour: Optional[int] = None,
    ) -> dict[str, float]:

        events = EventEngine.get_active_events(
            active_events,
            career_day,
            game_hour,
        )

        shocks: dict[str, float] = {}

        for event in events:
            symbol = EventEngine._value(
                event,
                "affected_symbol",
            )

            impact = float(
                EventEngine._value(
                    event,
                    "price_impact",
                    0.0,
                )
            )

            if not symbol or impact == 0.0:
                continue

            symbol = str(symbol).upper()

            shocks[symbol] = (
                shocks.get(symbol, 0.0)
                + impact
            )

        return shocks

    @staticmethod
    def get_macro_sector_shocks(
        active_events: list,
        career_day: Optional[int] = None,
        game_hour: Optional[int] = None,
    ) -> dict[str, float]:

        events = EventEngine.get_active_events(
            active_events,
            career_day,
            game_hour,
        )

        macro_map = {
            event["type"]: event
            for event in MACRO_EVENTS
        }

        sector_shocks: dict[str, float] = {}

        for event in events:
            event_type = EventEngine._value(
                event,
                "event_type",
                "",
            )

            template = macro_map.get(
                event_type
            )

            if template is None:
                continue

            duration = max(
                1,
                int(
                    EventEngine._value(
                        event,
                        "duration_hours",
                        8,
                    )
                ),
            )

            for sector, impact in template[
                "sector_impact"
            ].items():

                sector_shocks[sector] = (
                    sector_shocks.get(
                        sector,
                        0.0,
                    )
                    + float(impact) / duration
                )

        return sector_shocks