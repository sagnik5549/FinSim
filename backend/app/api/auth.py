from fastapi import APIRouter, Depends, Request

from app.api.deps import current_account
from app.config import settings
from app.schemas.requests import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    CodeRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    ProfileRequest,
    ResetPasswordRequest,
    SignupRequest,
)
from app.services import auth

router = APIRouter()


def client_ip(request: Request) -> str:
    # Vercel sets X-Forwarded-For to the real client address.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


@router.get("/config")
def config():
    return {"google_client_id": settings.GOOGLE_CLIENT_ID or None}


@router.post("/signup")
def signup(req: SignupRequest):
    return auth.signup(req.email, req.password, req.name, req.guest_player_id)


@router.post("/login")
def login(req: LoginRequest, request: Request):
    return auth.login(req.email, req.password, client_ip(request))


@router.post("/google")
def google(req: GoogleLoginRequest):
    return auth.google_login(req.credential, req.guest_player_id)


@router.get("/me")
def me(account: dict = Depends(current_account)):
    return auth.me(account["sub"])


# ---------------------------------------------------------------- password reset (signed out)
@router.post("/password/forgot")
def forgot_password(req: ForgotPasswordRequest, request: Request):
    return auth.forgot_password(req.email, client_ip(request))


@router.post("/password/reset")
def reset_password(req: ResetPasswordRequest):
    return auth.reset_password(req.email, req.code, req.new_password)


# ---------------------------------------------------------------- account settings (signed in)
@router.post("/code")
def request_code(req: CodeRequest, request: Request, account: dict = Depends(current_account)):
    return auth.request_code(account["sub"], req.purpose, req.new_email, client_ip(request))


@router.post("/email")
def change_email(req: ChangeEmailRequest, account: dict = Depends(current_account)):
    return auth.change_email(account["sub"], req.new_email, req.code)


@router.post("/password")
def change_password(req: ChangePasswordRequest, account: dict = Depends(current_account)):
    return auth.change_password(account["sub"], req.code, req.new_password)


@router.post("/profile")
def update_profile(req: ProfileRequest, account: dict = Depends(current_account)):
    return auth.update_profile(account["sub"], req.name)


@router.post("/sign-out-everywhere")
def sign_out_everywhere(account: dict = Depends(current_account)):
    return auth.sign_out_everywhere(account["sub"])
