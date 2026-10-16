"""Quản lý cache MP3 bằng khóa SHA256 và ghi file an toàn."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

_KEY_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class AudioStore:
    """Lưu và đọc file MP3 trong thư mục cache."""

    def __init__(self, root: str | Path = "audio_cache") -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def cache_key(text: str, language: str, voice: str) -> str:
        """Tạo khóa SHA256 từ văn bản, ngôn ngữ và giọng đọc."""
        content = "\0".join((language, voice, text)).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def _get_path(self, key: str) -> Path:
        """Kiểm tra khóa để ngăn truy cập đường dẫn ngoài cache."""
        if not isinstance(key, str) or not _KEY_PATTERN.fullmatch(key):
            raise ValueError("Khóa cache không hợp lệ")

        path = (self.root / f"{key}.mp3").resolve()

        if path.parent != self.root:
            raise ValueError("Đường dẫn cache không hợp lệ")

        return path

    def exists(self, key: str) -> bool:
        """Kiểm tra file cache có tồn tại và có dữ liệu."""
        path = self._get_path(key)
        return path.is_file() and path.stat().st_size > 0

    def read(self, key: str) -> bytes | None:
        """Đọc file MP3; trả về None nếu chưa có hoặc file rỗng."""
        path = self._get_path(key)

        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return None

        if not data:
            path.unlink(missing_ok=True)
            return None

        return data

    def write(self, key: str, data: bytes) -> Path:
        """Ghi file tạm rồi thay thế file đích một cách nguyên tử."""
        if not isinstance(data, bytes) or not data:
            raise ValueError("Dữ liệu MP3 không được rỗng")

        target = self._get_path(key)

        fd, temp_name = tempfile.mkstemp(
            prefix=".audio-",
            suffix=".tmp",
            dir=self.root,
        )

        try:
            with os.fdopen(fd, "wb") as file:
                file.write(data)
                file.flush()
                os.fsync(file.fileno())

            os.replace(temp_name, target)
        finally:
            Path(temp_name).unlink(missing_ok=True)

        return target
