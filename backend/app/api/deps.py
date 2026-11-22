from fastapi import Depends, Header, HTTPException

from app.services import auth
from app.services import game_service as svc


def current_account(authorization: str | None = Header(default=None)) -> dict:
    """Token payload of the signed-in user: {"sub": account_id, "pid": player_id, "exp": ...}."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Please sign in."})
    return auth.read_token(authorization[7:].strip())


def current_player(account: dict = Depends(current_account)) -> str:
    return account["pid"]


def game_id_header(x_game_id: str | None = Header(default=None), player_id: str = Depends(current_player)) -> str:
    if not x_game_id:
        raise HTTPException(status_code=404, detail={"code": "NO_GAME", "message": "No active game. Start a new career."})
    # Someone else's game id is reported as missing rather than forbidden, so ids can't be probed.
    if svc.owner_of(x_game_id) != player_id:
        raise svc.NotFound(x_game_id)
    return x_game_id
