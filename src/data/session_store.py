"""In-memory CallSession store (swap for Redis/DB later)."""

from __future__ import annotations

from threading import RLock
from typing import Optional

from ..models.call_session import CallSession


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, CallSession] = {}
        self._lock = RLock()

    def get_or_create(self, session_id: str, phone_number: str) -> CallSession:
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]
            session = CallSession(session_id=session_id, phone_number=phone_number)
            self._sessions[session_id] = session
            return session

    def get(self, session_id: str) -> Optional[CallSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
