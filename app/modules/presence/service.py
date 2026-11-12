"""Phiên khách và vị trí chia sẻ tạm thời trong RAM của một tiến trình."""

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

ACTIVE_WINDOW_SECONDS = 120
COOKIE_NAME = "bat_trang_visitor"


@dataclass
class VisitorSession:
    id: str
    last_seen: float
    location: dict[str, float] | None = None
    location_expires_at: float = 0.0


class VisitorPresence:
    def __init__(
        self, *, clock: Callable[[], float] = time.monotonic, capacity: int = 10_000
    ) -> None:
        self._clock = clock
        self._capacity = capacity
        self._seen: dict[str, VisitorSession] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        expired = []
        for key, session in self._seen.items():
            if now - session.last_seen >= ACTIVE_WINDOW_SECONDS:
                expired.append(key)
            elif session.location is not None and now >= session.location_expires_at:
                session.location = None
        for key in expired:
            del self._seen[key]

    def heartbeat(
        self,
        token: str | None,
        *,
        location: tuple[float, float] | None = None,
        update_location: bool = False,
    ) -> str:
        with self._lock:
            now = self._clock()
            self._prune(now)
            session = self._seen.get(token) if token is not None else None
            if session is None:
                if len(self._seen) >= self._capacity:
                    raise OverflowError("Visitor presence capacity reached")
                token = secrets.token_hex(32)
                session = self._seen[token] = VisitorSession(secrets.token_hex(8), now)
            session.last_seen = now
            if update_location:
                session.location = (
                    {"latitude": round(location[0], 3), "longitude": round(location[1], 3)}
                    if location is not None
                    else None
                )
                session.location_expires_at = now + ACTIVE_WINDOW_SECONDS
            return token

    def snapshot(self, *, include_sessions: bool = False) -> dict:
        with self._lock:
            now = self._clock()
            self._prune(now)
            result = {
                "active_visitors": len(self._seen),
                "active_window_seconds": ACTIVE_WINDOW_SECONDS,
            }
            if include_sessions:
                sessions = sorted(self._seen.values(), key=lambda session: -session.last_seen)
                result["sessions"] = [
                    {
                        "id": session.id,
                        "last_seen_seconds_ago": int(now - session.last_seen),
                        "location": session.location,
                    }
                    for session in sessions
                ]
            return result
