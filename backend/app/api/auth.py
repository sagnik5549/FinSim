from fastapi import APIRouter, Depends

from app.api.deps import current_account
from app.config import settings
from app.schemas.requests import GoogleLoginRequest, LoginRequest, SignupRequest
from app.services import auth

router = APIRouter()


@router.get("/config")
def config():
    return {"google_client_id": settings.GOOGLE_CLIENT_ID or None}


@router.post("/signup")
def signup(req: SignupRequest):
    return auth.signup(req.email, req.password, req.name, req.guest_player_id)


@router.post("/login")
def login(req: LoginRequest):
    return auth.login(req.email, req.password)


@router.post("/google")
def google(req: GoogleLoginRequest):
    return auth.google_login(req.credential, req.guest_player_id)


@router.get("/me")
def me(account: dict = Depends(current_account)):
    return auth.me(account["sub"])
