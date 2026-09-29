from fastapi import Header, HTTPException


def game_id_header(x_game_id: str | None = Header(default=None)) -> str:
    if not x_game_id:
        raise HTTPException(status_code=404, detail={"code": "NO_GAME", "message": "No active game. Start a new career."})
    return x_game_id
