from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Game
from app.services import game_service


router = APIRouter()


@router.get("/{game_id}")
def get_portfolio(
    game_id: str,
    db: Session = Depends(get_db),
):
    # Verify the career exists in PostgreSQL.
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

    try:
        return game_service.build_state_response(
            game,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc