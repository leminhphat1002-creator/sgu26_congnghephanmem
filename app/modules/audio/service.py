"""Lớp 2 (Business) của audio: tạo giọng nói và quản lý cache MP3."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.audio.store import AudioStore
from app.modules.audio.tts_client import VOICE_BY_LANGUAGE, synthesize_mp3

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 1200


class AudioService:
    """Tạo giọng nói, quản lý cache và tránh tạo trùng MP3."""

    def __init__(self, store: AudioStore | None = None) -> None:
        self.store = store or AudioStore(get_settings().audio_dir)
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    @staticmethod
    def normalize_text(text: str) -> str:
        """Chuẩn hóa khoảng trắng và kiểm tra giới hạn văn bản."""
        if not isinstance(text, str):
            raise ValueError("Văn bản không hợp lệ")

        normalized = re.sub(r"\s+", " ", text).strip()

        if not normalized:
            raise ValueError("Văn bản không được để trống")

        if len(normalized) > MAX_TEXT_LENGTH:
            raise ValueError(f"Văn bản không được vượt quá {MAX_TEXT_LENGTH} ký tự")

        return normalized

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Lấy khóa riêng cho từng cache key."""
        async with self._locks_guard:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def synthesize(self, text: str, lang: str = "vi") -> dict:
        """Tạo MP3 hoặc trả về kết quả từ cache."""
        normalized = self.normalize_text(text)

        if not isinstance(lang, str):
            raise ValueError("Ngôn ngữ không hợp lệ")

        language = lang.lower()

        if language not in VOICE_BY_LANGUAGE:
            raise ValueError(f"Ngôn ngữ chưa được hỗ trợ: {language}")

        voice = VOICE_BY_LANGUAGE[language]
        text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        key = self.store.cache_key(normalized, language, voice)
        lock = await self._get_lock(key)

        async with lock:
            cached = self.store.read(key)

            if cached is not None:
                return {
                    "lang": language,
                    "language": language,
                    "voice": voice,
                    "text_hash": text_hash,
                    "audio_filename": f"{key}.mp3",
                    "cache_key": key,
                    "audio": cached,
                    "cache_hit": True,
                }

            try:
                audio = await synthesize_mp3(normalized, language)

                if not audio:
                    raise RuntimeError("TTS không trả về dữ liệu âm thanh")

                path = self.store.write(key, audio)

                return {
                    "lang": language,
                    "language": language,
                    "voice": voice,
                    "text_hash": text_hash,
                    "audio_filename": path.name,
                    "cache_key": key,
                    "audio": audio,
                    "cache_hit": False,
                }

            except Exception as exc:
                logger.exception("Không thể tạo hoặc lưu âm thanh bằng TTS")
                raise AppError(
                    "tts_unavailable",
                    "Dịch vụ tạo giọng nói hiện không khả dụng",
                    status_code=503,
                ) from exc
