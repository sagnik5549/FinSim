import os
import sys
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp(prefix="ibmode-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp, 'test.db').as_posix()}"
os.environ["IBM_DISABLE_ML"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.simulation.game_engine import GameEngine  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def game(client):
    """A fresh game via the API; returns (client, headers, state)."""
    r = client.post("/api/game/new", json={"seed": 1234})
    assert r.status_code == 200, r.text
    body = r.json()
    headers = {"X-Game-Id": body["state"]["game_id"]}
    return client, headers, body["state"]


@pytest.fixture
def engine():
    return GameEngine.new_game("test-engine", seed=77)


def clear_blocking(eng: GameEngine) -> None:
    """Resolve any blocking popups the way a cautious player would."""
    s = eng.state
    for _ in range(10):
        blocking = [p for p in s.popups if p.blocking]
        if not blocking:
            return
        p = blocking[0]
        if p.type == "RISK_WARNING":
            eng.resolve_risk(p.payload["warning_id"], "IGNORE")
        else:
            eng.ack_popup(p.id)
