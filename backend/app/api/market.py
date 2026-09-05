from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.game_schemas import StockCandlesResponse
from app.services import game_service
from app.models.db_models import Stock, Game

router = APIRouter()


@router.get("/{game_id}")
def get_market(game_id: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    stocks = db.query(Stock).filter(Stock.game_id == game_id).all()
    return {
        "regime": game.market_regime,
        "stocks": [
            {
                "symbol": s.symbol, "name": s.name, "sector": s.sector,
                "current_price": s.current_price, "previous_price": s.previous_price,
                "daily_return": round((s.current_price / s.daily_open - 1) * 100, 4) if s.daily_open else 0.0,
                "daily_high": s.daily_high, "daily_low": s.daily_low,
                "volume": s.volume, "volatility": s.volatility,
                "beta": s.beta, "sentiment": s.sentiment,
                "growth": s.growth, "profitability": s.profitability,
                "debt": s.debt, "valuation": s.valuation,
            }
            for s in stocks
        ],
    }


@router.get("/{game_id}/{symbol}/candles", response_model=StockCandlesResponse)
def get_candles(game_id: str, symbol: str, days: int = Query(default=30, ge=1, le=90), db: Session = Depends(get_db)):
    try:
        return game_service.get_stock_candles(game_id, symbol.upper(), days, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
