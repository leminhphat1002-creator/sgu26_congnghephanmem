"""Thử tạo giọng mới với socket bị chặn; không dùng âm thanh đã cache."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from app.modules.audio.offline import OfflineSpeech
from app.modules.audio.store import AudioStore


def main() -> None:
    phrases = {
        "vi": "Bát Tràng có nghề gốm truyền thống. Giọng đọc này được tạo trực tiếp trên máy chủ.",
        "en": "Bat Trang is a pottery village. This voice is generated locally on the server.",
        "ja": "バッチャンは陶器の村です。この音声はサーバーで生成しています。",
    }
    with tempfile.TemporaryDirectory(prefix="bat-trang-offline-") as directory:
        speech = OfflineSpeech(AudioStore(Path(directory)))
        with (
            patch(
                "socket.socket.connect", side_effect=RuntimeError("Network disabled for this check")
            ),
            patch(
                "socket.create_connection",
                side_effect=RuntimeError("Network disabled for this check"),
            ),
        ):
            for language, text in phrases.items():
                started = time.perf_counter()
                parts = []
                first = 0.0
                for part in speech.stream(text, language):
                    if not parts:
                        first = time.perf_counter() - started
                    parts.append(part)
                size = sum(map(len, parts))
                if size < 1000:
                    raise RuntimeError(f"No usable local audio: {language}")
                print(f"{language}: offline OK; first={first:.2f}s; bytes={size}", flush=True)


if __name__ == "__main__":
    main()
