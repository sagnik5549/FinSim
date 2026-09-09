from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Game
from app.schemas.game_schemas import (
    AdvanceHoursRequest,
    GameStateResponse,
    LeaveRequest,
    NewGameRequest,
    NewGameResponse,
    QuarterlyReviewResponse,
)
from app.services import game_service
from app.simulation.constants import MARKET_CLOSE_HOUR


router = APIRouter()


@router.post("/new", response_model=NewGameResponse)
def new_game(
    req: NewGameRequest,
    db: Session = Depends(get_db),
):
    player_name = req.player_name.strip() or "Player"

    game_id = game_service.create_new_game(
        player_name,
        db,
    )

    return NewGameResponse(
        game_id=game_id,
        message="New career started. Welcome to Apex Capital.",
    )


@router.get(
    "/state/{game_id}",
    response_model=GameStateResponse,
)
def get_state(
    game_id: str,
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

    try:
        return game_service.build_state_response(
            game,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/advance-hour",
    response_model=GameStateResponse,
)
def advance_hour(
    req: AdvanceHoursRequest,
    db: Session = Depends(get_db),
):
    try:
        return game_service.advance_game_time(
            req.game_id,
            1,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/advance-hours",
    response_model=GameStateResponse,
)
def advance_hours(
    req: AdvanceHoursRequest,
    db: Session = Depends(get_db),
):
    if req.hours <= 0:
        raise HTTPException(
            status_code=400,
            detail="Hours must be greater than zero.",
        )

    try:
        return game_service.advance_game_time(
            req.game_id,
            req.hours,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/advance-to-close",
    response_model=GameStateResponse,
)
def advance_to_close(
    req: AdvanceHoursRequest,
    db: Session = Depends(get_db),
):
    game = (
        db.query(Game)
        .filter(Game.id == req.game_id)
        .first()
    )

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found.",
        )

    hours_to_close = max(
        1,
        MARKET_CLOSE_HOUR - game.game_hour,
    )

    try:
        return game_service.advance_game_time(
            req.game_id,
            hours_to_close,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/advance-next-business-day",
    response_model=GameStateResponse,
)
def advance_next_business_day(
    req: AdvanceHoursRequest,
    db: Session = Depends(get_db),
):
    game = (
        db.query(Game)
        .filter(Game.id == req.game_id)
        .first()
    )

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found.",
        )

    hours_to_advance = (
        MARKET_CLOSE_HOUR - game.game_hour + 1
    )

    try:
        return game_service.advance_game_time(
            req.game_id,
            hours_to_advance,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/skip-weekend",
    response_model=GameStateResponse,
)
def skip_weekend(
    req: AdvanceHoursRequest,
    db: Session = Depends(get_db),
):
    game = (
        db.query(Game)
        .filter(Game.id == req.game_id)
        .first()
    )

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found.",
        )

    try:
        return game_service.skip_weekend(
            req.game_id,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/quarterly-review",
    response_model=QuarterlyReviewResponse,
)
def quarterly_review(
    req: AdvanceHoursRequest,
    db: Session = Depends(get_db),
):
    try:
        return game_service.do_quarterly_review(
            req.game_id,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/list")
def list_games(
    db: Session = Depends(get_db),
):
    games = (
        db.query(Game)
        .order_by(Game.created_at.desc())
        .limit(10)
        .all()
    )

    return [
        {
            "id": str(game.id),
            "player_name": game.player_name,
            "status": game.status,
            "career_day": game.career_day,
            "created_at": (
                game.created_at.isoformat()
                if game.created_at
                else None
            ),
        }
        for game in games
    ]