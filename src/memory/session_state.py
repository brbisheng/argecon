"""Lightweight per-session storage for structured conversation slots."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any

from src.common.schemas import SessionState


class SessionStateStore:
    """In-memory V1 session memory store keyed by ``session_id``."""

    def __init__(self) -> None:
        self._states: dict[str, SessionState] = {}
        self._lock = RLock()

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            return self._states.get(session_id)

    def get_or_create(self, session_id: str, **defaults: Any) -> SessionState:
        with self._lock:
            state = self._states.get(session_id)
            if state is None:
                state = SessionState(session_id=session_id, **defaults)
                self._states[session_id] = state
            return state

    def save(self, state: SessionState) -> SessionState:
        with self._lock:
            if state.updated_at is None:
                state.updated_at = datetime.now(timezone.utc)
            self._states[state.session_id] = state
            return state

    def clear(self) -> None:
        with self._lock:
            self._states.clear()


DEFAULT_SESSION_STORE = SessionStateStore()


__all__ = ["DEFAULT_SESSION_STORE", "SessionState", "SessionStateStore"]
