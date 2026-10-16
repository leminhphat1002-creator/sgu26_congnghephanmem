"""Lưu MP3 an toàn, đặt tên cache bằng SHA-256 và ghi file nguyên tử."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path


class AudioStore:
    def __init__(self, audio_dir: str | Path) -> None:
        self.root = Path(audio_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def cache_key(text: str, lang: str, voice: str) -> str:
        raw = "\\0".join((lang.strip().lower(), voice.strip(), " ".join(text.split())))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def path_for_key(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            raise ValueError("Khóa audio không hợp lệ.")
        path = (self.root / f"{key}.mp3").resolve()
        if path.parent != self.root:
            raise ValueError("Đường dẫn audio không hợp lệ.")
        return path

    def exists(self, key: str) -> bool:
        return self.path_for_key(key).is_file()

    def save_bytes(self, key: str, content: bytes) -> Path:
        if not content:
            raise ValueError("Không thể lưu audio rỗng.")
        target = self.path_for_key(key)
        fd, temp_name = tempfile.mkstemp(prefix=".audio-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return target
