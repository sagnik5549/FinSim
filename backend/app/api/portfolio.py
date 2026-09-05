from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import game_service

router = APIRouter()


@router.get("/{game_id}")
def get_portfolio(game_id: str, db: Session = Depends(get_db)):
    try:
        from app.models.db_models import Game
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
        return game_service._build_state_response(game, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
