import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.modules.audio.store import AudioStore
from app.modules.audio.tts_client import synthesize_mp3


async def main():
    text = "Xin chào, đây là bài kiểm tra chức năng chuyển văn bản thành giọng nói."

    audio = await synthesize_mp3(text, language="vi")

    store = AudioStore("audio_cache")
    key = store.cache_key(
        text,
        "vi",
        "vi-VN-HoaiMyNeural",
    )
    path = store.write(key, audio)

    print(f"Tạo file MP3 thành công: {path}")
    print(f"Dung lượng: {Path(path).stat().st_size} bytes")


if __name__ == "__main__":
    asyncio.run(main())
