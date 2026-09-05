from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Game
from app.simulation.constants import CAREER_LEVELS
from app.simulation.career_engine import CareerEngine

router = APIRouter()


@router.get("/{game_id}")
def get_career(game_id: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    lvl = game.career_level
    lvl_data = CAREER_LEVELS.get(lvl, CAREER_LEVELS[1])
    return {
        "level": lvl,
        "role": CareerEngine.get_role_title(lvl),
        "xp": game.xp,
        "xp_to_next_level": lvl_data.get("xp_to_next", 9999),
        "reputation": round(game.reputation, 1),
        "leave_balance": game.leave_balance,
        "leave_used": game.leave_used,
        "career_day": game.career_day,
        "quarter": game.quarter,
        "career_year": game.career_year,
        "promotion_requirements": {
            "return_target": 12.0,
            "max_drawdown": 10.0,
            "min_reputation": 75.0,
        },
    }
