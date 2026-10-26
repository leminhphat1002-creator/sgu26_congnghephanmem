"""Presence tạm trong RAM của một process; không ghi database hoặc thông tin cá nhân."""

import secrets
import threading
import time
from collections.abc import Callable

ACTIVE_WINDOW_SECONDS = 120
COOKIE_NAME = "bat_trang_visitor"


class VisitorPresence:
    def __init__(
        self, *, clock: Callable[[], float] = time.monotonic, capacity: int = 10_000
    ) -> None:
        self._clock = clock
        self._capacity = capacity
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        expired = [key for key, last in self._seen.items() if now - last >= ACTIVE_WINDOW_SECONDS]
        for key in expired:
            del self._seen[key]

    def heartbeat(self, token: str | None) -> str:
        with self._lock:
            now = self._clock()
            self._prune(now)
            if token not in self._seen:
                if len(self._seen) >= self._capacity:
                    raise OverflowError("Visitor presence capacity reached")
                token = secrets.token_hex(32)
            self._seen[token] = now
            return token

    def snapshot(self) -> dict:
        with self._lock:
            self._prune(self._clock())
            return {
                "active_visitors": len(self._seen),
                "active_window_seconds": ACTIVE_WINDOW_SECONDS,
            }
