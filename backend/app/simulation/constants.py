"""
Game rules and static configuration shared by every engine.

All companies, indices, institutions and people are fictional. Index names are
deliberately generic ("Bharat 50", "Dalal 30", ...) so nothing implies a real
exchange product or live data feed.
"""
from __future__ import annotations

CURRENCY = "₹"
CRORE = 10_000_000
LAKH = 100_000

FIRM_NAME = "Apex Capital"
EXCHANGE_NAME = "Dalal Street Exchange"

# --------------------------------------------------------------------------- #
# Time
# --------------------------------------------------------------------------- #
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 17
TRADING_HOURS_PER_DAY = MARKET_CLOSE_HOUR - MARKET_OPEN_HOUR  # 8
SUBSTEPS_PER_HOUR = 12  # 5-minute ticks inside each simulated hour
QUARTER_DAYS = 90
CAREER_YEAR_DAYS = 360
PAID_LEAVE_PER_YEAR = 60
WARMUP_BUSINESS_DAYS = 45  # pre-game history so charts are never empty

# --------------------------------------------------------------------------- #
# Trading
# --------------------------------------------------------------------------- #
FEE_RATE = 0.0002  # brokerage + exchange charges (0.02%)
STT_RATE = 0.001  # securities transaction tax on sells (0.1%)
MIN_FEE = 20.0
IMPACT_COEFF = 0.008  # price impact per unit of (order qty / hourly volume)
MAX_IMPACT = 0.012

# --------------------------------------------------------------------------- #
# Risk policy (Apex Capital "MEDIUM" risk profile)
# --------------------------------------------------------------------------- #
RISK_POLICY = {
    "MEDIUM": {
        "max_single_stock": 0.15,
        "max_sector": 0.40,
        "max_drawdown": 0.10,
        "min_cash": 0.02,
    },
}
TERMINATION_DRAWDOWN = 0.20  # the board fires you on the spot beyond this

# --------------------------------------------------------------------------- #
# Stock universe (20 fictional listed companies)
# volatility = base daily volatility; valuation = 0 (cheap) .. 1 (expensive)
# --------------------------------------------------------------------------- #
STOCK_UNIVERSE = [
    {"symbol": "AKSH", "name": "Akashdeep Technologies", "sector": "Technology", "base_price": 3240.0,
     "volatility": 0.021, "beta": 1.30, "growth": 0.18, "profitability": 0.22, "debt": 0.10, "valuation": 0.72,
     "event_sensitivity": 0.70, "shares_cr": 36.0,
     "about": "IT services and cloud consulting for global banks."},
    {"symbol": "TRGM", "name": "Tarangam Systems", "sector": "Technology", "base_price": 1890.0,
     "volatility": 0.019, "beta": 1.20, "growth": 0.14, "profitability": 0.19, "debt": 0.08, "valuation": 0.62,
     "event_sensitivity": 0.60, "shares_cr": 41.0,
     "about": "Enterprise networking hardware and managed security."},
    {"symbol": "VYMK", "name": "Vyomika Software", "sector": "Technology", "base_price": 2150.0,
     "volatility": 0.026, "beta": 1.45, "growth": 0.24, "profitability": 0.15, "debt": 0.05, "valuation": 0.84,
     "event_sensitivity": 0.85, "shares_cr": 18.0,
     "about": "High-growth SaaS platform for payments and analytics."},
    {"symbol": "GMBK", "name": "Ganga Meridian Bank", "sector": "Banking", "base_price": 1580.0,
     "volatility": 0.016, "beta": 1.10, "growth": 0.13, "profitability": 0.17, "debt": 0.62, "valuation": 0.48,
     "event_sensitivity": 0.60, "shares_cr": 76.0,
     "about": "Large private-sector bank with a strong retail franchise."},
    {"symbol": "KVTB", "name": "Kaveri Trust Bank", "sector": "Banking", "base_price": 640.0,
     "volatility": 0.019, "beta": 1.20, "growth": 0.10, "profitability": 0.12, "debt": 0.70, "valuation": 0.30,
     "event_sensitivity": 0.65, "shares_cr": 110.0,
     "about": "Mid-sized lender, cheap on book value, patchy asset quality."},
    {"symbol": "SHRF", "name": "Shreyas Capital Finance", "sector": "Finance", "base_price": 1240.0,
     "volatility": 0.021, "beta": 1.15, "growth": 0.16, "profitability": 0.15, "debt": 0.58, "valuation": 0.55,
     "event_sensitivity": 0.60, "shares_cr": 30.0,
     "about": "Consumer and SME lending NBFC."},
    {"symbol": "AGNI", "name": "Agnivayu Energy", "sector": "Energy", "base_price": 340.0,
     "volatility": 0.022, "beta": 0.85, "growth": 0.07, "profitability": 0.11, "debt": 0.45, "valuation": 0.28,
     "event_sensitivity": 0.80, "shares_cr": 240.0,
     "about": "Integrated oil refining and fuel retail."},
    {"symbol": "PRKS", "name": "Prakashpath Solar", "sector": "Energy", "base_price": 210.0,
     "volatility": 0.030, "beta": 1.10, "growth": 0.26, "profitability": 0.07, "debt": 0.55, "valuation": 0.80,
     "event_sensitivity": 0.90, "shares_cr": 150.0,
     "about": "Utility-scale solar developer; policy-sensitive."},
    {"symbol": "DHAN", "name": "Dhanvantari Pharma", "sector": "Healthcare", "base_price": 1680.0,
     "volatility": 0.018, "beta": 0.70, "growth": 0.12, "profitability": 0.20, "debt": 0.18, "valuation": 0.58,
     "event_sensitivity": 0.90, "shares_cr": 24.0,
     "about": "Generic drugs exporter; exposed to regulator inspections."},
    {"symbol": "AROG", "name": "Arogyam Healthcare", "sector": "Healthcare", "base_price": 890.0,
     "volatility": 0.015, "beta": 0.60, "growth": 0.13, "profitability": 0.16, "debt": 0.22, "valuation": 0.52,
     "event_sensitivity": 0.60, "shares_cr": 28.0,
     "about": "Hospital chain across tier-1 and tier-2 cities."},
    {"symbol": "RATH", "name": "Rathmotion Motors", "sector": "Automobile", "base_price": 2340.0,
     "volatility": 0.020, "beta": 1.20, "growth": 0.11, "profitability": 0.12, "debt": 0.35, "valuation": 0.44,
     "event_sensitivity": 0.65, "shares_cr": 33.0,
     "about": "Passenger vehicles with an EV transition underway."},
    {"symbol": "CHKR", "name": "Chakra Autoworks", "sector": "Automobile", "base_price": 1450.0,
     "volatility": 0.018, "beta": 1.05, "growth": 0.08, "profitability": 0.13, "debt": 0.30, "valuation": 0.36,
     "event_sensitivity": 0.55, "shares_cr": 29.0,
     "about": "Two-wheelers and auto components."},
    {"symbol": "KESR", "name": "Kesarika Consumer", "sector": "FMCG", "base_price": 4200.0,
     "volatility": 0.011, "beta": 0.55, "growth": 0.08, "profitability": 0.21, "debt": 0.10, "valuation": 0.68,
     "event_sensitivity": 0.40, "shares_cr": 23.0,
     "about": "Packaged foods and personal care staples."},
    {"symbol": "NITY", "name": "Nityam Goods", "sector": "FMCG", "base_price": 1890.0,
     "volatility": 0.012, "beta": 0.55, "growth": 0.07, "profitability": 0.18, "debt": 0.12, "valuation": 0.55,
     "event_sensitivity": 0.35, "shares_cr": 26.0,
     "about": "Household products with deep rural distribution."},
    {"symbol": "BZRB", "name": "Bazaarbeat Retail", "sector": "FMCG", "base_price": 890.0,
     "volatility": 0.022, "beta": 0.95, "growth": 0.19, "profitability": 0.08, "debt": 0.28, "valuation": 0.74,
     "event_sensitivity": 0.60, "shares_cr": 40.0,
     "about": "Fast-growing omnichannel grocery retailer."},
    {"symbol": "DRVN", "name": "Doorvani Telecom", "sector": "Telecom", "base_price": 520.0,
     "volatility": 0.017, "beta": 0.85, "growth": 0.08, "profitability": 0.09, "debt": 0.66, "valuation": 0.40,
     "event_sensitivity": 0.55, "shares_cr": 180.0,
     "about": "Mobile and fibre broadband operator; tariff-sensitive."},
    {"symbol": "SETU", "name": "Setubandh Infrastructure", "sector": "Infrastructure", "base_price": 380.0,
     "volatility": 0.019, "beta": 1.05, "growth": 0.12, "profitability": 0.10, "debt": 0.52, "valuation": 0.38,
     "event_sensitivity": 0.60, "shares_cr": 120.0,
     "about": "Roads, bridges and metro construction."},
    {"symbol": "VJRA", "name": "Vajrashila Industries", "sector": "Infrastructure", "base_price": 560.0,
     "volatility": 0.017, "beta": 0.95, "growth": 0.09, "profitability": 0.11, "debt": 0.42, "valuation": 0.34,
     "event_sensitivity": 0.45, "shares_cr": 90.0,
     "about": "Cement and building materials."},
    {"symbol": "GRDA", "name": "Garudastra Defence", "sector": "Defence", "base_price": 2890.0,
     "volatility": 0.020, "beta": 0.75, "growth": 0.17, "profitability": 0.14, "debt": 0.15, "valuation": 0.70,
     "event_sensitivity": 0.75, "shares_cr": 15.0,
     "about": "Radar, avionics and naval systems."},
    {"symbol": "PTHK", "name": "Pathik Logistics", "sector": "Logistics", "base_price": 740.0,
     "volatility": 0.018, "beta": 0.95, "growth": 0.12, "profitability": 0.10, "debt": 0.32, "valuation": 0.46,
     "event_sensitivity": 0.50, "shares_cr": 35.0,
     "about": "Express freight, warehousing and last-mile delivery."},
]

SECTORS = sorted({s["sector"] for s in STOCK_UNIVERSE})

# How strongly a sector co-moves with the broad market factor (0..1).
SECTOR_MARKET_CORRELATION = {
    "Technology": 0.70, "Banking": 0.75, "Finance": 0.70, "Energy": 0.50, "Healthcare": 0.40,
    "Automobile": 0.65, "FMCG": 0.40, "Telecom": 0.45, "Infrastructure": 0.60, "Defence": 0.40,
    "Logistics": 0.55,
}

# Sensitivities of each sector to macro variables (used by the economy + event engines).
# rates: response to +1 unit of "rate shock"; oil: response to oil shock; global: to global risk factor.
SECTOR_MACRO = {
    "Technology": {"rates": -0.6, "oil": -0.1, "global": 1.0, "inr": 0.6},
    "Banking": {"rates": 0.3, "oil": -0.2, "global": 0.5, "inr": -0.2},
    "Finance": {"rates": -0.8, "oil": -0.2, "global": 0.5, "inr": -0.2},
    "Energy": {"rates": -0.2, "oil": 1.0, "global": 0.4, "inr": -0.1},
    "Healthcare": {"rates": -0.2, "oil": -0.1, "global": 0.3, "inr": 0.5},
    "Automobile": {"rates": -0.7, "oil": -0.7, "global": 0.4, "inr": -0.3},
    "FMCG": {"rates": -0.3, "oil": -0.5, "global": 0.1, "inr": -0.2},
    "Telecom": {"rates": -0.5, "oil": -0.1, "global": 0.2, "inr": -0.1},
    "Infrastructure": {"rates": -0.9, "oil": -0.4, "global": 0.3, "inr": -0.2},
    "Defence": {"rates": -0.2, "oil": -0.1, "global": 0.1, "inr": 0.0},
    "Logistics": {"rates": -0.4, "oil": -0.8, "global": 0.4, "inr": -0.1},
}

# --------------------------------------------------------------------------- #
# Market regimes (hidden from the player; inferred through price action/news)
# drift / vol are daily figures for the broad market factor.
# --------------------------------------------------------------------------- #
REGIMES = {
    "BULL": {"drift": 0.0009, "vol": 0.0062, "sector_vol": 0.0032, "idio_mult": 0.85, "event_rate": 0.9,
             "sentiment": 0.35, "min_days": 8, "max_days": 30,
             "next": {"BULL": 0.0, "STABLE": 0.60, "VOLATILE": 0.30, "BEAR": 0.10, "CRISIS": 0.0}},
    "STABLE": {"drift": 0.0003, "vol": 0.0055, "sector_vol": 0.0030, "idio_mult": 0.80, "event_rate": 0.8,
               "sentiment": 0.10, "min_days": 8, "max_days": 30,
               "next": {"BULL": 0.45, "STABLE": 0.0, "VOLATILE": 0.35, "BEAR": 0.18, "CRISIS": 0.02}},
    "VOLATILE": {"drift": -0.0001, "vol": 0.0105, "sector_vol": 0.0050, "idio_mult": 1.10, "event_rate": 1.3,
                 "sentiment": -0.05, "min_days": 4, "max_days": 14,
                 "next": {"BULL": 0.25, "STABLE": 0.35, "VOLATILE": 0.0, "BEAR": 0.32, "CRISIS": 0.08}},
    "BEAR": {"drift": -0.0007, "vol": 0.0090, "sector_vol": 0.0045, "idio_mult": 1.00, "event_rate": 1.1,
             "sentiment": -0.30, "min_days": 5, "max_days": 18,
             "next": {"BULL": 0.10, "STABLE": 0.40, "VOLATILE": 0.35, "BEAR": 0.0, "CRISIS": 0.15}},
    "CRISIS": {"drift": -0.0030, "vol": 0.0180, "sector_vol": 0.0080, "idio_mult": 1.40, "event_rate": 1.8,
               "sentiment": -0.70, "min_days": 2, "max_days": 7,
               "next": {"BULL": 0.0, "STABLE": 0.15, "VOLATILE": 0.50, "BEAR": 0.35, "CRISIS": 0.0}},
}
INITIAL_REGIME_WEIGHTS = {"BULL": 0.30, "STABLE": 0.40, "VOLATILE": 0.20, "BEAR": 0.10, "CRISIS": 0.0}

# --------------------------------------------------------------------------- #
# Simulated benchmark/indicator tickers — generic names, simulated values.
# --------------------------------------------------------------------------- #
INDEX_DEFS = [
    {"key": "BH50", "name": "BHARAT 50", "base": 24500.0, "kind": "equity_broad"},
    {"key": "DL30", "name": "DALAL 30", "base": 80500.0, "kind": "equity_large"},
    {"key": "BKX", "name": "BHARAT BANK", "base": 51000.0, "kind": "equity_bank"},
    {"key": "BVIX", "name": "BHARAT VOL", "base": 14.5, "kind": "volatility"},
    {"key": "USDINR", "name": "USD/INR", "base": 83.50, "kind": "fx"},
    {"key": "GOLD", "name": "GOLD ₹/10g", "base": 72000.0, "kind": "gold"},
    {"key": "UST100", "name": "US TECH 100", "base": 17500.0, "kind": "global_tech"},
    {"key": "US500", "name": "US 500", "base": 5450.0, "kind": "global_broad"},
]
LARGE_CAP_COUNT = 12  # DALAL 30 tracks the 12 largest by market cap

# --------------------------------------------------------------------------- #
# Career ladder. Level 1 is the playable vertical slice; the others are wired
# into the same review/promotion machinery so they can be expanded later.
# --------------------------------------------------------------------------- #
CAREER_LEVELS = {
    1: {"title": "Head of Investments", "target_return": 0.12, "max_drawdown": 0.10, "capital_add": 0,
        "delegate": None,
        "unlocks": ["Equities", "Buy / Sell", "Portfolio", "Research desk", "Block deals"]},
    2: {"title": "Investment Director", "target_return": 0.10, "max_drawdown": 0.09, "capital_add": 150 * CRORE,
        "delegate": "junior_analyst",
        "unlocks": ["Sector allocation", "Research team hiring", "Junior analyst delegation"]},
    3: {"title": "Senior Investment Director", "target_return": 0.10, "max_drawdown": 0.085, "capital_add": 250 * CRORE,
        "delegate": "portfolio_manager",
        "unlocks": ["Bonds", "IPOs", "Hedging", "Advanced risk"]},
    4: {"title": "Portfolio Director", "target_return": 0.09, "max_drawdown": 0.08, "capital_add": 500 * CRORE,
        "delegate": "investment_team",
        "unlocks": ["M&A", "Multiple portfolios", "Institutional clients"]},
    5: {"title": "Chief Investment Officer", "target_return": 0.09, "max_drawdown": 0.075, "capital_add": 1000 * CRORE,
        "delegate": "investment_team",
        "unlocks": ["Investment teams", "Large capital", "Board decisions"]},
    6: {"title": "Managing Director", "target_return": 0.08, "max_drawdown": 0.07, "capital_add": 2000 * CRORE,
        "delegate": "division",
        "unlocks": ["Multiple divisions", "Competitor firms", "Large deals"]},
    7: {"title": "Chief Executive Officer", "target_return": 0.08, "max_drawdown": 0.07, "capital_add": 5000 * CRORE,
        "delegate": "division",
        "unlocks": ["Run the entire investment organisation"]},
}
MAX_LEVEL = max(CAREER_LEVELS)
XP_PER_LEVEL = [0, 1000, 2500, 4500, 7000, 10000, 14000, 99999]

STARTING_CAPITAL = 100 * CRORE
STARTING_REPUTATION = 60.0
