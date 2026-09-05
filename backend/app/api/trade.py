from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.game_schemas import BuyRequest, SellRequest, TradeResult
from app.services import game_service

router = APIRouter()


@router.post("/buy", response_model=TradeResult)
def buy(req: BuyRequest, db: Session = Depends(get_db)):
    result = game_service.execute_buy(req.game_id, req.symbol.upper(), req.quantity, db)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.post("/sell", response_model=TradeResult)
def sell(req: SellRequest, db: Session = Depends(get_db)):
    result = game_service.execute_sell(req.game_id, req.symbol.upper(), req.quantity, db)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result
