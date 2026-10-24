"""Lớp Business của Content.

Lấy nội dung biên soạn từ SQLite, fallback ngôn ngữ,
chuẩn hóa văn bản và quản lý cache SQLite.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.modules.content.repository import ContentRepository


class ContentService:
    """Lấy và xử lý nội dung biên soạn đa ngôn ngữ."""

    SUPPORTED_LANGUAGES = ("vi", "en", "ja")
    MAX_EXTRACT_LENGTH = 900
    MIN_EXTRACT_LENGTH = 450

    def __init__(self, repository: ContentRepository | None = None) -> None:
        self.repository = repository

    @staticmethod
    def clean_text(text: str | None) -> str:
        """Chuẩn hóa khoảng trắng và loại bỏ HTML."""
        if not text:
            return ""

        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @classmethod
    def shorten_text(cls, text: str | None) -> str:
        """Rút gọn văn bản tại ranh giới câu."""
        cleaned = cls.clean_text(text)

        if len(cleaned) <= cls.MAX_EXTRACT_LENGTH:
            return cleaned

        candidate = cleaned[: cls.MAX_EXTRACT_LENGTH]
        sentence_ends = list(re.finditer(r"[.!?。！？](?:\s|$)", candidate))

        if sentence_ends:
            end = sentence_ends[-1].end()

            if end >= cls.MIN_EXTRACT_LENGTH:
                return candidate[:end].strip()

        if " " in candidate:
            candidate = candidate.rsplit(" ", 1)[0]

        return candidate.rstrip(" ,;:-") + "…"

    @staticmethod
    def normalize_cache_title(title: str) -> str:
        """Chuẩn hóa khóa cache không phân biệt hoa/thường."""
        normalized = unicodedata.normalize(
            "NFC",
            title.strip(),
        )
        return normalized.casefold()

    async def get_content(self, title: str, lang: str = "vi") -> dict[str, Any] | None:
        """Tra tên địa điểm trong SQLite; không gọi dịch vụ nội dung bên ngoài."""
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Tên địa điểm không được để trống")
        if lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError("Ngôn ngữ không được hỗ trợ")
        if self.repository is None:
            return None
        location_id = self.repository.find_location_id(title)
        if location_id is None:
            return None
        return await self.get_location_content(location_id, lang)

    async def get_location_content(self, location_id: int, lang: str = "vi") -> dict | None:
        """Ưu tiên ngôn ngữ yêu cầu, sau đó tiếng Anh và tiếng Việt."""
        if lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError("Ngôn ngữ không được hỗ trợ")
        if self.repository is None:
            return None
        for language in dict.fromkeys((lang, "en", "vi")):
            content = self.repository.get_narration(location_id, language)
            if content and self.clean_text(content["extract"]):
                return {
                    **content,
                    "extract": self.shorten_text(content["extract"]),
                    "requested_language": lang,
                    "fallback_used": language != lang,
                }
        return None

    def get_cached_content(
        self,
        title: str,
        lang: str,
    ) -> dict[str, Any] | None:
        """Đọc cache hiện có, không gọi Wikimedia."""
        if lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Ngôn ngữ chưa được hỗ trợ: {lang}")

        if self.repository is None:
            return None

        cached = self.repository.get(
            self.normalize_cache_title(title),
            lang,
        )

        if cached is None:
            return None

        return {
            "title": cached.page_title,
            "extract": cached.extract,
            "url": cached.source_url,
            "language": cached.language,
            "expires_at": cached.expires_at.isoformat(),
        }

    def invalidate_content(
        self,
        title: str,
        lang: str | None = None,
    ) -> int:
        """Xóa cache theo tiêu đề đã chuẩn hóa."""
        if self.repository is None:
            return 0

        cache_title = self.normalize_cache_title(title)

        return self.repository.invalidate(
            page_title=cache_title,
            language=lang,
        )
