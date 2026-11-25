"""
Accounts and sessions — email/password and Google sign-in.

Sessions are stateless HMAC-signed bearer tokens (no session table), so any
serverless instance can verify them with only AUTH_SECRET. Passwords are hashed
with scrypt from the standard library; Google ID tokens are verified by Google's
tokeninfo endpoint, which checks the signature and expiry for us.

Each token carries the account's session_version; bumping it (password change or
reset, "sign out everywhere") invalidates every older token. Sign-in failures and
code emails are rate-limited through the rate_limits table, and one-time codes are
stored only as HMACs, expire after 10 minutes and allow 5 guesses.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, update

from app.config import settings
from app.database import models as m
from app.services import mailer
from app.services.game_service import session

_DEV_SECRET = "ibmode-insecure-dev-secret"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

# (attempts, window, lockout): reaching `attempts` within `window` blocks the key for `lockout`.
_LOGIN_EMAIL_LIMIT = (5, timedelta(minutes=15), timedelta(minutes=15))
_LOGIN_IP_LIMIT = (30, timedelta(minutes=15), timedelta(minutes=15))
_SEND_EMAIL_LIMIT = (5, timedelta(hours=1), timedelta(hours=1))
_SEND_IP_LIMIT = (20, timedelta(hours=1), timedelta(hours=1))
_RESEND_COOLDOWN = timedelta(seconds=60)
_CODE_TTL = timedelta(minutes=10)
_CODE_TRIES = 5


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
    payload = {"sub": account.id, "pid": account.player_id, "v": account.session_version or 0,
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


def authenticate(token: str) -> dict:
    """read_token plus a check that the session hasn't been revoked since the token was issued."""
    payload = read_token(token)
    with session() as db:
        version = db.execute(select(m.Account.session_version).where(m.Account.id == payload.get("sub"))).scalar()
    if version is None or version != payload.get("v", 0):
        raise AuthError(401, "UNAUTHORIZED", "You were signed out. Please sign in again.")
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


# ---------------------------------------------------------------- rules and limits
def check_password(password: str, email: str) -> None:
    if len(password) < 8:
        raise AuthError(422, "WEAK_PASSWORD", "Use at least 8 characters.")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        raise AuthError(422, "WEAK_PASSWORD", "Use at least one letter and one number.")
    if password.strip().lower() == email.lower():
        raise AuthError(422, "WEAK_PASSWORD", "Don't use your email address as your password.")


def _now() -> datetime:
    return datetime.utcnow()


def _wait(remaining: timedelta) -> str:
    mins = max(1, math.ceil(remaining.total_seconds() / 60))
    return f"Too many attempts. Try again in {mins} minute{'s' if mins > 1 else ''}."


def _check(db, key: str, now: datetime, message: Optional[str] = None) -> None:
    row = db.get(m.RateLimit, key)
    if row is not None and row.locked_until is not None and row.locked_until > now:
        raise AuthError(429, "TOO_MANY_ATTEMPTS", message or _wait(row.locked_until - now))


def _count(db, key: str, limit: tuple[int, timedelta, timedelta], now: datetime) -> None:
    attempts, window, lockout = limit
    row = db.get(m.RateLimit, key)
    if row is None:
        row = m.RateLimit(key=key, count=0, window_start=now)
        db.add(row)
    if now - row.window_start > window or (row.locked_until is not None and row.locked_until <= now):
        row.count, row.window_start, row.locked_until = 0, now, None
    row.count += 1
    if row.count >= attempts:
        row.locked_until = now + lockout


def _clear(db, key: str) -> None:
    row = db.get(m.RateLimit, key)
    if row is not None:
        db.delete(row)


def _code_hash(email: str, purpose: str, code: str) -> str:
    return hmac.new(_secret(), f"{purpose}:{email}:{code}".encode(), hashlib.sha256).hexdigest()


def _mask(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}{'•' * min(4, max(1, len(local) - 2))}@{domain}"


def _limit_sends(db, email: str, purpose: str, ip: str, now: datetime) -> None:
    """Cooldown and hourly caps on code emails, also applied to unknown emails so responses don't reveal accounts."""
    _check(db, f"cool:{purpose}:{email}", now, "Please wait a minute before requesting another code.")
    _check(db, f"send:{email}", now)
    _check(db, f"send-ip:{ip}", now)
    _count(db, f"send:{email}", _SEND_EMAIL_LIMIT, now)
    _count(db, f"send-ip:{ip}", _SEND_IP_LIMIT, now)
    _count(db, f"cool:{purpose}:{email}", (1, _RESEND_COOLDOWN, _RESEND_COOLDOWN), now)


def _send_code(db, *, email: str, purpose: str, account_id: str, ip: str) -> None:
    """Issue a fresh code (voiding earlier ones), email it, then commit; nothing is stored if sending fails."""
    now = _now()
    _limit_sends(db, email, purpose, ip, now)
    db.execute(update(m.EmailCode).where(m.EmailCode.email == email, m.EmailCode.purpose == purpose,
                                         m.EmailCode.used_at.is_(None)).values(used_at=now))
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(m.EmailCode(email=email, purpose=purpose, account_id=account_id, code_hash=_code_hash(email, purpose, code),
                       expires_at=now + _CODE_TTL, created_at=now))
    try:
        mailer.send_code(email, code, purpose, int(_CODE_TTL.total_seconds() // 60))
    except mailer.MailNotConfigured:
        raise AuthError(503, "EMAIL_NOT_CONFIGURED", "Email isn't set up on this server yet, so codes can't be sent.")
    except mailer.MailFailed:
        raise AuthError(502, "EMAIL_FAILED", "We couldn't send the email. Please try again in a minute.")
    db.commit()


def _use_code(db, *, email: str, purpose: str, code: str, account_id: str) -> None:
    now = _now()
    row = db.execute(select(m.EmailCode).where(
        m.EmailCode.email == email, m.EmailCode.purpose == purpose, m.EmailCode.account_id == account_id,
        m.EmailCode.used_at.is_(None), m.EmailCode.expires_at > now,
    ).order_by(m.EmailCode.created_at.desc()).limit(1)).scalar()
    if row is None:
        raise AuthError(400, "CODE_INVALID", "This code has expired or was replaced. Request a new one.")
    if not hmac.compare_digest(row.code_hash, _code_hash(email, purpose, code.strip())):
        row.attempts += 1
        left = _CODE_TRIES - row.attempts
        if left <= 0:
            row.used_at = now
        db.commit()
        raise AuthError(400, "CODE_INVALID", f"Incorrect code. {left} attempt{'s' if left != 1 else ''} left."
                        if left > 0 else "Incorrect code. Request a new one.")
    row.used_at = now


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
    check_password(password, email)
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


def login(email: str, password: str, ip: str) -> dict:
    email, now = email.strip().lower(), _now()
    with session() as db:
        _check(db, f"login:{email}", now)
        _check(db, f"login-ip:{ip}", now)
        account = db.execute(select(m.Account).where(m.Account.email == email)).scalar()
        if account is None or account.password_hash is None or not verify_password(password, account.password_hash):
            _count(db, f"login:{email}", _LOGIN_EMAIL_LIMIT, now)
            _count(db, f"login-ip:{ip}", _LOGIN_IP_LIMIT, now)
            db.commit()
            if account is not None and account.password_hash is None:
                raise AuthError(401, "USE_GOOGLE", "This account uses Google sign-in. Use “Continue with Google”, "
                                                   "or “Forgot password?” to add a password.")
            raise AuthError(401, "BAD_CREDENTIALS", "Incorrect email or password.")
        _clear(db, f"login:{email}")
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


def _account(db, account_id: str) -> m.Account:
    account = db.get(m.Account, account_id)
    if account is None:
        raise AuthError(401, "UNAUTHORIZED", "This account no longer exists.")
    return account


def _email_free(db, email: str, account_id: str) -> None:
    other = db.execute(select(m.Account.id).where(m.Account.email == email, m.Account.id != account_id)).first()
    if other is not None:
        raise AuthError(409, "EMAIL_TAKEN", "Another account already uses this email.")


def _set_password(db, account: m.Account, password: str) -> None:
    account.password_hash = hash_password(password)
    account.session_version = (account.session_version or 0) + 1  # sign out every other device
    _clear(db, f"login:{account.email}")


# ---------------------------------------------------------------- password reset
def forgot_password(email: str, ip: str) -> dict:
    email = _normalise_email(email)
    with session() as db:
        account = db.execute(select(m.Account).where(m.Account.email == email)).scalar()
        if account is None:
            # Same limits and the same answer as for a real account, so this can't be used to find accounts.
            _limit_sends(db, email, "reset", ip, _now())
            db.commit()
        else:
            _send_code(db, email=email, purpose="reset", account_id=account.id, ip=ip)
    return {"sent_to": _mask(email)}


def reset_password(email: str, code: str, password: str) -> dict:
    email = _normalise_email(email)
    check_password(password, email)
    with session() as db:
        account = db.execute(select(m.Account).where(m.Account.email == email)).scalar()
        if account is None:
            raise AuthError(400, "CODE_INVALID", "This code has expired or was replaced. Request a new one.")
        _use_code(db, email=email, purpose="reset", code=code, account_id=account.id)
        _set_password(db, account, password)
        return _respond(db, account)


# ---------------------------------------------------------------- signed-in account changes
def request_code(account_id: str, purpose: str, new_email: Optional[str], ip: str) -> dict:
    with session() as db:
        account = _account(db, account_id)
        if purpose == "change_email":
            target = _normalise_email(new_email or "")
            if target == account.email:
                raise AuthError(422, "SAME_EMAIL", "That's already your email address.")
            _email_free(db, target, account.id)
        else:
            target = account.email
        _send_code(db, email=target, purpose=purpose, account_id=account.id, ip=ip)
    return {"sent_to": _mask(target)}


def change_email(account_id: str, new_email: str, code: str) -> dict:
    new_email = _normalise_email(new_email)
    with session() as db:
        account = _account(db, account_id)
        _use_code(db, email=new_email, purpose="change_email", code=code, account_id=account.id)
        _email_free(db, new_email, account.id)
        old_email, account.email = account.email, new_email
        db.commit()
        user = _user(db, account)
    mailer.send_notice(old_email, "Your Apex Capital email was changed",
                       f"The email on your Apex Capital account was changed to {_mask(new_email)}.\n"
                       "If this wasn't you, reset your password from the sign-in page right away.")
    return user


def change_password(account_id: str, code: str, password: str) -> dict:
    with session() as db:
        account = _account(db, account_id)
        check_password(password, account.email)
        _use_code(db, email=account.email, purpose="change_password", code=code, account_id=account.id)
        _set_password(db, account, password)
        return _respond(db, account)


def update_profile(account_id: str, name: str) -> dict:
    name = name.strip()
    if not name:
        raise AuthError(422, "INVALID_NAME", "Enter a name.")
    with session() as db:
        account = _account(db, account_id)
        account.name = name[:80]
        db.commit()
        return _user(db, account)


def sign_out_everywhere(account_id: str) -> dict:
    """Revoke every session, then hand this device a fresh token."""
    with session() as db:
        account = _account(db, account_id)
        account.session_version = (account.session_version or 0) + 1
        return _respond(db, account)
