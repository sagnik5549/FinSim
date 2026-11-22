"""Accounts, sessions and per-player game ownership."""
import json
import time
import uuid

import pytest

from app.config import settings
from app.services import auth as auth_svc
from tests.conftest import signup


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_game_routes_require_login(client):
    assert client.post("/api/game/new", json={}).status_code == 401
    r = client.get("/api/game/state", headers={"X-Game-Id": "whatever", "Authorization": "Bearer nope.nope"})
    assert r.status_code == 401 and r.json()["detail"]["code"] == "UNAUTHORIZED"


def test_signup_login_and_me(client):
    email = f"{uuid.uuid4().hex[:8]}@Example.com"
    r = client.post("/api/auth/signup", json={"email": email, "password": "hunter2-hunter2", "name": "Asha"})
    assert r.status_code == 200, r.text
    user = r.json()["user"]
    assert user["email"] == email.lower() and user["name"] == "Asha" and user["latest_game_id"] is None

    dup = client.post("/api/auth/signup", json={"email": email.upper(), "password": "another-pass-1"})
    assert dup.status_code == 409 and dup.json()["detail"]["code"] == "EMAIL_TAKEN"

    bad = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert bad.status_code == 401 and bad.json()["detail"]["code"] == "BAD_CREDENTIALS"

    tok = client.post("/api/auth/login", json={"email": email, "password": "hunter2-hunter2"}).json()["token"]
    gid = client.post("/api/game/new", json={}, headers=bearer(tok)).json()["state"]["game_id"]
    me = client.get("/api/auth/me", headers=bearer(tok)).json()
    assert me["id"] == user["id"] and me["latest_game_id"] == gid


def test_short_password_rejected(client):
    r = client.post("/api/auth/signup", json={"email": "short@test.dev", "password": "1234567"})
    assert r.status_code == 422


def test_players_cannot_touch_each_others_games(client, game):
    _, headers, st = game
    intruder = bearer(signup(client)["token"])
    r = client.get("/api/game/state", headers={**intruder, "X-Game-Id": st["game_id"]})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "NO_GAME"
    save = client.post("/api/game/save", headers=headers, json={"name": "mine"}).json()
    r = client.post("/api/game/load", headers=intruder, json={"save_id": save["id"]})
    assert r.status_code == 404
    assert client.get("/api/game/saves", headers=intruder).json() == []


def test_tampered_or_expired_token_rejected(client):
    tok = signup(client)["token"]
    body, sig = tok.split(".")
    forged = auth_svc._b64(json.dumps({"sub": "x", "pid": "y", "exp": int(time.time()) + 999}).encode())
    assert client.get("/api/auth/me", headers=bearer(f"{forged}.{sig}")).status_code == 401
    payload = auth_svc.read_token(tok)
    acct = type("A", (), {"id": payload["sub"], "player_id": payload["pid"], "session_version": 0})()
    old = settings.AUTH_TOKEN_DAYS
    settings.AUTH_TOKEN_DAYS = -1
    try:
        expired = auth_svc.issue_token(acct)
    finally:
        settings.AUTH_TOKEN_DAYS = old
    assert client.get("/api/auth/me", headers=bearer(expired)).status_code == 401


def test_signup_adopts_guest_player(client):
    from app.services import game_service as svc
    guest = svc.new_game(seed=5)
    body = signup(client, guest_player_id=guest["player_id"])
    assert body["user"]["player_id"] == guest["player_id"]
    assert body["user"]["latest_game_id"] == guest["state"]["game_id"]
    # A second account can't claim the same guest player.
    assert signup(client, guest_player_id=guest["player_id"])["user"]["player_id"] != guest["player_id"]


def test_password_hashing():
    h = auth_svc.hash_password("s3cret-pass")
    assert h.startswith("scrypt$") and "s3cret" not in h
    assert auth_svc.verify_password("s3cret-pass", h)
    assert not auth_svc.verify_password("s3cret-pasS", h)


@pytest.fixture
def google(monkeypatch):
    """Pretend Google's tokeninfo endpoint accepted the credential with these claims."""
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-123.apps.googleusercontent.com")
    claims = {"aud": "client-123.apps.googleusercontent.com", "iss": "https://accounts.google.com",
              "exp": str(int(time.time()) + 600), "email_verified": "true"}

    def use(**c):
        full = {**claims, **c}
        monkeypatch.setattr(auth_svc, "verify_google", lambda cred: full)
        return full
    return use


def test_google_signin_creates_then_reuses_account(client, google):
    sub = uuid.uuid4().hex
    google(sub=sub, email=f"{sub[:8]}@gmail.com", name="Ravi K")
    first = client.post("/api/auth/google", json={"credential": "x" * 40}).json()
    again = client.post("/api/auth/google", json={"credential": "y" * 40}).json()
    assert first["user"]["id"] == again["user"]["id"] and first["user"]["has_google"]
    assert first["user"]["name"] == "Ravi K" and not first["user"]["has_password"]
    r = client.post("/api/auth/login", json={"email": f"{sub[:8]}@gmail.com", "password": "anything-at-all"})
    assert r.json()["detail"]["code"] == "USE_GOOGLE"


def test_google_links_existing_email_account(client, google):
    email = f"{uuid.uuid4().hex[:8]}@gmail.com"
    pw = client.post("/api/auth/signup", json={"email": email, "password": "password-123"}).json()["user"]
    google(sub=uuid.uuid4().hex, email=email)
    g = client.post("/api/auth/google", json={"credential": "z" * 40}).json()["user"]
    assert g["id"] == pw["id"] and g["has_google"] and g["has_password"]


def test_google_token_checks(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    with pytest.raises(auth_svc.AuthError) as e:
        auth_svc.verify_google("token")
    assert e.value.code == "GOOGLE_DISABLED"

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "mine")

    class Resp:
        def __init__(self, claims): self.claims = claims
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(self.claims).encode()

    base = {"aud": "mine", "iss": "accounts.google.com", "exp": str(int(time.time()) + 60),
            "email": "a@b.co", "email_verified": "true", "sub": "1"}
    for bad, code in [({"aud": "someone-else"}, "GOOGLE_INVALID"), ({"iss": "evil.com"}, "GOOGLE_INVALID"),
                      ({"email_verified": "false"}, "GOOGLE_UNVERIFIED")]:
        monkeypatch.setattr(auth_svc.urllib.request, "urlopen", lambda *a, c={**base, **bad}, **k: Resp(c))
        with pytest.raises(auth_svc.AuthError) as e:
            auth_svc.verify_google("token")
        assert e.value.code == code
    monkeypatch.setattr(auth_svc.urllib.request, "urlopen", lambda *a, **k: Resp(base))
    assert auth_svc.verify_google("token")["sub"] == "1"
