"""
Stock universe, sector definitions, career levels, and game constants
for Investment Banker Mode.
"""

# ─── Currency ────────────────────────────────────────────────────────────────
CURRENCY = "₹"
CRORE = 1_00_00_000      # 10_000_000
LAKH = 1_00_000           # 100_000

STARTING_CAPITAL = 100 * CRORE          # ₹100 Cr
QUARTERLY_TARGET = 112 * CRORE          # ₹112 Cr
MAX_DRAWDOWN_LIMIT = 0.10               # 10%
TRANSACTION_FEE_RATE = 0.0002           # 0.02% STT + brokerage approximation
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 17                  # 5 PM; 9 working hours (9,10,11,12,13,14,15,16)
WORKING_HOURS = list(range(MARKET_OPEN_HOUR, MARKET_CLOSE_HOUR))  # [9..16]
HOURS_PER_DAY = len(WORKING_HOURS)     # 8
CAREER_DAYS = 90

# ─── 20 Fictional Stock Universe ─────────────────────────────────────────────
# All prices in INR (realistic Indian exchange price ranges)
STOCK_UNIVERSE = [
    # Technology
    {
        "symbol": "APXT", "name": "Apex Technologies", "sector": "Technology",
        "base_price": 3240.0, "volatility": 0.025, "beta": 1.4,
        "growth": 0.18, "profitability": 0.22, "debt": 0.15, "valuation": 0.72,
        "market_sensitivity": 1.4, "event_sensitivity": 0.7,
    },
    {
        "symbol": "VTXS", "name": "Vertex Systems", "sector": "Technology",
        "base_price": 1890.0, "volatility": 0.022, "beta": 1.3,
        "growth": 0.15, "profitability": 0.19, "debt": 0.10, "valuation": 0.65,
        "market_sensitivity": 1.3, "event_sensitivity": 0.6,
    },
    {
        "symbol": "NXSW", "name": "Nexus Software", "sector": "Technology",
        "base_price": 2150.0, "volatility": 0.028, "beta": 1.5,
        "growth": 0.22, "profitability": 0.18, "debt": 0.08, "valuation": 0.78,
        "market_sensitivity": 1.5, "event_sensitivity": 0.8,
    },
    # Banking
    {
        "symbol": "ZNTH", "name": "Zenith Bank", "sector": "Banking",
        "base_price": 780.0, "volatility": 0.018, "beta": 1.1,
        "growth": 0.12, "profitability": 0.15, "debt": 0.65, "valuation": 0.45,
        "market_sensitivity": 1.1, "event_sensitivity": 0.6,
    },
    {
        "symbol": "MRDN", "name": "Meridian Capital", "sector": "Banking",
        "base_price": 960.0, "volatility": 0.019, "beta": 0.95,
        "growth": 0.09, "profitability": 0.13, "debt": 0.48, "valuation": 0.38,
        "market_sensitivity": 1.0, "event_sensitivity": 0.55,
    },
    # Finance
    {
        "symbol": "ORFN", "name": "Orion Finance", "sector": "Finance",
        "base_price": 1240.0, "volatility": 0.020, "beta": 1.0,
        "growth": 0.10, "profitability": 0.14, "debt": 0.55, "valuation": 0.40,
        "market_sensitivity": 1.05, "event_sensitivity": 0.5,
    },
    # Energy
    {
        "symbol": "TITNE", "name": "Titan Energy", "sector": "Energy",
        "base_price": 340.0, "volatility": 0.030, "beta": 0.8,
        "growth": 0.08, "profitability": 0.11, "debt": 0.45, "valuation": 0.35,
        "market_sensitivity": 0.8, "event_sensitivity": 0.8,
    },
    {
        "symbol": "SLRS", "name": "Solaris Energy", "sector": "Energy",
        "base_price": 210.0, "volatility": 0.032, "beta": 0.75,
        "growth": 0.12, "profitability": 0.09, "debt": 0.40, "valuation": 0.30,
        "market_sensitivity": 0.75, "event_sensitivity": 0.85,
    },
    # Healthcare
    {
        "symbol": "BWPH", "name": "BlueWave Pharma", "sector": "Healthcare",
        "base_price": 1680.0, "volatility": 0.022, "beta": 0.7,
        "growth": 0.14, "profitability": 0.20, "debt": 0.20, "valuation": 0.60,
        "market_sensitivity": 0.7, "event_sensitivity": 0.9,
    },
    {
        "symbol": "HLXH", "name": "Helix Healthcare", "sector": "Healthcare",
        "base_price": 890.0, "volatility": 0.018, "beta": 0.65,
        "growth": 0.11, "profitability": 0.17, "debt": 0.18, "valuation": 0.55,
        "market_sensitivity": 0.65, "event_sensitivity": 0.85,
    },
    # Automobile
    {
        "symbol": "NVMT", "name": "Nova Motors", "sector": "Automobile",
        "base_price": 2340.0, "volatility": 0.024, "beta": 1.2,
        "growth": 0.10, "profitability": 0.12, "debt": 0.35, "valuation": 0.42,
        "market_sensitivity": 1.2, "event_sensitivity": 0.6,
    },
    {
        "symbol": "CRSA", "name": "Crescent Auto", "sector": "Automobile",
        "base_price": 1450.0, "volatility": 0.022, "beta": 1.15,
        "growth": 0.08, "profitability": 0.10, "debt": 0.38, "valuation": 0.38,
        "market_sensitivity": 1.15, "event_sensitivity": 0.55,
    },
    # FMCG
    {
        "symbol": "EVGR", "name": "Evergreen FMCG", "sector": "FMCG",
        "base_price": 4200.0, "volatility": 0.014, "beta": 0.6,
        "growth": 0.08, "profitability": 0.18, "debt": 0.15, "valuation": 0.55,
        "market_sensitivity": 0.6, "event_sensitivity": 0.4,
    },
    {
        "symbol": "PNCR", "name": "Pioneer Consumer", "sector": "FMCG",
        "base_price": 1890.0, "volatility": 0.013, "beta": 0.55,
        "growth": 0.07, "profitability": 0.16, "debt": 0.12, "valuation": 0.50,
        "market_sensitivity": 0.55, "event_sensitivity": 0.35,
    },
    {
        "symbol": "QNRT", "name": "Quantum Retail", "sector": "FMCG",
        "base_price": 890.0, "volatility": 0.021, "beta": 0.8,
        "growth": 0.13, "profitability": 0.10, "debt": 0.22, "valuation": 0.45,
        "market_sensitivity": 0.8, "event_sensitivity": 0.5,
    },
    # Telecom
    {
        "symbol": "SLTM", "name": "Stellar Telecom", "sector": "Telecom",
        "base_price": 520.0, "volatility": 0.020, "beta": 0.85,
        "growth": 0.06, "profitability": 0.08, "debt": 0.60, "valuation": 0.32,
        "market_sensitivity": 0.85, "event_sensitivity": 0.5,
    },
    # Infrastructure
    {
        "symbol": "IDUS", "name": "Indus Infrastructure", "sector": "Infrastructure",
        "base_price": 380.0, "volatility": 0.016, "beta": 0.9,
        "growth": 0.09, "profitability": 0.10, "debt": 0.50, "valuation": 0.36,
        "market_sensitivity": 0.9, "event_sensitivity": 0.45,
    },
    {
        "symbol": "ATLS", "name": "Atlas Industries", "sector": "Infrastructure",
        "base_price": 560.0, "volatility": 0.018, "beta": 0.85,
        "growth": 0.08, "profitability": 0.09, "debt": 0.45, "valuation": 0.34,
        "market_sensitivity": 0.85, "event_sensitivity": 0.4,
    },
    # Defence
    {
        "symbol": "ARDF", "name": "Archer Defence", "sector": "Defence",
        "base_price": 2890.0, "volatility": 0.016, "beta": 0.7,
        "growth": 0.12, "profitability": 0.14, "debt": 0.20, "valuation": 0.50,
        "market_sensitivity": 0.7, "event_sensitivity": 0.6,
    },
    # Logistics
    {
        "symbol": "PRLG", "name": "Prime Logistics", "sector": "Logistics",
        "base_price": 740.0, "volatility": 0.019, "beta": 0.95,
        "growth": 0.10, "profitability": 0.11, "debt": 0.30, "valuation": 0.42,
        "market_sensitivity": 0.95, "event_sensitivity": 0.5,
    },
]

SECTORS = list({s["sector"] for s in STOCK_UNIVERSE})

# ─── Market Regime Parameters ────────────────────────────────────────────────
REGIME_PARAMS = {
    "BULL": {
        "daily_drift_range": (0.003, 0.006),   # 0.3–0.6% per day
        "vol_multiplier": 0.8,
        "transition_probs": {"BULL": 0.75, "STABLE": 0.20, "VOLATILE": 0.05, "BEAR": 0.0, "CRISIS": 0.0},
        "min_days": 5, "max_days": 20,
    },
    "STABLE": {
        "daily_drift_range": (-0.001, 0.002),
        "vol_multiplier": 1.0,
        "transition_probs": {"BULL": 0.20, "STABLE": 0.60, "VOLATILE": 0.15, "BEAR": 0.05, "CRISIS": 0.0},
        "min_days": 8, "max_days": 25,
    },
    "VOLATILE": {
        "daily_drift_range": (-0.003, 0.003),
        "vol_multiplier": 1.8,
        "transition_probs": {"BULL": 0.15, "STABLE": 0.35, "VOLATILE": 0.30, "BEAR": 0.15, "CRISIS": 0.05},
        "min_days": 3, "max_days": 12,
    },
    "BEAR": {
        "daily_drift_range": (-0.005, -0.001),
        "vol_multiplier": 1.4,
        "transition_probs": {"BULL": 0.05, "STABLE": 0.25, "VOLATILE": 0.25, "BEAR": 0.40, "CRISIS": 0.05},
        "min_days": 5, "max_days": 18,
    },
    "CRISIS": {
        "daily_drift_range": (-0.015, -0.005),
        "vol_multiplier": 2.5,
        "transition_probs": {"BULL": 0.0, "STABLE": 0.10, "VOLATILE": 0.30, "BEAR": 0.45, "CRISIS": 0.15},
        "min_days": 2, "max_days": 8,
    },
}

# Sector sensitivity to market (how much each sector correlates with market factor)
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

# ─── Career Levels ────────────────────────────────────────────────────────────
CAREER_LEVELS = {
    1: {
        "title": "Head of Investments",
        "xp_required": 0,
        "xp_to_next": 1000,
        "capital_limit": 100 * CRORE,
    },
    2: {
        "title": "Investment Manager",
        "xp_required": 1000,
        "xp_to_next": 3000,
        "capital_limit": 250 * CRORE,
    },
    3: {
        "title": "Senior Investment Manager",
        "xp_required": 3000,
        "xp_to_next": 7000,
        "capital_limit": 500 * CRORE,
    },
}

# ─── Index Starting Values ────────────────────────────────────────────────────
INDEX_DEFAULTS = {
    "nifty": 24500.0,
    "sensex": 80500.0,
    "bank_nifty": 51000.0,
    "india_vix": 14.5,
    "usdinr": 83.50,
    "gold": 72000.0,   # per 10g in INR
    "nasdaq": 17500.0,
    "sp500": 5450.0,
}
