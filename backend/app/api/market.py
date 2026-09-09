from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Game, Stock
from app.schemas.game_schemas import StockCandlesResponse
from app.services import game_service


router = APIRouter()


@router.get("/{game_id}")
def get_market(
    game_id: str,
    db: Session = Depends(get_db),
):
    # Read the authoritative market state from PostgreSQL.
    game = (
        db.query(Game)
        .filter(Game.id == game_id)
        .first()
    )

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found.",
        )

    stocks = (
        db.query(Stock)
        .filter(Stock.game_id == game_id)
        .order_by(Stock.symbol)
        .all()
    )

    return {
        "game_id": str(game.id),
        "regime": game.market_regime,
        "stocks": [
            {
                "symbol": stock.symbol,
                "name": stock.name,
                "sector": stock.sector,
                "current_price": float(stock.current_price),
                "previous_price": float(stock.previous_price),
                "daily_return": round(
                    (
                        stock.current_price / stock.daily_open - 1
                    ) * 100,
                    4,
                )
                if stock.daily_open
                else 0.0,
                "daily_high": float(stock.daily_high),
                "daily_low": float(stock.daily_low),
                "volume": int(stock.volume),
                "volatility": float(stock.volatility),
                "beta": float(stock.beta),
                "sentiment": float(stock.sentiment),
                "growth": float(stock.growth),
                "profitability": float(stock.profitability),
                "debt": float(stock.debt),
                "valuation": float(stock.valuation),
            }
            for stock in stocks
        ],
    }


@router.get(
    "/{game_id}/{symbol}/candles",
    response_model=StockCandlesResponse,
)
def get_candles(
    game_id: str,
    symbol: str,
    days: int = Query(
        default=30,
        ge=1,
        le=90,
    ),
    db: Session = Depends(get_db),
):
    game = (
        db.query(Game)
        .filter(Game.id == game_id)
        .first()
    )

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found.",
        )

    stock = (
        db.query(Stock)
        .filter(
            Stock.game_id == game_id,
            Stock.symbol == symbol.upper(),
        )
        .first()
    )

    if stock is None:
        raise HTTPException(
            status_code=404,
            detail=f"Stock '{symbol.upper()}' not found.",
        )

    try:
        return game_service.get_stock_candles(
            game_id,
            stock.symbol,
            days,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc