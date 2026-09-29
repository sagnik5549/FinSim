"""
Market engine — multi-factor stochastic price simulation.

Every 5-minute tick, each stock's log-return is

    r = beta * market + sector + drift * dt + idiosyncratic + event jumps

where
  * market  — regime-dependent drift/volatility (hidden regime), global risk appetite
  * sector  — sector sentiment + macro sensitivities (rates, oil, global, INR)
  * drift   — fundamentals (growth/profitability/debt), mean reversion to a hidden
              fair value, sentiment, momentum, institutional flows, active events
  * noise   — fat-tailed (Student-t) shocks scaled by stock volatility and regime

Nothing here looks at the player's holdings.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

import numpy as np

from app.simulation.constants import (
    INDEX_DEFS,
    INITIAL_REGIME_WEIGHTS,
    LARGE_CAP_COUNT,
    REGIMES,
    SECTOR_MACRO,
    SECTORS,
    STOCK_UNIVERSE,
    SUBSTEPS_PER_HOUR,
    TRADING_HOURS_PER_DAY,
)
from app.simulation.state import GameState, IndexState, MarketState, StockState

SPARK_LEN = 40
DT = 1.0 / (TRADING_HOURS_PER_DAY * SUBSTEPS_PER_HOUR)  # fraction of a trading day per tick
T_SCALE = math.sqrt(3.0 / 5.0)  # normalises Student-t(5) to unit variance
VIX_TARGET = {"BULL": 12.0, "STABLE": 13.5, "VOLATILE": 20.0, "BEAR": 19.0, "CRISIS": 32.0}


def _t(rng: np.random.Generator, size=None):
    return rng.standard_t(5, size=size) * T_SCALE


# --------------------------------------------------------------------------- #
# Creation
# --------------------------------------------------------------------------- #
def create_market(rng: np.random.Generator) -> MarketState:
    regimes = list(INITIAL_REGIME_WEIGHTS)
    weights = np.array([INITIAL_REGIME_WEIGHTS[r] for r in regimes])
    regime = regimes[int(rng.choice(len(regimes), p=weights / weights.sum()))]
    params = REGIMES[regime]
    m = MarketState(
        regime=regime,
        regime_days=0,
        regime_len=int(rng.integers(params["min_days"], params["max_days"] + 1)),
        sector_sentiment={s: float(rng.normal(0, 0.15)) for s in SECTORS},
        sector_level={s: 0.0 for s in SECTORS},
    )
    e = m.economy
    e.inflation = round(float(rng.normal(5.0, 0.6)), 2)
    e.gdp_growth = round(float(rng.normal(6.7, 0.5)), 2)
    e.policy_rate = 6.50
    e.oil = round(float(rng.normal(82, 6)), 2)
    return m


def create_stocks(rng: np.random.Generator) -> dict[str, StockState]:
    """Seeded perturbation of the universe so every career has a different market."""
    stocks: dict[str, StockState] = {}
    for cfg in STOCK_UNIVERSE:
        jitter = lambda v, sd, lo=0.0, hi=5.0: float(np.clip(v * math.exp(rng.normal(0, sd)), lo, hi))
        price = round(cfg["base_price"] * math.exp(rng.normal(0, 0.12)), 2)
        valuation = float(np.clip(cfg["valuation"] + rng.normal(0, 0.06), 0.05, 0.95))
        pe = 10 + valuation * 50
        vol = jitter(cfg["volatility"], 0.10, 0.008, 0.05)
        shares = cfg["shares_cr"] * 1e7
        daily_turnover = price * shares * float(rng.uniform(0.0022, 0.0045))
        stocks[cfg["symbol"]] = StockState(
            symbol=cfg["symbol"],
            name=cfg["name"],
            sector=cfg["sector"],
            about=cfg["about"],
            price=price,
            prev_close=price,
            day_open=price,
            day_high=price,
            day_low=price,
            avg_hourly_volume=daily_turnover / price / TRADING_HOURS_PER_DAY,
            shares_cr=cfg["shares_cr"],
            volatility=vol,
            beta=jitter(cfg["beta"], 0.08, 0.3, 2.0),
            growth=jitter(cfg["growth"], 0.15, 0.01, 0.5),
            profitability=jitter(cfg["profitability"], 0.12, 0.02, 0.4),
            debt=float(np.clip(cfg["debt"] + rng.normal(0, 0.05), 0.02, 0.9)),
            valuation=valuation,
            eps=price / pe,
            fair_value=price * math.exp(rng.normal(0, 0.09)),
            earnings_quality=float(np.clip(rng.normal(0, 0.5), -1, 1)),
            sentiment=float(np.clip(rng.normal(0, 0.2), -1, 1)),
            event_sensitivity=cfg["event_sensitivity"],
            realized_vol=vol,
            spark=[price],
            week_ago_price=price,
        )
    return stocks


def market_cap(s: StockState) -> float:
    return s.price * s.shares_cr * 1e7


def create_indices(state: GameState, rng: np.random.Generator) -> dict[str, IndexState]:
    caps = {k: market_cap(s) for k, s in state.stocks.items()}
    large = sorted(caps, key=caps.get, reverse=True)[:LARGE_CAP_COUNT]
    banks = [k for k, s in state.stocks.items() if s.sector in ("Banking", "Finance")]
    state.flags["index_members"] = {"BH50": list(caps), "DL30": large, "BKX": banks}
    state.flags["index_base_cap"] = {
        "BH50": sum(caps.values()),
        "DL30": sum(caps[k] for k in large),
        "BKX": sum(caps[k] for k in banks),
    }
    out = {}
    for d in INDEX_DEFS:
        base = d["base"] * math.exp(rng.normal(0, 0.03)) if d["kind"] not in ("volatility",) else d["base"]
        out[d["key"]] = IndexState(key=d["key"], name=d["name"], kind=d["kind"], value=round(base, 2),
                                   prev_close=round(base, 2), day_open=round(base, 2), spark=[round(base, 2)])
    state.flags["index_base_value"] = {k: v.value for k, v in out.items()}
    return out


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def sector_macro_drift(market: MarketState, sector: str) -> float:
    e = market.economy
    sens = SECTOR_MACRO[sector]
    return 0.0015 * (
        sens["rates"] * e.rate_pressure
        + sens["oil"] * e.oil_shock
        + sens["global"] * e.global_risk
        + sens["inr"] * e.inr_shock
    )


def fundamental_drift(s: StockState) -> float:
    """Daily log drift from fundamentals, valuation gap, sentiment, momentum and flows."""
    # Equity risk premium scales with beta (~2.5% a quarter at beta 1) + quality tilt
    fund = 0.0004 * s.beta + (s.growth - 0.12) * 0.004 + (s.profitability - 0.14) * 0.003 - (s.debt - 0.35) * 0.0012
    reversion = 0.015 * math.log(s.fair_value / s.price)
    return fund + reversion + 0.0012 * s.sentiment + 0.03 * s.momentum + 0.0015 * s.institutional_pressure


def index_value(state: GameState, key: str, prices: dict[str, float] | None = None) -> float:
    members = state.flags["index_members"][key]
    base_cap = state.flags["index_base_cap"][key]
    base_val = state.flags["index_base_value"][key]
    px = prices or {k: s.price for k, s in state.stocks.items()}
    cap = sum(px[k] * state.stocks[k].shares_cr * 1e7 for k in members)
    return base_val * cap / base_cap


# --------------------------------------------------------------------------- #
# Hour simulation
# --------------------------------------------------------------------------- #
def simulate_hour(
    state: GameState,
    rng: np.random.Generator,
    start: datetime,
    jumps: dict[str, float],
    event_drift: dict[str, float],
    vol_boost: dict[str, float],
    market_vol_boost: float,
) -> dict[str, float]:
    """Simulate one trading hour. Returns each stock's hourly log return."""
    m = state.market
    R = REGIMES[m.regime]
    syms = list(state.stocks)
    stocks = [state.stocks[k] for k in syms]
    n = len(stocks)
    sec_idx = np.array([SECTORS.index(s.sector) for s in stocks])
    beta = np.array([s.beta for s in stocks])
    vol = np.array([s.volatility for s in stocks]) * R["idio_mult"] * np.array([1 + vol_boost.get(k, 0.0) for k in syms])
    drift = np.array([fundamental_drift(s) + event_drift.get(k, 0.0) * TRADING_HOURS_PER_DAY
                      for k, s in zip(syms, stocks)])
    sector_drift = np.array([
        sector_macro_drift(m, sec) + 0.0012 * m.sector_sentiment.get(sec, 0.0) for sec in SECTORS
    ])
    jump_vec = np.array([jumps.get(k, 0.0) for k in syms])
    e = m.economy

    mkt_drift = R["drift"] + 0.0010 * e.global_risk
    mkt_vol = R["vol"] * (1 + market_vol_boost)
    sqdt = math.sqrt(DT)

    p0 = np.array([s.price for s in stocks])
    path = np.empty((SUBSTEPS_PER_HOUR + 1, n))
    path[0] = p0
    logp = np.log(p0)
    mkt_sum = 0.0
    for k in range(SUBSTEPS_PER_HOUR):
        zm = float(_t(rng))
        zs = _t(rng, len(SECTORS))
        zi = _t(rng, n)
        mret = mkt_drift * DT + mkt_vol * sqdt * zm
        sret = sector_drift * DT + R["sector_vol"] * sqdt * zs
        r = beta * mret + sret[sec_idx] + drift * DT + vol * 0.75 * sqdt * zi
        if k == SUBSTEPS_PER_HOUR - 1:
            r = r + jump_vec
        logp = logp + r
        path[k + 1] = np.exp(logp)
        mkt_sum += mret
    m.market_level += mkt_sum
    for i, sec in enumerate(SECTORS):
        m.sector_level[sec] = m.sector_level.get(sec, 0.0) + float(sector_drift[i])

    hour_ret = np.log(path[-1] / path[0])
    hour_of_day = start.hour - 9
    u_shape = 1.35 if hour_of_day in (0, 7) else (0.8 if hour_of_day in (3, 4) else 1.0)
    t_key = start.isoformat()
    candles = state.outbox("stock_prices")
    ret_map: dict[str, float] = {}
    for i, (k, s) in enumerate(zip(syms, stocks)):
        col = path[:, i]
        hourly_sigma = max(s.volatility / math.sqrt(TRADING_HOURS_PER_DAY), 1e-4)
        surprise = abs(hour_ret[i]) / hourly_sigma
        vol_units = s.avg_hourly_volume * u_shape * (1 + 0.6 * surprise + 1.5 * vol_boost.get(k, 0.0))
        volume = float(vol_units * math.exp(rng.normal(0, 0.25)))
        o, h, l, c = float(col[0]), float(col.max()), float(col.min()), float(col[-1])
        s.price = round(c, 2)
        s.day_high = max(s.day_high, h)
        s.day_low = min(s.day_low, l)
        s.volume_today += volume
        # State dynamics
        hr = float(hour_ret[i])
        ret_map[k] = hr
        s.momentum = 0.94 * s.momentum + 0.06 * hr * TRADING_HOURS_PER_DAY
        s.realized_vol = math.sqrt(0.97 * s.realized_vol ** 2 + 0.03 * (hr ** 2) * TRADING_HOURS_PER_DAY)
        s.sentiment = float(np.clip(s.sentiment * 0.98 + rng.normal(0, 0.02) + 0.1 * hr, -1, 1))
        s.institutional_pressure *= 0.985
        s.fair_value *= math.exp(s.growth / (252 * TRADING_HOURS_PER_DAY) + rng.normal(0, 0.0015))
        s.spark = (s.spark + [s.price])[-SPARK_LEN:]
        candles.append({"symbol": k, "t": t_key, "o": round(o, 2), "h": round(h, 2), "l": round(l, 2),
                        "c": round(c, 2), "v": int(volume)})

    # Sector sentiment mean-reverts toward the regime's mood
    for sec in SECTORS:
        cur = m.sector_sentiment.get(sec, 0.0)
        m.sector_sentiment[sec] = float(np.clip(cur + 0.03 * (R["sentiment"] - cur) + rng.normal(0, 0.03), -1, 1))

    # Indices (paths derived from the stock paths)
    idx_paths = _simulate_index_hour(state, rng, syms, path, mkt_sum, start)
    state.last_tick.t = start
    state.last_tick.paths = {k: [round(float(v), 2) for v in path[:, i]] for i, k in enumerate(syms)}
    state.last_tick.paths.update({k: [round(v, 4) for v in p] for k, p in idx_paths.items()})
    return ret_map


def _simulate_index_hour(state, rng, syms, path, mkt_sum, start) -> dict[str, list[float]]:
    m = state.market
    e = m.economy
    out: dict[str, list[float]] = {}
    shares = np.array([state.stocks[k].shares_cr * 1e7 for k in syms])
    pos = {k: i for i, k in enumerate(syms)}
    for key in ("BH50", "DL30", "BKX"):
        members = [pos[k] for k in state.flags["index_members"][key]]
        caps = (path[:, members] * shares[members]).sum(axis=1)
        vals = state.flags["index_base_value"][key] * caps / state.flags["index_base_cap"][key]
        out[key] = [float(v) for v in vals]

    n = SUBSTEPS_PER_HOUR
    # Volatility index: mean-reverts to regime level, spikes on market drops.
    vix = state.indices["BVIX"].value
    vix_path = [vix]
    target = VIX_TARGET[m.regime] * (1 + 0.5 * max(0.0, -e.global_risk))
    for _ in range(n):
        vix = max(8.0, vix + 0.02 * (target - vix) - 45 * mkt_sum / n + rng.normal(0, 0.06))
        vix_path.append(vix)
    out["BVIX"] = vix_path

    def walk(key, sigma_hour, drift_hour):
        v = state.indices[key].value
        p = [v]
        for _ in range(n):
            v *= math.exp(drift_hour / n + sigma_hour / math.sqrt(n) * rng.normal())
            p.append(v)
        return p

    out["USDINR"] = walk("USDINR", 0.0006, 0.00002 + 0.0004 * e.inr_shock - 0.0002 * e.global_risk)
    out["GOLD"] = walk("GOLD", 0.0016, 0.00003 - 0.0006 * e.global_risk + 0.0008 * (m.regime == "CRISIS"))
    # US futures drift slightly during Indian hours; the big moves happen overnight.
    g = walk("US500", 0.0012, 0.00005 + 0.0005 * e.global_risk)
    out["US500"] = g
    out["UST100"] = [state.indices["UST100"].value * (x / g[0]) ** 1.3 for x in g]
    m.global_level += math.log(g[-1] / g[0])

    t_key = start.isoformat()
    candles = state.outbox("stock_prices")
    for key, p in out.items():
        idx = state.indices[key]
        idx.value = round(p[-1], 4 if key in ("USDINR",) else 2)
        idx.spark = (idx.spark + [idx.value])[-SPARK_LEN:]
        candles.append({"symbol": key, "t": t_key, "o": round(p[0], 4), "h": round(max(p), 4),
                        "l": round(min(p), 4), "c": round(p[-1], 4), "v": 0})
    return out


# --------------------------------------------------------------------------- #
# Sessions, overnight and regimes
# --------------------------------------------------------------------------- #
def overnight(state: GameState, rng: np.random.Generator, from_day: date, to_day: date) -> dict[str, float]:
    """Simulate global markets between sessions; accumulate opening gaps. Returns global move by day."""
    m = state.market
    e = m.economy
    nights = (to_day - from_day).days
    g_total = 0.0
    for _ in range(nights):
        g = rng.normal(0.0004 + 0.0015 * e.global_risk, 0.0070)
        g_total += g
    m.global_level += g_total
    for key, mult in (("US500", 1.0), ("UST100", 1.3)):
        idx = state.indices[key]
        idx.value = round(idx.value * math.exp(g_total * mult + rng.normal(0, 0.002)), 2)
    idx = state.indices["GOLD"]
    idx.value = round(idx.value * math.exp(rng.normal(0.0002, 0.004 * math.sqrt(nights)) - 0.2 * g_total), 2)
    idx = state.indices["USDINR"]
    idx.value = round(idx.value * math.exp(rng.normal(0.0001, 0.0015 * math.sqrt(nights)) - 0.05 * g_total), 4)

    R = REGIMES[m.regime]
    mkt_gap = 0.25 * g_total + rng.normal(R["drift"] * 0.3, R["vol"] * 0.30 * math.sqrt(nights))
    for s in state.stocks.values():
        sens_g = SECTOR_MACRO[s.sector]["global"]
        s.pending_gap += (
            s.beta * mkt_gap
            + 0.15 * sens_g * g_total
            + rng.normal(0, s.volatility * 0.22 * math.sqrt(nights))
        )
    return {"global": g_total}


def open_session(state: GameState) -> None:
    for s in state.stocks.values():
        if s.pending_gap:
            s.price = round(s.price * math.exp(float(np.clip(s.pending_gap, -0.35, 0.35))), 2)
            s.pending_gap = 0.0
        s.day_open = s.price
        s.day_high = s.price
        s.day_low = s.price
        s.volume_today = 0.0
    prices = {k: s.price for k, s in state.stocks.items()}
    for key in ("BH50", "DL30", "BKX"):
        state.indices[key].value = round(index_value(state, key, prices), 2)
    for idx in state.indices.values():
        idx.day_open = idx.value


def close_session(state: GameState) -> None:
    for s in state.stocks.values():
        s.prev_close = s.price
        s.prev_volume = s.volume_today
    for idx in state.indices.values():
        idx.prev_close = idx.value


def daily_regime_step(state: GameState, rng: np.random.Generator, bias: dict[str, float] | None = None) -> bool:
    """Advance the hidden regime by one business day. Returns True if it changed."""
    m = state.market
    m.regime_days += 1
    if m.regime_days < m.regime_len:
        return False
    probs = dict(REGIMES[m.regime]["next"])
    e = m.economy
    # Macro conditions tilt transitions (hawkish/oil/global risk-off -> worse regimes)
    stress = max(0.0, e.rate_pressure) * 0.5 + max(0.0, e.oil_shock) * 0.3 + max(0.0, -e.global_risk) * 0.6
    for r in ("BEAR", "VOLATILE", "CRISIS"):
        if probs.get(r, 0) > 0:
            probs[r] *= 1 + stress
    for r, b in (bias or {}).items():
        if probs.get(r, 0) > 0:
            probs[r] = max(0.0, probs[r] * (1 + float(np.clip(b, -0.25, 0.25))))
    keys = [k for k in probs if probs[k] > 0]
    w = np.array([probs[k] for k in keys])
    new = keys[int(rng.choice(len(keys), p=w / w.sum()))]
    m.regime = new
    m.regime_days = 0
    params = REGIMES[new]
    m.regime_len = int(rng.integers(params["min_days"], params["max_days"] + 1))
    return True


def daily_stock_step(state: GameState) -> None:
    """End-of-day bookkeeping: valuation score from P/E, weekly reference prices."""
    by_sector: dict[str, list[float]] = {}
    for s in state.stocks.values():
        by_sector.setdefault(s.sector, []).append(s.price / s.eps)
    for s in state.stocks.values():
        pe = s.price / s.eps
        s.valuation = float(np.clip((pe - 10) / 50, 0.02, 0.98))


def stock_pe(s: StockState) -> float:
    return s.price / s.eps if s.eps > 0 else 0.0


def period_return(state: GameState, symbol: str) -> float:
    s = state.stocks[symbol]
    return s.price / s.prev_close - 1 if s.prev_close else 0.0


def weekly_reference(state: GameState) -> None:
    for s in state.stocks.values():
        s.week_ago_price = s.price


def hours_between(a: datetime, b: datetime) -> float:
    return (b - a) / timedelta(hours=1)
