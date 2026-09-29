from typing import Literal

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


@router.get("/{symbol}")
def stock_detail(symbol: str, tf: Literal["1h", "1d"] = Query("1h"), limit: int = Query(240, ge=20, le=2000),
                 game_id: str = Depends(game_id_header)):
    symbol = symbol.upper()

    def build(state):
        is_index = symbol in state.indices
        if symbol not in state.stocks and not is_index:
            raise HTTPException(status_code=404, detail={"code": "INVALID_SYMBOL", "message": f"Unknown symbol {symbol}"})
        with svc.session() as db:
            rows = [{"t": r.t.isoformat(), "o": r.o, "h": r.h, "l": r.l, "c": r.c, "v": r.v}
                    for r in repo.candles(db, game_id, symbol, limit=4000 if tf == "1d" else limit + 60)]
        if tf == "1d":
            rows = indicators.aggregate_daily(rows)
        ind = indicators.compute(rows)
        rows, ind = rows[-limit:], {k: v[-limit:] for k, v in ind.items()}
        out = {"symbol": symbol, "tf": tf, "candles": rows, "indicators": ind}
        if is_index:
            i = state.indices[symbol]
            out["index"] = {"key": i.key, "name": i.name, "value": i.value,
                            "change_pct": i.value / i.prev_close - 1 if i.prev_close else 0}
            return out
        s = state.stocks[symbol]
        out["stock"] = ser.stock_row(state, s)
        out["fundamentals"] = ser.fundamentals(s)
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
