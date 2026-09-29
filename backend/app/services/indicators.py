"""
Technical indicators for the research terminal (SMA, EMA, Bollinger, RSI, MACD, ATR)
and daily aggregation of hourly candles. Research tools — not predictions.
"""
from __future__ import annotations

from typing import Optional

import numpy as np


def aggregate_daily(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        d = r["t"][:10]
        if out and out[-1]["t"] == d:
            c = out[-1]
            c["h"] = max(c["h"], r["h"])
            c["l"] = min(c["l"], r["l"])
            c["c"] = r["c"]
            c["v"] += r["v"]
        else:
            out.append({"t": d, "o": r["o"], "h": r["h"], "l": r["l"], "c": r["c"], "v": r["v"]})
    return out


def _nan_to_none(a: np.ndarray) -> list[Optional[float]]:
    return [None if not np.isfinite(x) else round(float(x), 4) for x in a]


def sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    if len(x) >= n:
        c = np.cumsum(np.insert(x, 0, 0.0))
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    if len(x) == 0:
        return out
    k = 2 / (n + 1)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = x[i] * k + out[i - 1] * (1 - k)
    out[: min(n - 1, len(x))] = np.nan
    return out


def rsi(x: np.ndarray, n: int = 14) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    if len(x) <= n:
        return out
    d = np.diff(x)
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    au, ad = up[:n].mean(), dn[:n].mean()
    for i in range(n, len(x)):
        if i > n:
            au = (au * (n - 1) + up[i - 1]) / n
            ad = (ad * (n - 1) + dn[i - 1]) / n
        out[i] = 100 - 100 / (1 + au / ad) if ad > 0 else 100.0
    return out


def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    prev = np.concatenate([[c[0]], c[:-1]]) if len(c) else c
    tr = np.maximum.reduce([h - l, np.abs(h - prev), np.abs(l - prev)]) if len(c) else c
    return ema(tr, n)


def compute(rows: list[dict]) -> dict:
    if not rows:
        return {}
    c = np.array([r["c"] for r in rows], dtype=float)
    h = np.array([r["h"] for r in rows], dtype=float)
    l = np.array([r["l"] for r in rows], dtype=float)
    mid = sma(c, 20)
    sd = np.full_like(c, np.nan)
    for i in range(19, len(c)):
        sd[i] = c[i - 19:i + 1].std()
    e12, e26 = ema(c, 12), ema(c, 26)
    macd = e12 - e26
    sig = np.full_like(c, np.nan)
    valid = np.where(np.isfinite(macd))[0]
    if len(valid):
        sig[valid] = ema(macd[valid], 9)
    return {
        "sma20": _nan_to_none(mid),
        "sma50": _nan_to_none(sma(c, 50)),
        "ema20": _nan_to_none(ema(c, 20)),
        "bb_upper": _nan_to_none(mid + 2 * sd),
        "bb_lower": _nan_to_none(mid - 2 * sd),
        "rsi14": _nan_to_none(rsi(c, 14)),
        "macd": _nan_to_none(macd),
        "macd_signal": _nan_to_none(sig),
        "macd_hist": _nan_to_none(macd - sig),
        "atr14": _nan_to_none(atr(h, l, c, 14)),
    }
