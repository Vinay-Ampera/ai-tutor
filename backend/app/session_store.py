from dataclasses import dataclass, field
from threading import Lock
from typing import Literal, TypedDict

from app.graphs.tutor_state import TutorState


class TutorMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


@dataclass
class TutorSession:
    state: TutorState | None = None
    messages: list[TutorMessage] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, TutorSession] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> TutorSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create(self, session_id: str) -> TutorSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = TutorSession()
                self._sessions[session_id] = session
            return session

    def delete(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            return

        with session.lock:
            with self._lock:
                if self._sessions.get(session_id) is session:
                    del self._sessions[session_id]


session_store = SessionStore()
