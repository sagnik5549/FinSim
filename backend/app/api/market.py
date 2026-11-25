from typing import Literal

import zlib

import numpy as np

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import game_id_header
from app.services import game_service as svc
from app.services import indicators
from app.services import repository as repo
from app.services import serializers as ser

router = APIRouter()


@router.get("")
def market(game_id: str = Depends(game_id_header)):
    def build(state):
        return {"clock": ser.clock(state), "stocks": [ser.stock_row(state, s) for s in state.stocks.values()],
                "indices": ser.full_state(state, include_paths=False)["indices"]}
    return svc.read(game_id, build)


@router.get("/calendar")
def calendar(game_id: str = Depends(game_id_header)):
    return svc.read(game_id, lambda s: ser.calendar(s, limit=40))


TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15}


def _bucket(rows: list[dict], minutes: int) -> list[dict]:
    """Aggregate 1-minute rows into n-minute candles aligned to the session clock."""
    if minutes == 1:
        return rows
    out: list[dict] = []
    for r in rows:
        t = r["t"]
        mm = int(t[14:16])
        key = f"{t[:14]}{mm - mm % minutes:02d}:00"
        if out and out[-1]["t"] == key:
            c = out[-1]
            c["h"], c["l"], c["c"], c["v"] = max(c["h"], r["h"]), min(c["l"], r["l"]), r["c"], c["v"] + r["v"]
        else:
            out.append({**r, "t": key})
    return out


def _forming_hour(state, symbol: str) -> dict | None:
    """The hourly candle still being traded (from the live hour's running aggregates)."""
    hs = state.hour
    if hs is None or symbol not in hs.agg or hs.minute == 0:
        return None
    o, h, l, v = hs.agg[symbol]
    c = state.stocks[symbol].price if symbol in state.stocks else state.indices[symbol].value
    return {"t": hs.start.isoformat(), "o": o, "h": max(h, c), "l": min(l, c), "c": c, "v": int(v)}


def depth(state, symbol: str) -> dict:
    """A plausible 5-level order book around the last price (simulated; for display).

    The spread widens with volatility and thins with liquidity, consistent with the
    market-impact model used for fills."""
    s = state.stocks[symbol]
    tick = 0.05 if s.price < 1000 else 0.1 if s.price < 5000 else 0.5
    spread_ticks = max(1, round(s.price * s.realized_vol * 0.02 / tick))
    per_min = max(s.avg_hourly_volume / 60, 50)
    seed = zlib.crc32(f"{state.id}{symbol}{state.now.isoformat()}".encode())
    rng = np.random.default_rng(seed)
    mid = round(s.price / tick) * tick
    bids, asks = [], []
    for i in range(5):
        bq = int(per_min * (0.4 + 0.3 * i) * rng.lognormal(0, 0.45))
        aq = int(per_min * (0.4 + 0.3 * i) * rng.lognormal(0, 0.45))
        bids.append({"price": round(mid - tick * (i + (spread_ticks + 1) // 2), 2), "qty": bq, "orders": int(rng.integers(1, 40))})
        asks.append({"price": round(mid + tick * (i + spread_ticks // 2 + (0 if spread_ticks % 2 else 1)), 2), "qty": aq,
                     "orders": int(rng.integers(1, 40))})
    tb, ta = sum(b["qty"] for b in bids), sum(a["qty"] for a in asks)
    return {"bids": bids, "asks": asks, "total_bid": tb, "total_ask": ta, "tick": tick}


@router.get("/{symbol}")
def stock_detail(symbol: str, tf: Literal["1m", "5m", "15m", "1h", "1d"] = Query("1h"),
                 limit: int = Query(240, ge=20, le=2000), game_id: str = Depends(game_id_header)):
    symbol = symbol.upper()

    def build(state):
        is_index = symbol in state.indices
        if symbol not in state.stocks and not is_index:
            raise HTTPException(status_code=404, detail={"code": "INVALID_SYMBOL", "message": f"Unknown symbol {symbol}"})
        with svc.session() as db:
            if tf in TF_MINUTES:
                k = TF_MINUTES[tf]
                rows = [{"t": r.t.isoformat(), "o": r.o, "h": r.h, "l": r.l, "c": r.c, "v": r.v}
                        for r in repo.minute_candles(db, game_id, symbol, limit=min(6000, (limit + 60) * k))]
                rows = _bucket(rows, k)
            else:
                rows = [{"t": r.t.isoformat(), "o": r.o, "h": r.h, "l": r.l, "c": r.c, "v": r.v}
                        for r in repo.candles(db, game_id, symbol, limit=4000 if tf == "1d" else limit + 60)]
                forming = _forming_hour(state, symbol)
                if forming and (not rows or rows[-1]["t"] < forming["t"]):
                    rows.append(forming)
                if tf == "1d":
                    rows = indicators.aggregate_daily(rows)
        ind = indicators.compute(rows)
        rows, ind = rows[-limit:], {k2: v[-limit:] for k2, v in ind.items()}
        out = {"symbol": symbol, "tf": tf, "candles": rows, "indicators": ind, "as_of": state.now.isoformat()}
        if is_index:
            i = state.indices[symbol]
            out["index"] = {"key": i.key, "name": i.name, "value": i.value,
                            "change_pct": i.value / i.prev_close - 1 if i.prev_close else 0}
            return out
        s = state.stocks[symbol]
        out["stock"] = ser.stock_row(state, s)
        out["fundamentals"] = ser.fundamentals(s)
        out["depth"] = depth(state, symbol)
        out["news"] = [n.model_dump(mode="json") for n in reversed(state.news) if symbol in n.symbols][:15]
        out["events"] = [{"id": e.id, "type": e.type, "title": e.title, "severity": e.severity,
                          "started_at": e.started_at.isoformat(), "active": e.active}
                         for e in reversed(state.events) if symbol in e.affected_symbols and e.category == "company"][:10]
        out["calendar"] = [c for c in ser.calendar(state, limit=40) if c.get("symbol") == symbol]
        out["research"] = [r.model_dump(mode="json") for r in reversed(state.research) if r.symbol == symbol][:3]
        out["theses"] = [t.model_dump(mode="json") for t in reversed(state.theses) if t.symbol == symbol][:5]
        h = state.portfolio.holdings.get(symbol)
        out["position"] = next((x for x in ser.holdings(state) if x["symbol"] == symbol), None) if h else None
        return out

    return svc.read(game_id, build)
