"""
Accounts and sessions — email/password and Google sign-in.

Sessions are stateless HMAC-signed bearer tokens (no session table), so any
serverless instance can verify them with only AUTH_SECRET. Passwords are hashed
with scrypt from the standard library; Google ID tokens are verified by Google's
tokeninfo endpoint, which checks the signature and expiry for us.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select

from app.config import settings
from app.database import models as m
from app.services.game_service import session

_DEV_SECRET = "ibmode-insecure-dev-secret"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class AuthError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), dklen=32, **_SCRYPT)
    return hmac.compare_digest(calc.hex(), digest)


# ---------------------------------------------------------------- tokens
def _secret() -> bytes:
    if settings.AUTH_SECRET:
        return settings.AUTH_SECRET.encode()
    if settings.DATABASE_URL.startswith("sqlite"):
        return _DEV_SECRET.encode()
    # A hosted database URL carries its password, and anyone holding it already controls every account,
    # so it is an acceptable fallback key. Rotating the database password signs everyone out.
    return hashlib.sha256(b"ibmode-auth:" + settings.DATABASE_URL.encode()).digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(account: m.Account) -> str:
    payload = {"sub": account.id, "pid": account.player_id,
               "exp": int(time.time()) + settings.AUTH_TOKEN_DAYS * 86400}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(token: str) -> dict:
    """Return the token payload ({sub, pid, exp}) or raise AuthError."""
    try:
        body, sig = token.split(".")
        expected = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(body))
    except AuthError:
        raise
    except Exception:
        raise AuthError(401, "UNAUTHORIZED", "Your session is invalid. Please sign in again.")
    if payload.get("exp", 0) < time.time():
        raise AuthError(401, "UNAUTHORIZED", "Your session has expired. Please sign in again.")
    return payload


# ---------------------------------------------------------------- google
def verify_google(credential: str) -> dict:
    """Validate a Google Identity Services ID token; returns its claims."""
    if not settings.GOOGLE_CLIENT_ID:
        raise AuthError(503, "GOOGLE_DISABLED", "Google sign-in is not configured on this server.")
    url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode({"id_token": credential})
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            claims = json.loads(r.read())
    except urllib.error.HTTPError:
        raise AuthError(401, "GOOGLE_INVALID", "Google could not verify this sign-in. Please try again.")
    except Exception:
        raise AuthError(502, "GOOGLE_UNREACHABLE", "Could not reach Google to verify the sign-in.")
    if (claims.get("aud") != settings.GOOGLE_CLIENT_ID or claims.get("iss") not in _GOOGLE_ISSUERS
            or int(claims.get("exp", 0)) < time.time()):
        raise AuthError(401, "GOOGLE_INVALID", "This Google sign-in was not issued for this app.")
    if str(claims.get("email_verified")).lower() != "true" or not claims.get("email"):
        raise AuthError(401, "GOOGLE_UNVERIFIED", "Your Google account email is not verified.")
    return claims


# ---------------------------------------------------------------- accounts
def _normalise_email(email: str) -> str:
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise AuthError(422, "INVALID_EMAIL", "Enter a valid email address.")
    return email


def _player_for_new_account(db, guest_player_id: Optional[str], name: str) -> str:
    """Adopt the browser's guest player (keeping its games and saves) unless another account owns it."""
    if guest_player_id and db.get(m.Player, guest_player_id) is not None:
        owned = db.execute(select(m.Account.id).where(m.Account.player_id == guest_player_id)).first()
        if owned is None:
            return guest_player_id
    player_id = uuid.uuid4().hex[:16]
    db.add(m.Player(id=player_id, name=name[:80]))
    db.flush()
    return player_id


def _respond(db, account: m.Account) -> dict:
    account.last_login_at = datetime.utcnow()
    db.commit()
    return {"token": issue_token(account), "user": _user(db, account)}


def _user(db, account: m.Account) -> dict:
    latest = db.execute(select(m.Game.id).where(m.Game.player_id == account.player_id)
                        .order_by(m.Game.updated_at.desc()).limit(1)).scalar()
    return {"id": account.id, "email": account.email, "name": account.name, "player_id": account.player_id,
            "has_password": account.password_hash is not None, "has_google": account.google_sub is not None,
            "latest_game_id": latest}


def signup(email: str, password: str, name: str, guest_player_id: Optional[str]) -> dict:
    email = _normalise_email(email)
    name = name.strip() or email.split("@")[0]
    with session() as db:
        existing = db.execute(select(m.Account).where(m.Account.email == email)).scalar()
        if existing is not None:
            hint = " Use “Continue with Google”." if existing.password_hash is None else " Sign in instead."
            raise AuthError(409, "EMAIL_TAKEN", "An account with this email already exists." + hint)
        player_id = _player_for_new_account(db, guest_player_id, name)
        account = m.Account(id=uuid.uuid4().hex[:16], player_id=player_id, email=email, name=name[:80],
                            password_hash=hash_password(password))
        db.add(account)
        return _respond(db, account)


def login(email: str, password: str) -> dict:
    with session() as db:
        account = db.execute(select(m.Account).where(m.Account.email == email.strip().lower())).scalar()
        if account is None or account.password_hash is None or not verify_password(password, account.password_hash):
            if account is not None and account.password_hash is None:
                raise AuthError(401, "USE_GOOGLE", "This account uses Google sign-in. Use “Continue with Google”.")
            raise AuthError(401, "BAD_CREDENTIALS", "Incorrect email or password.")
        return _respond(db, account)


def google_login(credential: str, guest_player_id: Optional[str]) -> dict:
    claims = verify_google(credential)
    email, sub = claims["email"].lower(), claims["sub"]
    with session() as db:
        account = db.execute(select(m.Account).where(m.Account.google_sub == sub)).scalar()
        if account is None:
            # Google has verified the address, so it is safe to link an existing email/password account.
            account = db.execute(select(m.Account).where(func.lower(m.Account.email) == email)).scalar()
            if account is not None:
                account.google_sub = sub
        if account is None:
            name = (claims.get("name") or email.split("@")[0])[:80]
            player_id = _player_for_new_account(db, guest_player_id, name)
            account = m.Account(id=uuid.uuid4().hex[:16], player_id=player_id, email=email, name=name,
                                google_sub=sub)
            db.add(account)
        return _respond(db, account)


def me(account_id: str) -> dict:
    with session() as db:
        account = db.get(m.Account, account_id)
        if account is None:
            raise AuthError(401, "UNAUTHORIZED", "This account no longer exists.")
        return _user(db, account)
