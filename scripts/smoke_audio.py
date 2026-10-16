"""Smoke test Edge TTS thật và xác nhận MP3 được tạo thành công."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asyncio
import tempfile
from pathlib import Path

from app.core.config import Settings
from app.modules.audio.tts_client import synthesize_mp3


async def main() -> None:
    """Generate a real MP3 and verify that it contains data."""
    text = "Xin chào, đây là bài kiểm tra tổng hợp giọng nói."
    settings = Settings.from_env()

    print("Đang gọi Edge TTS...")
    audio_data = await synthesize_mp3(
        text=text,
        language="vi",
        timeout=settings.tts_timeout_s,
    )

    if not audio_data:
        raise RuntimeError("Edge TTS trả về dữ liệu âm thanh rỗng.")

    with tempfile.TemporaryDirectory(prefix="smoke-audio-") as temp_dir:
        output_path = Path(temp_dir) / "smoke-test.mp3"
        output_path.write_bytes(audio_data)

        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError("Không tạo được file MP3 hợp lệ.")

        print("Smoke test TTS: PASS")
        print(f"Kích thước MP3: {output_path.stat().st_size:,} bytes")
        print("File MP3 đã được ghi và kiểm tra thành công.")

    print("File tạm đã được dọn dẹp.")


if __name__ == "__main__":
    asyncio.run(main())
