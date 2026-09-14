from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Game
from app.simulation.constants import CAREER_LEVELS, PAID_LEAVE_PER_YEAR, CAREER_DAYS
from app.simulation.career_engine import (
    CareerEngine,
    MIN_REPUTATION_FOR_REVIEW_PASS,
)


router = APIRouter()


def _get_level_data(level: int) -> dict:
    if not CAREER_LEVELS:
        return {}

    return CAREER_LEVELS.get(
        level,
        CAREER_LEVELS[min(CAREER_LEVELS.keys())],
    )


def _get_next_level(level: int):
    for career_level in sorted(CAREER_LEVELS.keys()):
        if career_level > level:
            return career_level

    return None


def _get_previous_level(level: int):
    for career_level in sorted(CAREER_LEVELS.keys(), reverse=True):
        if career_level < level:
            return career_level

    return None


def _get_role_title(level: int) -> str:
    try:
        return CareerEngine.get_role_title(level)
    except (KeyError, TypeError, ValueError):
        return "Unknown Role"


def _get_xp_progress(xp: int, xp_to_next: int) -> float:
    if xp_to_next <= 0:
        return 100.0

    return round(
        min(max((xp / xp_to_next) * 100.0, 0.0), 100.0),
        1,
    )


@router.get("/{game_id}")
def get_career(
    game_id: str,
    db: Session = Depends(get_db),
):
    # Read the authoritative career state from PostgreSQL.
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

    level = int(game.career_level or 1)
    level_data = _get_level_data(level)

    next_level = _get_next_level(level)
    previous_level = _get_previous_level(level)

    xp = int(game.xp or 0)
    xp_to_next = int(
        level_data.get("xp_to_next", 9999)
    )

    reputation = round(
        float(game.reputation or 0.0),
        1,
    )

    leave_used = int(game.leave_used or 0)
    leave_balance = int(game.leave_balance or 0)

    career_day = int(game.career_day or 1)
    quarter = int(game.quarter or 1)
    career_year = int(game.career_year or 1)

    return {
        "game_id": str(game.id),

        "career": {
            "level": level,
            "role": _get_role_title(level),

            "next_level": next_level,
            "next_role": (
                _get_role_title(next_level)
                if next_level is not None
                else None
            ),

            "previous_level": previous_level,
            "previous_role": (
                _get_role_title(previous_level)
                if previous_level is not None
                else None
            ),

            "is_max_level": next_level is None,

            "xp": xp,
            "xp_to_next_level": xp_to_next,
            "xp_progress": _get_xp_progress(
                xp,
                xp_to_next,
            ),

            "reputation": reputation,

            "career_day": career_day,
            "quarter": quarter,
            "career_year": career_year,
        },

        "promotion": {
            "target_required": float(
                level_data.get("target_return_pct", 12.0)
            ),
            "max_drawdown_allowed": float(
                level_data.get("max_drawdown_limit", 0.10) * 100
            ),
            "minimum_reputation": float(
                MIN_REPUTATION_FOR_REVIEW_PASS
            ),
            "can_be_promoted": next_level is not None,
        },

        "career_review": {
            "promotion": "PASS",
            "first_failure": "WARNING",
            "second_failure_level_2_plus": "DEMOTION",
            "second_failure_level_1": "LAYOFF",
        },

        "leave": {
            "annual_allowance": PAID_LEAVE_PER_YEAR,
            "used": leave_used,
            "remaining": leave_balance,
        },

        "status": {
            "career_active": career_day <= CAREER_DAYS,
            "can_be_promoted": next_level is not None,
            "can_be_demoted": previous_level is not None,
        },
    }