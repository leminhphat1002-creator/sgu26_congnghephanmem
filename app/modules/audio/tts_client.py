"""Client Edge TTS: chuyển văn bản thành MP3 với timeout hữu hạn."""
from __future__ import annotations

import asyncio

import edge_tts

from app.core.exceptions import AppError

VOICES = {"vi": "vi-VN-HoaiMyNeural", "en": "en-US-AriaNeural", "ja": "ja-JP-NanamiNeural"}


class EdgeTTSClient:
    def __init__(self, timeout_s: float = 15.0) -> None:
        self.timeout_s = timeout_s

    async def synthesize(self, text: str, lang: str) -> bytes:
        if not text or not text.strip():
            raise AppError("empty_text", "Văn bản cần đọc không được để trống.", 422)
        language = lang.lower().split("-")[0]
        voice = VOICES.get(language)
        if voice is None:
            raise AppError("unsupported_language", "Ngôn ngữ TTS hỗ trợ: vi, en, ja.", 422)
        try:
            async def collect() -> bytes:
                chunks: list[bytes] = []
                communicate = edge_tts.Communicate(text.strip(), voice)
                async for chunk in communicate.stream():
                    if chunk.get("type") == "audio":
                        chunks.append(chunk["data"])
                return b"".join(chunks)
            audio = await asyncio.wait_for(collect(), timeout=self.timeout_s)
            if not audio:
                raise RuntimeError("Edge TTS không trả dữ liệu âm thanh.")
            return audio
        except AppError:
            raise
        except Exception as exc:
            raise AppError("tts_unavailable", "Không thể tạo giọng đọc lúc này.", 503) from exc
