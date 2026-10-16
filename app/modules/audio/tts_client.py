"""Client chuyển văn bản thành giọng nói bằng Edge TTS."""

from __future__ import annotations

import asyncio

VOICE_BY_LANGUAGE = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-AriaNeural",
    "ja": "ja-JP-NanamiNeural",
}


async def synthesize_mp3(
    text: str,
    language: str = "vi",
    timeout: float = 30.0,
) -> bytes:
    """Tạo MP3 bất đồng bộ, có timeout và kiểm tra ngôn ngữ."""
    if not text or not text.strip():
        raise ValueError("Văn bản không được để trống")

    if timeout <= 0:
        raise ValueError("Timeout phải lớn hơn 0")

    if not isinstance(language, str):
        raise ValueError("Ngôn ngữ không hợp lệ")

    language = language.lower()

    if language not in VOICE_BY_LANGUAGE:
        raise ValueError(f"Ngôn ngữ chưa được hỗ trợ: {language}")

    voice = VOICE_BY_LANGUAGE[language]

    async def generate() -> bytes:
        import edge_tts

        communicate = edge_tts.Communicate(text.strip(), voice)
        chunks: list[bytes] = []

        async for item in communicate.stream():
            if item.get("type") == "audio" and item.get("data"):
                chunks.append(item["data"])

        audio = b"".join(chunks)

        if not audio:
            raise RuntimeError("Edge TTS không trả về dữ liệu âm thanh")

        return audio

    try:
        return await asyncio.wait_for(
            generate(),
            timeout=timeout,
        )
    except TimeoutError as exc:
        raise TimeoutError(
            f"Edge TTS vượt quá thời gian chờ {timeout} giây"
        ) from exc
