"""Cấu hình ứng dụng, đọc từ biến môi trường (xem .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _read_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Biến môi trường {name} phải là số, nhận được: {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    database_url: str
    audio_dir: str
    wikimedia_user_agent: str
    wikimedia_timeout_s: float
    tts_timeout_s: float
    request_timeout_s: float
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        """Đọc cấu hình mới nhất từ môi trường (không cache, dùng cho Alembic và test)."""
        return cls(
            database_url=os.environ.get("DATABASE_URL", "sqlite:///./data/app.db"),
            audio_dir=os.environ.get("AUDIO_DIR", "./audio_files"),
            wikimedia_user_agent=os.environ.get(
                "WIKIMEDIA_USER_AGENT",
                "sgu26-congnghephanmem/0.1",
            ),
            wikimedia_timeout_s=_read_float("WIKIMEDIA_TIMEOUT_S", 8.0),
            tts_timeout_s=_read_float("TTS_TIMEOUT_S", 15.0),
            request_timeout_s=_read_float("REQUEST_TIMEOUT_S", 25.0),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )


@lru_cache
def get_settings() -> Settings:
    """Cấu hình dùng chung của app (cache một lần cho mỗi process)."""
    return Settings.from_env()
