"""
Game service — loads engines, serialises access per game, persists after each action.

A write-through in-memory cache avoids re-parsing the snapshot on every request;
the database remains the source of truth, so a server restart or browser
refresh resumes exactly where the player left off.
"""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Iterator, Optional

from sqlalchemy import select

from app.config import settings
from app.database import models as m
from app.database.session import SessionLocal
from app.services import repository as repo
from app.services import serializers as ser
from app.simulation import portfolio_engine as pe
from app.simulation.game_engine import ActionError, GameEngine
from app.simulation.state import GameState


class NotFound(Exception):
    pass


_cache: dict[str, tuple[GameState, str]] = {}
_locks: dict[str, threading.Lock] = {}
_global = threading.Lock()


def _lock(game_id: str) -> threading.Lock:
    with _global:
        return _locks.setdefault(game_id, threading.Lock())


def _get(db, game_id: str, for_update: bool = False) -> tuple[GameState, str]:
    if settings.SERVERLESS:
        # Another instance may have advanced this game: always read the database, and lock
        # the row for mutating actions so two instances can't interleave (no-op on SQLite).
        if for_update:
            db.execute(select(m.Game.id).where(m.Game.id == game_id).with_for_update())
        loaded = repo.load(db, game_id)
        if loaded is None:
            raise NotFound(game_id)
        return loaded
    if game_id in _cache:
        return _cache[game_id]
    loaded = repo.load(db, game_id)
    if loaded is None:
        raise NotFound(game_id)
    _cache[game_id] = loaded
    return loaded


@contextmanager
def session() -> Iterator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def new_game(player_name: str = "Player", seed: Optional[int] = None, player_id: Optional[str] = None) -> dict:
    game_id = uuid.uuid4().hex[:16]
    with session() as db:
        if player_id and db.get(m.Player, player_id) is None:
            player_id = None
        if not player_id:
            player_id = uuid.uuid4().hex[:16]
            db.add(m.Player(id=player_id, name=(player_name or "Player")[:80]))
            db.flush()
        eng = GameEngine.new_game(game_id, seed)
        repo.save(db, eng.state, player_id)
        _cache[game_id] = (eng.state, player_id)
        return {"player_id": player_id, "state": ser.full_state(eng.state)}


def read(game_id: str, fn: Callable[[GameState], Any]) -> Any:
    with session() as db, _lock(game_id):
        state, _ = _get(db, game_id)
        return fn(state)


def act(game_id: str, fn: Callable[[GameEngine], Any]) -> dict:
    """Run a mutating action atomically: on any error the cached state is discarded."""
    with session() as db, _lock(game_id):
        state, player_id = _get(db, game_id, for_update=True)
        eng = GameEngine(state)
        try:
            result = fn(eng)
        except ActionError:
            # Validation errors are raised before mutation, but be safe with RNG/state.
            _cache.pop(game_id, None)
            raise
        except Exception:
            _cache.pop(game_id, None)
            raise
        repo.save(db, state, player_id)
        return {"result": result, "state": ser.full_state(state)}


def save_slot(game_id: str, name: str) -> dict:
    with session() as db, _lock(game_id):
        state, player_id = _get(db, game_id, for_update=True)
        summary ={"nav": pe.nav(state), "level": state.career.level, "title": state.career.title,
                   "reputation": state.career.reputation, "date": state.now.strftime("%a %d %b %Y %H:%M"),
                   "quarter": state.career.quarter_index}
        repo.save(db, state, player_id)  # flush pending history first
        slot = m.SaveSlot(game_id=game_id, player_id=player_id, name=(name or "Save")[:80], game_time=state.now,
                          summary=summary, snapshot=state.model_dump(mode="json"))
        db.add(slot)
        db.commit()
        return {"id": slot.id, "name": slot.name, "game_time": slot.game_time.isoformat(), "summary": summary}


def list_saves(player_id: str) -> list[dict]:
    with session() as db:
        rows = db.execute(select(m.SaveSlot).where(m.SaveSlot.player_id == player_id)
                          .order_by(m.SaveSlot.created_at.desc()).limit(30)).scalars().all()
        return [{"id": r.id, "game_id": r.game_id, "name": r.name, "game_time": r.game_time.isoformat(),
                 "created_at": r.created_at.isoformat(), "summary": r.summary} for r in rows]


def load_slot(save_id: int, player_id: Optional[str] = None) -> dict:
    with session() as db:
        slot = db.get(m.SaveSlot, save_id)
        if slot is None or (player_id and slot.player_id != player_id):
            raise NotFound(str(save_id))
        with _lock(slot.game_id):
            state = GameState.model_validate(slot.snapshot)
            repo.rollback_to(db, state)
            row = db.get(m.Game, slot.game_id)
            row.snapshot = slot.snapshot
            row.game_time = state.now
            row.status = state.career.status
            row.updated_at = datetime.utcnow()
            db.commit()
            _cache[slot.game_id] = (state, slot.player_id)
            return {"game_id": slot.game_id, "state": ser.full_state(state)}


def player_of(game_id: str) -> str:
    with session() as db:
        row = db.get(m.Game, game_id)
        if row is None:
            raise NotFound(game_id)
        return row.player_id


def clear_cache() -> None:
    _cache.clear()
