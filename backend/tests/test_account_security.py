"""Password reset, email-code account changes, session revocation and rate limits."""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, inspect, text

from app.database import models as m
from app.database import session as db_session
from app.services import auth as auth_svc
from app.services import mailer
from app.services.game_service import session
from tests.conftest import signup

PW = "start-pass-1"


@pytest.fixture
def outbox(monkeypatch):
    """Capture codes instead of emailing them: list of (to, code, purpose)."""
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mailer, "send_code", lambda to, code, purpose, minutes: sent.append((to, code, purpose)))
    monkeypatch.setattr(mailer, "send_notice", lambda to, subject, body: sent.append((to, subject, "notice")))
    return sent


def new_user(client, ip=None):
    email = f"{uuid.uuid4().hex[:10]}@test.dev"
    r = client.post("/api/auth/signup", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    return email, {"Authorization": f"Bearer {r.json()['token']}"}


def reset_cooldown(email: str, purpose: str):
    """Skip the 60 s resend wait in tests."""
    with session() as db:
        row = db.get(m.RateLimit, f"cool:{purpose}:{email}")
        if row:
            db.delete(row)
            db.commit()


def test_password_rules(client):
    for pw, msg in [("short1", "8 characters"), ("onlyletters", "letter and one number"), ("12345678", "letter")]:
        r = client.post("/api/auth/signup", json={"email": f"{uuid.uuid4().hex[:8]}@t.dev", "password": pw})
        assert r.status_code == 422, pw
    email = f"{uuid.uuid4().hex[:6]}1@t.dev"
    r = client.post("/api/auth/signup", json={"email": email, "password": email})
    assert r.json()["detail"]["code"] == "WEAK_PASSWORD"


def test_forgot_and_reset_password(client, outbox):
    email, old = new_user(client)
    r = client.post("/api/auth/password/forgot", json={"email": email.upper()})
    assert r.status_code == 200 and r.json()["sent_to"].endswith("@test.dev")
    to, code, purpose = outbox[-1]
    assert (to, purpose) == (email, "reset") and len(code) == 6

    bad = client.post("/api/auth/password/reset", json={"email": email, "code": "000000" if code != "000000" else "111111",
                                                        "new_password": "new-pass-22"})
    assert bad.status_code == 400 and "4 attempts left" in bad.json()["detail"]["message"]

    r = client.post("/api/auth/password/reset", json={"email": email, "code": code, "new_password": "new-pass-22"})
    assert r.status_code == 200, r.text
    assert client.get("/api/auth/me", headers=old).status_code == 401  # other sessions signed out
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": PW}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "new-pass-22"}).status_code == 200
    # A code works once.
    again = client.post("/api/auth/password/reset", json={"email": email, "code": code, "new_password": "other-pass-3"})
    assert again.json()["detail"]["code"] == "CODE_INVALID"


def test_forgot_unknown_email_looks_the_same(client, outbox):
    r = client.post("/api/auth/password/forgot", json={"email": f"nobody{uuid.uuid4().hex[:6]}@test.dev"})
    assert r.status_code == 200 and "sent_to" in r.json()
    assert outbox == []


def test_code_cooldown_and_hourly_cap(client, outbox):
    email, _ = new_user(client)
    assert client.post("/api/auth/password/forgot", json={"email": email}).status_code == 200
    r = client.post("/api/auth/password/forgot", json={"email": email})
    assert r.status_code == 429 and "wait a minute" in r.json()["detail"]["message"]
    for _ in range(4):
        reset_cooldown(email, "reset")
        assert client.post("/api/auth/password/forgot", json={"email": email}).status_code == 200
    reset_cooldown(email, "reset")
    r = client.post("/api/auth/password/forgot", json={"email": email})
    assert r.status_code == 429 and r.json()["detail"]["code"] == "TOO_MANY_ATTEMPTS"
    assert len(outbox) == 5


def test_new_code_replaces_old_and_tries_run_out(client, outbox):
    email, _ = new_user(client)
    client.post("/api/auth/password/forgot", json={"email": email})
    first = outbox[-1][1]
    reset_cooldown(email, "reset")
    client.post("/api/auth/password/forgot", json={"email": email})
    second = outbox[-1][1]
    if first != second:
        r = client.post("/api/auth/password/reset", json={"email": email, "code": first, "new_password": "new-pass-22"})
        assert r.status_code == 400
    wrong = "123456" if second != "123456" else "654321"
    for _ in range(4):
        client.post("/api/auth/password/reset", json={"email": email, "code": wrong, "new_password": "new-pass-22"})
    r = client.post("/api/auth/password/reset", json={"email": email, "code": second, "new_password": "new-pass-22"})
    assert r.status_code == 400  # the 5 tries were spent (one on `first` or on a wrong guess)


def test_login_lockout(client):
    email, _ = new_user(client)
    for i in range(5):
        r = client.post("/api/auth/login", json={"email": email, "password": "wrong-pass-1"})
        assert r.status_code == 401, i
    r = client.post("/api/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 429 and "Try again in 15 minutes" in r.json()["detail"]["message"]
    # After the lock expires the right password works and the counter resets.
    with session() as db:
        row = db.get(m.RateLimit, f"login:{email}")
        row.locked_until = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post("/api/auth/login", json={"email": email, "password": PW}).status_code == 200
    with session() as db:
        assert db.get(m.RateLimit, f"login:{email}") is None


def test_change_email_with_code(client, outbox):
    email, h = new_user(client)
    taken, _ = new_user(client)
    assert client.post("/api/auth/code", headers=h, json={"purpose": "change_email", "new_email": taken}).status_code == 409
    assert client.post("/api/auth/code", headers=h, json={"purpose": "change_email", "new_email": email}).status_code == 422

    new_email = f"new{uuid.uuid4().hex[:8]}@test.dev"
    r = client.post("/api/auth/code", headers=h, json={"purpose": "change_email", "new_email": new_email.upper()})
    assert r.status_code == 200
    to, code, purpose = outbox[-1]
    assert (to, purpose) == (new_email, "change_email")
    # Another account can't use this code.
    _, h2 = new_user(client)
    assert client.post("/api/auth/email", headers=h2, json={"new_email": new_email, "code": code}).status_code == 400

    r = client.post("/api/auth/email", headers=h, json={"new_email": new_email, "code": code})
    assert r.status_code == 200 and r.json()["email"] == new_email
    assert outbox[-1][0] == email and outbox[-1][2] == "notice"  # old address told about the change
    assert client.post("/api/auth/login", json={"email": new_email, "password": PW}).status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": PW}).status_code == 401


def test_change_password_with_code(client, outbox):
    email, h = new_user(client)
    second_device = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'email': email, 'password': PW}).json()['token']}"}
    assert client.post("/api/auth/code", headers=h, json={"purpose": "change_password"}).status_code == 200
    to, code, _ = outbox[-1]
    assert to == email
    weak = client.post("/api/auth/password", headers=h, json={"code": code, "new_password": "nonumbers"})
    assert weak.json()["detail"]["code"] == "WEAK_PASSWORD"
    r = client.post("/api/auth/password", headers=h, json={"code": code, "new_password": "fresh-pass-9"})
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=second_device).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).status_code == 200


def test_google_only_account_can_add_password_by_reset(client, outbox, monkeypatch):
    monkeypatch.setattr(auth_svc.settings, "GOOGLE_CLIENT_ID", "cid")
    email = f"g{uuid.uuid4().hex[:8]}@gmail.com"
    monkeypatch.setattr(auth_svc, "verify_google", lambda cred: {"email": email, "sub": uuid.uuid4().hex, "name": "G"})
    client.post("/api/auth/google", json={"credential": "x" * 40})
    client.post("/api/auth/password/forgot", json={"email": email})
    r = client.post("/api/auth/password/reset", json={"email": email, "code": outbox[-1][1], "new_password": "added-pass-1"})
    assert r.status_code == 200 and r.json()["user"]["has_password"] and r.json()["user"]["has_google"]


def test_profile_and_sign_out_everywhere(client):
    email, h = new_user(client)
    r = client.post("/api/auth/profile", headers=h, json={"name": "  Meera Rao "})
    assert r.json()["name"] == "Meera Rao"
    assert client.post("/api/auth/profile", headers=h, json={"name": "   "}).status_code == 422
    other = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'email': email, 'password': PW}).json()['token']}"}
    r = client.post("/api/auth/sign-out-everywhere", headers=h)
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert client.get("/api/auth/me", headers=other).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).status_code == 200


def test_codes_stored_hashed(client, outbox):
    email, _ = new_user(client)
    client.post("/api/auth/password/forgot", json={"email": email})
    code = outbox[-1][1]
    with session() as db:
        row = db.query(m.EmailCode).filter_by(email=email).one()
        assert code not in row.code_hash and len(row.code_hash) == 64


def test_serverless_without_email_provider(client, monkeypatch):
    monkeypatch.setattr(mailer.settings, "SERVERLESS", True)
    email, _ = new_user(client)
    r = client.post("/api/auth/password/forgot", json={"email": email})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "EMAIL_NOT_CONFIGURED"
    with session() as db:  # nothing was stored, so a retry once email works isn't blocked by the cooldown
        assert db.get(m.RateLimit, f"cool:reset:{email}") is None


def test_adds_session_version_column_to_existing_table(tmp_path, monkeypatch):
    eng = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE accounts (id VARCHAR(40) PRIMARY KEY, email VARCHAR(254))"))
        c.execute(text("INSERT INTO accounts (id, email) VALUES ('a', 'a@b.co')"))
    monkeypatch.setattr(db_session, "engine", eng)
    db_session._add_missing_columns()
    db_session._add_missing_columns()  # idempotent
    assert "session_version" in {c["name"] for c in inspect(eng).get_columns("accounts")}
    with eng.connect() as c:
        assert c.execute(text("SELECT session_version FROM accounts")).scalar() == 0
