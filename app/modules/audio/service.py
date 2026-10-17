"""Lớp 2 (Business) của audio.

Nhiệm vụ: synthesize(text, lang) có cache (chuẩn hóa văn bản, tính key, cache hit/miss,
khóa theo key), lỗi tts_unavailable. audio không import module nào khác. (Viết ở Tuần 3.)"""

from __future__ import annotations

import asyncio
import logging
import re

from app.modules.audio.store import AudioStore
from app.modules.audio.tts_client import VOICE_BY_LANGUAGE, synthesize_mp3

logger = logging.getLogger(__name__)


class AudioService:
    """Generate speech and cache MP3 files."""

    def __init__(self, store: AudioStore | None = None) -> None:
        self.store = store or AudioStore()
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    @staticmethod
    def normalize_text(text: str) -> str:
        if not isinstance(text, str):
            raise ValueError("Văn bản không hợp lệ")
        return re.sub(r"\s+", " ", text).strip()

    async def _get_lock(self, key: str) -> asyncio.Lock:
        async with self._locks_guard:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def synthesize(self, text: str, lang: str = "vi") -> dict:
        normalized = self.normalize_text(text)
        if not normalized:
            raise ValueError("Văn bản không được để trống")

        if not isinstance(lang, str):
            raise ValueError("Ngôn ngữ không hợp lệ")

        language = lang.lower()
        if language not in VOICE_BY_LANGUAGE:
            raise ValueError(f"Ngôn ngữ chưa được hỗ trợ: {language}")

        voice = VOICE_BY_LANGUAGE[language]
        key = self.store.cache_key(normalized, language, voice)
        lock = await self._get_lock(key)

        async with lock:
            cached = self.store.read(key)
            if cached is not None:
                return {
                    "cache_key": key,
                    "language": language,
                    "audio": cached,
                    "cache_hit": True,
                }

            try:
                audio = await synthesize_mp3(normalized, language)
                if not audio:
                    raise RuntimeError("TTS không trả về dữ liệu âm thanh")

                self.store.write(key, audio)
                return {
                    "cache_key": key,
                    "language": language,
                    "audio": audio,
                    "cache_hit": False,
                }
            except Exception as exc:
                logger.exception("Không thể tạo âm thanh bằng TTS")
                raise RuntimeError("tts_unavailable") from exc
