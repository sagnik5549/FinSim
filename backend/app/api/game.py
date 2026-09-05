from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.game_schemas import (
    NewGameRequest, NewGameResponse, GameStateResponse,
    AdvanceHoursRequest, LeaveRequest, QuarterlyReviewResponse,
)
from app.services import game_service

router = APIRouter()


@router.post("/new", response_model=NewGameResponse)
def new_game(req: NewGameRequest, db: Session = Depends(get_db)):
    player_name = req.player_name.strip() or "Player"
    game_id = game_service.create_new_game(player_name, db)
    return NewGameResponse(game_id=game_id, message="New career started. Welcome to Apex Capital.")


@router.get("/state/{game_id}", response_model=GameStateResponse)
def get_state(game_id: str, db: Session = Depends(get_db)):
    try:
        game = db.query(__import__("app.models.db_models", fromlist=["Game"]).Game).filter_by(id=game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
        return game_service._build_state_response(game, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/advance-hour", response_model=GameStateResponse)
def advance_hour(req: AdvanceHoursRequest, db: Session = Depends(get_db)):
    try:
        return game_service.advance_game_time(req.game_id, 1, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/advance-hours", response_model=GameStateResponse)
def advance_hours(req: AdvanceHoursRequest, db: Session = Depends(get_db)):
    try:
        return game_service.advance_game_time(req.game_id, req.hours, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/advance-to-close", response_model=GameStateResponse)
def advance_to_close(req: AdvanceHoursRequest, db: Session = Depends(get_db)):
    try:
        from app.simulation.constants import MARKET_CLOSE_HOUR
        from app.models.db_models import Game
        game = db.query(Game).filter(Game.id == req.game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
        hours_left = max(1, MARKET_CLOSE_HOUR - game.game_hour)
        return game_service.advance_game_time(req.game_id, hours_left, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/advance-next-business-day", response_model=GameStateResponse)
def advance_next_day(req: AdvanceHoursRequest, db: Session = Depends(get_db)):
    try:
        from app.simulation.constants import MARKET_CLOSE_HOUR
        from app.models.db_models import Game
        game = db.query(Game).filter(Game.id == req.game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
        hours_to_advance = MARKET_CLOSE_HOUR - game.game_hour + 1  # close today + open next day
        return game_service.advance_game_time(req.game_id, hours_to_advance, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/skip-weekend", response_model=GameStateResponse)
def skip_weekend(req: AdvanceHoursRequest, db: Session = Depends(get_db)):
    try:
        from app.models.db_models import Game
        from app.simulation.constants import MARKET_CLOSE_HOUR
        game = db.query(Game).filter(Game.id == req.game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
        # Advance enough to get past the weekend
        return game_service.advance_game_time(req.game_id, MARKET_CLOSE_HOUR - game.game_hour + 24, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quarterly-review", response_model=QuarterlyReviewResponse)
def quarterly_review(req: AdvanceHoursRequest, db: Session = Depends(get_db)):
    try:
        return game_service.do_quarterly_review(req.game_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
def list_games(db: Session = Depends(get_db)):
    from app.models.db_models import Game
    games = db.query(Game).order_by(Game.created_at.desc()).limit(10).all()
    return [{"id": str(g.id), "player_name": g.player_name, "status": g.status,
             "career_day": g.career_day, "created_at": g.created_at.isoformat()} for g in games]
