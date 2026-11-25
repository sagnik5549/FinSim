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
from app.simulation.state import GameState, HourSession, IndexState, MarketState, StockState

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
# Hour simulation, one minute at a time
#
#   begin_hour()   draws the hour's drift/volatility parameters (events, macro, regime)
#   step_minutes() moves every price forward k minutes (k = 1 for the live clock,
#                  up to 60 when time is skipped); vectorised over minutes and stocks
#   end_hour()     writes the hourly candle and updates the slow state dynamics
# --------------------------------------------------------------------------- #
DERIVED_INDICES = ("BH50", "DL30", "BKX")
RECENT_MINUTES = 6


def _u_shape(hour: int) -> float:
    h = hour - 9
    return 1.35 if h in (0, 7) else (0.8 if h in (3, 4) else 1.0)


def begin_hour(state: GameState, start: datetime, event_drift: dict[str, float], vol_boost: dict[str, float],
               market_vol_boost: float, jumps: dict[str, float]) -> HourSession:
    m = state.market
    R = REGIMES[m.regime]
    e = m.economy
    hs = HourSession(
        start=start,
        drift={k: fundamental_drift(s) + event_drift.get(k, 0.0) * TRADING_HOURS_PER_DAY for k, s in state.stocks.items()},
        vol={k: s.volatility * R["idio_mult"] * (1 + vol_boost.get(k, 0.0)) for k, s in state.stocks.items()},
        vol_boost={k: v for k, v in vol_boost.items() if v},
        sector_drift={sec: sector_macro_drift(m, sec) + 0.0012 * m.sector_sentiment.get(sec, 0.0) for sec in SECTORS},
        mkt_drift=R["drift"] + 0.0010 * e.global_risk,
        mkt_vol=R["vol"] * (1 + market_vol_boost),
        jumps=dict(jumps),
    )
    for k, s in state.stocks.items():
        hs.agg[k] = [s.price, s.price, s.price, 0.0]
    for k, i in state.indices.items():
        hs.agg[k] = [i.value, i.value, i.value, 0.0]
    state.hour = hs
    return hs


def step_minutes(state: GameState, rng: np.random.Generator, k: int, record: bool = True) -> dict[str, np.ndarray]:
    """Advance every price by k one-minute steps inside the current hour.

    Returns per-symbol arrays of shape (k, 4): open, high, low, close of each minute
    (used to trigger resting orders and alerts). Prices, day ranges and volumes in
    `state` are updated to the end of the k minutes."""
    hs = state.hour
    assert hs is not None and 1 <= k <= SUBSTEPS_PER_HOUR - hs.minute
    m = state.market
    R = REGIMES[m.regime]
    syms = list(state.stocks)
    stocks = [state.stocks[x] for x in syms]
    n = len(stocks)
    sec_idx = np.array([SECTORS.index(s.sector) for s in stocks])
    beta = np.array([s.beta for s in stocks])
    vol = np.array([hs.vol[x] for x in syms])
    drift = np.array([hs.drift[x] for x in syms])
    sector_drift = np.array([hs.sector_drift[sec] for sec in SECTORS])
    sqdt = math.sqrt(DT)

    zm = _t(rng, k)
    zs = _t(rng, (k, len(SECTORS)))
    zi = _t(rng, (k, n))
    mret = hs.mkt_drift * DT + hs.mkt_vol * sqdt * zm  # (k,)
    sret = sector_drift * DT + R["sector_vol"] * sqdt * zs  # (k, sectors)
    r = beta[None, :] * mret[:, None] + sret[:, sec_idx] + drift[None, :] * DT + vol[None, :] * 0.75 * sqdt * zi
    if hs.jumps:
        r[0] += np.array([hs.jumps.get(x, 0.0) for x in syms])
        hs.jumps = {}
    p0 = np.array([s.price for s in stocks])
    closes = p0[None, :] * np.exp(np.cumsum(r, axis=0))  # (k, n)
    opens = np.vstack([p0[None, :], closes[:-1]])
    # Intra-minute range: a little beyond the open/close, proportional to per-minute volatility.
    wick = np.abs(rng.normal(0, 1, (2, k, n))) * vol[None, :] * sqdt * 0.35
    highs = np.maximum(opens, closes) * np.exp(wick[0])
    lows = np.minimum(opens, closes) * np.exp(-wick[1])

    # Volume per minute: U-shaped through the day, higher on surprises and event days.
    minute_sigma = np.maximum(vol * sqdt, 1e-5)
    surprise = np.abs(np.log(closes / opens)) / minute_sigma[None, :]
    base = np.array([s.avg_hourly_volume for s in stocks]) / SUBSTEPS_PER_HOUR * _u_shape(hs.start.hour)
    boost = np.array([1.5 * hs.vol_boost.get(x, 0.0) for x in syms])
    vols = base[None, :] * (0.7 + 0.3 * surprise + boost[None, :]) * np.exp(rng.normal(0, 0.3, (k, n)))

    m.market_level += float(mret.sum())
    hs.mkt_sum += float(mret.sum())
    his, los, vsum = highs.max(axis=0).tolist(), lows.min(axis=0).tolist(), vols.sum(axis=0).tolist()
    last = np.round(closes[-1], 2).tolist()
    for i, (x, s) in enumerate(zip(syms, stocks)):
        a = hs.agg[x]
        hi, lo, v = his[i], los[i], vsum[i]
        a[1], a[2], a[3] = max(a[1], hi), min(a[2], lo), a[3] + v
        s.price = last[i]
        if hi > s.day_high:
            s.day_high = hi
        if lo < s.day_low:
            s.day_low = lo
        s.volume_today += v
    ohlc = np.stack([opens, highs, lows, closes], axis=2)  # (k, n, 4)
    out: dict[str, np.ndarray] = {x: ohlc[:, i, :] for i, x in enumerate(syms)}

    idx_bars = _step_indices(state, rng, syms, closes, mret)
    out.update(idx_bars)

    t0 = hs.start + timedelta(minutes=hs.minute)
    hs.minute += k
    if record:
        _record_minutes(state, t0, k, out, {x: vols[:, i] for i, x in enumerate(syms)})
    return out


def _step_indices(state: GameState, rng, syms, closes: np.ndarray, mret: np.ndarray) -> dict[str, np.ndarray]:
    hs = state.hour
    m = state.market
    e = m.economy
    k = closes.shape[0]
    out: dict[str, np.ndarray] = {}
    shares = np.array([state.stocks[x].shares_cr * 1e7 for x in syms])
    pos = {x: i for i, x in enumerate(syms)}

    def finish(key: str, path: np.ndarray, decimals: int = 2) -> None:
        start = state.indices[key].value
        opens = np.concatenate([[start], path[:-1]])
        bars = np.stack([opens, np.maximum(opens, path), np.minimum(opens, path), path], axis=1)
        a = hs.agg[key]
        a[1], a[2] = max(a[1], float(bars[:, 1].max())), min(a[2], float(bars[:, 2].min()))
        state.indices[key].value = round(float(path[-1]), decimals)
        out[key] = bars

    for key in DERIVED_INDICES:
        members = [pos[x] for x in state.flags["index_members"][key]]
        caps = (closes[:, members] * shares[members]).sum(axis=1)
        finish(key, state.flags["index_base_value"][key] * caps / state.flags["index_base_cap"][key])

    # Volatility index: mean-reverts to the regime level and spikes when the market drops.
    target = VIX_TARGET[m.regime] * (1 + 0.5 * max(0.0, -e.global_risk))
    vix = state.indices["BVIX"].value
    noise = rng.normal(0, 0.06 / math.sqrt(5), k)
    vpath = np.empty(k)
    for j in range(k):
        vix = max(8.0, vix + 0.004 * (target - vix) - 45 * float(mret[j]) + float(noise[j]))
        vpath[j] = vix
    finish("BVIX", vpath)

    n = SUBSTEPS_PER_HOUR

    def walk(key: str, sigma_hour: float, drift_hour: float) -> np.ndarray:
        steps = drift_hour / n + sigma_hour / math.sqrt(n) * rng.normal(0, 1, k)
        return state.indices[key].value * np.exp(np.cumsum(steps))

    finish("USDINR", walk("USDINR", 0.0006, 0.00002 + 0.0004 * e.inr_shock - 0.0002 * e.global_risk), 4)
    finish("GOLD", walk("GOLD", 0.0016, 0.00003 - 0.0006 * e.global_risk + 0.0008 * (m.regime == "CRISIS")))
    # US futures drift slightly during Indian hours; the big moves happen overnight.
    us0 = state.indices["US500"].value
    g = walk("US500", 0.0012, 0.00005 + 0.0005 * e.global_risk)
    m.global_level += math.log(float(g[-1]) / us0)
    finish("US500", g)
    finish("UST100", state.indices["UST100"].value * (g / us0) ** 1.3)
    return out


def _record_minutes(state: GameState, t0: datetime, k: int, bars: dict[str, np.ndarray],
                    vols: dict[str, np.ndarray]) -> None:
    rows = state.outbox("minute_prices")
    rec = state.recent
    times = [(t0 + timedelta(minutes=j)).isoformat() for j in range(k)]
    keep = max(0, k - RECENT_MINUTES)
    rec.t = (rec.t + times[keep:])[-RECENT_MINUTES:]
    for sym, b in bars.items():
        v = vols.get(sym)
        vol = v.astype(np.int64).tolist() if v is not None else [0] * k
        ohlc = np.round(b, 4 if sym == "USDINR" else 2).tolist()
        for j in range(k):
            o, h, l, c = ohlc[j]
            rows.append({"symbol": sym, "t": times[j], "o": o, "h": h, "l": l, "c": c, "v": vol[j]})
        lst = rec.bars.get(sym, []) + [[*ohlc[j], vol[j]] for j in range(keep, k)]
        rec.bars[sym] = lst[-RECENT_MINUTES:]


def end_hour(state: GameState, rng: np.random.Generator) -> dict[str, float]:
    """Close the hour: write hourly candles and update momentum, sentiment and fair values."""
    hs = state.hour
    assert hs is not None
    m = state.market
    R = REGIMES[m.regime]
    t_key = hs.start.isoformat()
    candles = state.outbox("stock_prices")
    ret_map: dict[str, float] = {}
    for k, s in state.stocks.items():
        o, h, l, v = hs.agg[k]
        c = s.price
        candles.append({"symbol": k, "t": t_key, "o": round(o, 2), "h": round(max(h, c), 2),
                        "l": round(min(l, c), 2), "c": round(c, 2), "v": int(v)})
        hr = math.log(c / o) if o > 0 else 0.0
        ret_map[k] = hr
        s.momentum = 0.94 * s.momentum + 0.06 * hr * TRADING_HOURS_PER_DAY
        s.realized_vol = math.sqrt(0.97 * s.realized_vol ** 2 + 0.03 * (hr ** 2) * TRADING_HOURS_PER_DAY)
        s.sentiment = float(np.clip(s.sentiment * 0.98 + rng.normal(0, 0.02) + 0.1 * hr, -1, 1))
        s.institutional_pressure *= 0.985
        s.fair_value *= math.exp(s.growth / (252 * TRADING_HOURS_PER_DAY) + rng.normal(0, 0.0015))
        s.spark = (s.spark + [s.price])[-SPARK_LEN:]
    for key, idx in state.indices.items():
        o, h, l, _ = hs.agg[key]
        c = idx.value
        candles.append({"symbol": key, "t": t_key, "o": round(o, 4), "h": round(max(h, c), 4),
                        "l": round(min(l, c), 4), "c": round(c, 4), "v": 0})
        idx.spark = (idx.spark + [idx.value])[-SPARK_LEN:]
    for sec in SECTORS:
        m.sector_level[sec] = m.sector_level.get(sec, 0.0) + hs.sector_drift[sec]
        cur = m.sector_sentiment.get(sec, 0.0)
        m.sector_sentiment[sec] = float(np.clip(cur + 0.03 * (R["sentiment"] - cur) + rng.normal(0, 0.03), -1, 1))
    leftover = hs.jumps
    state.hour = None
    if leftover:
        state.flags["pending_jumps"] = {k: state.flags.get("pending_jumps", {}).get(k, 0.0) + v for k, v in leftover.items()}
    return ret_map


# --------------------------------------------------------------------------- #
# Sessions, overnight and regimes
# --------------------------------------------------------------------------- #
def overnight(state: GameState, rng: np.random.Generator, from_day: date, to_day: date) -> dict[str, float]:
    """Simulate global markets between sessions; accumulate opening gaps. Returns global move by day."""
    roll_previous_close(state)
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
    # Price jumps that landed after the last trade of the previous session open as a gap.
    for k, j in state.flags.pop("pending_jumps", {}).items():
        if k in state.stocks:
            state.stocks[k].pending_gap += j
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
    # The day's change stays on screen after the bell; previous closes roll when the
    # overnight session starts (see roll_previous_close).
    for s in state.stocks.values():
        s.prev_volume = s.volume_today


def roll_previous_close(state: GameState) -> None:
    for s in state.stocks.values():
        s.prev_close = s.price
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
