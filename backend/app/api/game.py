from fastapi import APIRouter, Depends

from app.api.deps import game_id_header
from app.schemas.requests import AckRequest, AdvanceHoursRequest, LoadRequest, NewGameRequest, ReadRequest, SaveRequest
from app.services import game_service as svc
from app.services import serializers as ser

router = APIRouter()


@router.post("/new")
def new_game(req: NewGameRequest):
    return svc.new_game(req.player_name, req.seed, req.player_id)


@router.get("/state")
def get_state(game_id: str = Depends(game_id_header)):
    return svc.read(game_id, ser.full_state)


@router.post("/advance-hour")
def advance_hour(game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.advance("hour"))


@router.post("/advance-hours")
def advance_hours(req: AdvanceHoursRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.advance("hours", req.hours))


@router.post("/advance-to-close")
def advance_to_close(game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.advance("close"))


@router.post("/advance-next-business-day")
def advance_next_business_day(game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.advance("next_day"))


@router.post("/skip-weekend")
def skip_weekend(game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.advance("weekend"))


@router.post("/advance-week")
def advance_week(game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.advance("week"))


@router.post("/popup/ack")
def ack_popup(req: AckRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.ack_popup(req.popup_id))


@router.post("/read")
def mark_read(req: ReadRequest, game_id: str = Depends(game_id_header)):
    return svc.act(game_id, lambda e: e.mark_read(req.kind, req.ids))


@router.post("/save")
def save_game(req: SaveRequest, game_id: str = Depends(game_id_header)):
    return svc.save_slot(game_id, req.name)


@router.get("/saves")
def list_saves(game_id: str = Depends(game_id_header)):
    return svc.list_saves(svc.player_of(game_id))


@router.post("/load")
def load_game(req: LoadRequest, game_id: str = Depends(game_id_header)):
    return svc.load_slot(req.save_id, svc.player_of(game_id))


@router.post("/restart")
def restart(game_id: str = Depends(game_id_header)):
    return svc.new_game(player_id=svc.player_of(game_id))
