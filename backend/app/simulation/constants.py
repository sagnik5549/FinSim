"""
Game constants and simulation configuration.
All game rules that are shared across engines belong here.
"""

CURRENCY = "₹"
CRORE = 10_000_000
LAKH = 100_000

STARTING_CAPITAL = 100 * CRORE
QUARTERLY_TARGET = 112 * CRORE
MAX_DRAWDOWN_LIMIT = 0.10
TRANSACTION_FEE_RATE = 0.0002

MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 17
WORKING_HOURS = list(range(MARKET_OPEN_HOUR, MARKET_CLOSE_HOUR))
HOURS_PER_DAY = len(WORKING_HOURS)

DAYS_PER_QUARTER = 90
CAREER_DAYS = 90

PAID_LEAVE_PER_YEAR = 60
CAREER_DAYS_PER_YEAR = 360

MARKET_STATUSES = {
    "PRE_MARKET",
    "OPEN",
    "CLOSED",
    "WEEKEND",
}

GAME_STATUSES = {
    "ACTIVE",
    "CAREER_ADVANCE",
    "REVIEW",
    "TERMINATED",
}

CAREER_STATUSES = {
    "ACTIVE",
    "WARNING",
    "TERMINATED",
}


STOCK_UNIVERSE = [
    {
        "symbol": "APXT",
        "name": "Apex Technologies",
        "sector": "Technology",
        "base_price": 3240.0,
        "volatility": 0.025,
        "beta": 1.4,
        "growth": 0.18,
        "profitability": 0.22,
        "debt": 0.15,
        "valuation": 0.72,
        "market_sensitivity": 1.4,
        "event_sensitivity": 0.7,
    },
    {
        "symbol": "VTXS",
        "name": "Vertex Systems",
        "sector": "Technology",
        "base_price": 1890.0,
        "volatility": 0.022,
        "beta": 1.3,
        "growth": 0.15,
        "profitability": 0.19,
        "debt": 0.10,
        "valuation": 0.65,
        "market_sensitivity": 1.3,
        "event_sensitivity": 0.6,
    },
    {
        "symbol": "NXSW",
        "name": "Nexus Software",
        "sector": "Technology",
        "base_price": 2150.0,
        "volatility": 0.028,
        "beta": 1.5,
        "growth": 0.22,
        "profitability": 0.18,
        "debt": 0.08,
        "valuation": 0.78,
        "market_sensitivity": 1.5,
        "event_sensitivity": 0.8,
    },
    {
        "symbol": "ZNTH",
        "name": "Zenith Bank",
        "sector": "Banking",
        "base_price": 780.0,
        "volatility": 0.018,
        "beta": 1.1,
        "growth": 0.12,
        "profitability": 0.15,
        "debt": 0.65,
        "valuation": 0.45,
        "market_sensitivity": 1.1,
        "event_sensitivity": 0.6,
    },
    {
        "symbol": "MRDN",
        "name": "Meridian Capital",
        "sector": "Banking",
        "base_price": 960.0,
        "volatility": 0.019,
        "beta": 0.95,
        "growth": 0.09,
        "profitability": 0.13,
        "debt": 0.48,
        "valuation": 0.38,
        "market_sensitivity": 1.0,
        "event_sensitivity": 0.55,
    },
    {
        "symbol": "ORFN",
        "name": "Orion Finance",
        "sector": "Finance",
        "base_price": 1240.0,
        "volatility": 0.020,
        "beta": 1.0,
        "growth": 0.10,
        "profitability": 0.14,
        "debt": 0.55,
        "valuation": 0.40,
        "market_sensitivity": 1.05,
        "event_sensitivity": 0.5,
    },
    {
        "symbol": "TITNE",
        "name": "Titan Energy",
        "sector": "Energy",
        "base_price": 340.0,
        "volatility": 0.030,
        "beta": 0.8,
        "growth": 0.08,
        "profitability": 0.11,
        "debt": 0.45,
        "valuation": 0.35,
        "market_sensitivity": 0.8,
        "event_sensitivity": 0.8,
    },
    {
        "symbol": "SLRS",
        "name": "Solaris Energy",
        "sector": "Energy",
        "base_price": 210.0,
        "volatility": 0.032,
        "beta": 0.75,
        "growth": 0.12,
        "profitability": 0.09,
        "debt": 0.40,
        "valuation": 0.30,
        "market_sensitivity": 0.75,
        "event_sensitivity": 0.85,
    },
    {
        "symbol": "BWPH",
        "name": "BlueWave Pharma",
        "sector": "Healthcare",
        "base_price": 1680.0,
        "volatility": 0.022,
        "beta": 0.7,
        "growth": 0.14,
        "profitability": 0.20,
        "debt": 0.20,
        "valuation": 0.60,
        "market_sensitivity": 0.7,
        "event_sensitivity": 0.9,
    },
    {
        "symbol": "HLXH",
        "name": "Helix Healthcare",
        "sector": "Healthcare",
        "base_price": 890.0,
        "volatility": 0.018,
        "beta": 0.65,
        "growth": 0.11,
        "profitability": 0.17,
        "debt": 0.18,
        "valuation": 0.55,
        "market_sensitivity": 0.65,
        "event_sensitivity": 0.85,
    },
    {
        "symbol": "NVMT",
        "name": "Nova Motors",
        "sector": "Automobile",
        "base_price": 2340.0,
        "volatility": 0.024,
        "beta": 1.2,
        "growth": 0.10,
        "profitability": 0.12,
        "debt": 0.35,
        "valuation": 0.42,
        "market_sensitivity": 1.2,
        "event_sensitivity": 0.6,
    },
    {
        "symbol": "CRSA",
        "name": "Crescent Auto",
        "sector": "Automobile",
        "base_price": 1450.0,
        "volatility": 0.022,
        "beta": 1.15,
        "growth": 0.08,
        "profitability": 0.10,
        "debt": 0.38,
        "valuation": 0.38,
        "market_sensitivity": 1.15,
        "event_sensitivity": 0.55,
    },
    {
        "symbol": "EVGR",
        "name": "Evergreen FMCG",
        "sector": "FMCG",
        "base_price": 4200.0,
        "volatility": 0.014,
        "beta": 0.6,
        "growth": 0.08,
        "profitability": 0.18,
        "debt": 0.15,
        "valuation": 0.55,
        "market_sensitivity": 0.6,
        "event_sensitivity": 0.4,
    },
    {
        "symbol": "PNCR",
        "name": "Pioneer Consumer",
        "sector": "FMCG",
        "base_price": 1890.0,
        "volatility": 0.013,
        "beta": 0.55,
        "growth": 0.07,
        "profitability": 0.16,
        "debt": 0.12,
        "valuation": 0.50,
        "market_sensitivity": 0.55,
        "event_sensitivity": 0.35,
    },
    {
        "symbol": "QNRT",
        "name": "Quantum Retail",
        "sector": "FMCG",
        "base_price": 890.0,
        "volatility": 0.021,
        "beta": 0.8,
        "growth": 0.13,
        "profitability": 0.10,
        "debt": 0.22,
        "valuation": 0.45,
        "market_sensitivity": 0.8,
        "event_sensitivity": 0.5,
    },
    {
        "symbol": "SLTM",
        "name": "Stellar Telecom",
        "sector": "Telecom",
        "base_price": 520.0,
        "volatility": 0.020,
        "beta": 0.85,
        "growth": 0.06,
        "profitability": 0.08,
        "debt": 0.60,
        "valuation": 0.32,
        "market_sensitivity": 0.85,
        "event_sensitivity": 0.5,
    },
    {
        "symbol": "IDUS",
        "name": "Indus Infrastructure",
        "sector": "Infrastructure",
        "base_price": 380.0,
        "volatility": 0.016,
        "beta": 0.9,
        "growth": 0.09,
        "profitability": 0.10,
        "debt": 0.50,
        "valuation": 0.36,
        "market_sensitivity": 0.9,
        "event_sensitivity": 0.45,
    },
    {
        "symbol": "ATLS",
        "name": "Atlas Industries",
        "sector": "Infrastructure",
        "base_price": 560.0,
        "volatility": 0.018,
        "beta": 0.85,
        "growth": 0.08,
        "profitability": 0.09,
        "debt": 0.45,
        "valuation": 0.34,
        "market_sensitivity": 0.85,
        "event_sensitivity": 0.4,
    },
    {
        "symbol": "ARDF",
        "name": "Archer Defence",
        "sector": "Defence",
        "base_price": 2890.0,
        "volatility": 0.016,
        "beta": 0.7,
        "growth": 0.12,
        "profitability": 0.14,
        "debt": 0.20,
        "valuation": 0.50,
        "market_sensitivity": 0.7,
        "event_sensitivity": 0.6,
    },
    {
        "symbol": "PRLG",
        "name": "Prime Logistics",
        "sector": "Logistics",
        "base_price": 740.0,
        "volatility": 0.019,
        "beta": 0.95,
        "growth": 0.10,
        "profitability": 0.11,
        "debt": 0.30,
        "valuation": 0.42,
        "market_sensitivity": 0.95,
        "event_sensitivity": 0.5,
    },
]

SECTORS = sorted({stock["sector"] for stock in STOCK_UNIVERSE})


REGIME_PARAMS = {
    "BULL": {
        "daily_drift_range": (0.003, 0.006),
        "vol_multiplier": 0.8,
        "transition_probs": {
            "BULL": 0.75,
            "STABLE": 0.20,
            "VOLATILE": 0.05,
            "BEAR": 0.0,
            "CRISIS": 0.0,
        },
        "min_days": 5,
        "max_days": 20,
    },
    "STABLE": {
        "daily_drift_range": (-0.001, 0.002),
        "vol_multiplier": 1.0,
        "transition_probs": {
            "BULL": 0.20,
            "STABLE": 0.60,
            "VOLATILE": 0.15,
            "BEAR": 0.05,
            "CRISIS": 0.0,
        },
        "min_days": 8,
        "max_days": 25,
    },
    "VOLATILE": {
        "daily_drift_range": (-0.003, 0.003),
        "vol_multiplier": 1.8,
        "transition_probs": {
            "BULL": 0.15,
            "STABLE": 0.35,
            "VOLATILE": 0.30,
            "BEAR": 0.15,
            "CRISIS": 0.05,
        },
        "min_days": 3,
        "max_days": 12,
    },
    "BEAR": {
        "daily_drift_range": (-0.005, -0.001),
        "vol_multiplier": 1.4,
        "transition_probs": {
            "BULL": 0.05,
            "STABLE": 0.25,
            "VOLATILE": 0.25,
            "BEAR": 0.40,
            "CRISIS": 0.05,
        },
        "min_days": 5,
        "max_days": 18,
    },
    "CRISIS": {
        "daily_drift_range": (-0.015, -0.005),
        "vol_multiplier": 2.5,
        "transition_probs": {
            "BULL": 0.0,
            "STABLE": 0.10,
            "VOLATILE": 0.30,
            "BEAR": 0.45,
            "CRISIS": 0.15,
        },
        "min_days": 2,
        "max_days": 8,
    },
}


SECTOR_MARKET_CORRELATION = {
    "Technology": 0.75,
    "Banking": 0.70,
    "Finance": 0.65,
    "Energy": 0.50,
    "Healthcare": 0.40,
    "Automobile": 0.65,
    "FMCG": 0.35,
    "Telecom": 0.45,
    "Infrastructure": 0.55,
    "Defence": 0.35,
    "Logistics": 0.50,
}


CAREER_LEVELS = {
    1: {
        "title": "Head of Investments",
        "quarter": 1,
        "quarter_name": "Quarter 1: Foundation Mandate",
        "xp_required": 0,
        "xp_to_next": 1000,
        "starting_capital": 100 * CRORE,
        "target_capital": 112 * CRORE,
        "target_return_pct": 12.0,
        "max_drawdown_limit": 0.10,
        "capital_injection": 0.0,
        "max_career_days": 90,
        "perks": [
            "Core 20-Stock Universe",
            "Standard Execution Desk",
            "Basic Technical Feed",
        ],
        "description": (
            "Establish baseline performance at Apex Capital. "
            "Demonstrate prudent capital allocation and risk control."
        ),
    },
    2: {
        "title": "Managing Director (Equities)",
        "quarter": 2,
        "quarter_name": "Quarter 2: Institutional Expansion",
        "xp_required": 1000,
        "xp_to_next": 3000,
        "starting_capital": 250 * CRORE,
        "target_capital": 287.5 * CRORE,
        "target_return_pct": 15.0,
        "max_drawdown_limit": 0.085,
        "capital_injection": 150 * CRORE,
        "max_career_days": 180,
        "perks": [
            "ML Quant Predictive Intelligence",
            "Real-Time Candlestick Telemetry",
            "Priority Order Routing",
        ],
        "description": (
            "Apex Capital elevates your mandate with an additional "
            "₹150 Cr institutional tranche."
        ),
    },
    3: {
        "title": "Chief Investment Officer (CIO)",
        "quarter": 3,
        "quarter_name": "Quarter 3: Flagship Fund Leadership",
        "xp_required": 3000,
        "xp_to_next": 7000,
        "starting_capital": 500 * CRORE,
        "target_capital": 590 * CRORE,
        "target_return_pct": 18.0,
        "max_drawdown_limit": 0.075,
        "capital_injection": 250 * CRORE,
        "max_career_days": 270,
        "perks": [
            "Institutional Block Trading",
            "Adaptive Multi-Regime Hedging",
            "Executive Risk Authority",
        ],
        "description": (
            "Assume executive CIO oversight of the flagship "
            "institutional balance sheet."
        ),
    },
    4: {
        "title": "Senior Managing Partner",
        "quarter": 4,
        "quarter_name": "Quarter 4: Apex Partnership & Spinoff",
        "xp_required": 7000,
        "xp_to_next": 15000,
        "starting_capital": 1000 * CRORE,
        "target_capital": 1200 * CRORE,
        "target_return_pct": 20.0,
        "max_drawdown_limit": 0.060,
        "capital_injection": 500 * CRORE,
        "max_career_days": 360,
        "perks": [
            "Apex Partnership Equity",
            "Autonomous Spinoff Fund",
            "Sovereign Co-Investment",
        ],
        "description": (
            "Offered equity partnership and the opportunity to lead "
            "an autonomous spinoff fund."
        ),
    },
    5: {
        "title": "Apex Sovereign Legend",
        "quarter": 5,
        "quarter_name": "Quarter 5+: Sovereign Wealth Advisory",
        "xp_required": 15000,
        "xp_to_next": 99999,
        "starting_capital": 2500 * CRORE,
        "target_capital": 3000 * CRORE,
        "target_return_pct": 20.0,
        "max_drawdown_limit": 0.050,
        "capital_injection": 1500 * CRORE,
        "max_career_days": 720,
        "perks": [
            "Sovereign Mandate",
            "Perpetual Simulation Mode",
            "Hall of Fame Legacy",
        ],
        "description": (
            "Pinnacle of financial mastery. Managing multi-billion "
            "rupee sovereign wealth."
        ),
    },
}


INDEX_DEFAULTS = {
    "nifty": 24500.0,
    "sensex": 80500.0,
    "bank_nifty": 51000.0,
    "india_vix": 14.5,
    "usdinr": 83.50,
    "gold": 72000.0,
    "nasdaq": 17500.0,
    "sp500": 5450.0,
}


def get_level_info(level: int) -> dict:
    return CAREER_LEVELS.get(level, CAREER_LEVELS[1])


def get_quarter_from_career_day(career_day: int) -> int:
    if career_day < 1:
        return 1

    return min(
        max(CAREER_LEVELS),
        ((career_day - 1) // DAYS_PER_QUARTER) + 1,
    )


def get_career_year(career_day: int) -> int:
    if career_day < 1:
        return 1

    return ((career_day - 1) // CAREER_DAYS_PER_YEAR) + 1


def get_quarter_max_days(quarter: int) -> int:
    level = min(max(CAREER_LEVELS), max(1, quarter))
    return CAREER_LEVELS[level]["max_career_days"]