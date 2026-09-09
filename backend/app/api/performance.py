from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.game_schemas import PerformanceData
from app.services import game_service


router = APIRouter()


@router.get(
    "/{game_id}",
    response_model=PerformanceData,
)
def get_performance(
    game_id: str,
    db: Session = Depends(get_db),
):
    try:
        return game_service.get_performance(
            game_id,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc