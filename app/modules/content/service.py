"""Lớp 2 (Business) của content.

Nhiệm vụ: làm sạch văn bản Wikimedia, rút gọn 450-900 ký tự ở ranh giới câu, chuỗi fallback
ngôn ngữ đích -> en -> ngôn ngữ nguồn (không dịch máy), TTL và invalidation cache nội dung.
content không import module nào khác. (Viết ở Tuần 3.)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.modules.content.repository import ContentRepository
from app.modules.content.wikimedia_client import WikimediaClient


class ContentService:
    """Làm sạch nội dung Wikimedia và chọn nội dung theo ngôn ngữ."""

    SUPPORTED_LANGUAGES = ("vi", "en", "ja")
    MAX_EXTRACT_LENGTH = 900
    MIN_EXTRACT_LENGTH = 450
    CACHE_TTL_SECONDS = 3600

    def __init__(
        self,
        client: WikimediaClient | None = None,
        repository: ContentRepository | None = None,
    ) -> None:
        self.client = client or WikimediaClient()
        self.repository = repository

    @staticmethod
    def clean_text(text: str | None) -> str:
        """Chuẩn hóa khoảng trắng và loại bỏ thẻ HTML."""
        if not text:
            return ""

        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def shorten_text(cls, text: str | None) -> str:
        """Rút gọn nội dung, ưu tiên cắt tại ranh giới câu."""
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
        """Chuẩn hóa khóa cache, không phân biệt hoa/thường."""
        normalized = unicodedata.normalize("NFC", title.strip())
        return normalized.casefold()

    async def get_content(
        self,
        title: str,
        lang: str = "vi",
    ) -> dict[str, Any] | None:
        """Lấy nội dung theo ngôn ngữ yêu cầu, có cache và fallback."""
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Tên địa điểm không được để trống")

        title = title.strip()
        cache_title = self.normalize_cache_title(title)

        if lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Ngôn ngữ chưa được hỗ trợ: {lang}")

        fallback_order = [lang]
        for fallback_lang in ("en", "vi"):
            if fallback_lang not in fallback_order:
                fallback_order.append(fallback_lang)

        for current_lang in fallback_order:
            if self.repository is not None:
                cached = self.repository.get(cache_title, current_lang)

                if cached is not None:
                    return {
                        "title": cached.page_title,
                        "extract": cached.extract,
                        "url": cached.source_url,
                        "language": cached.language,
                        "requested_language": lang,
                        "fallback_used": current_lang != lang,
                    }

            page = await self.client.get_extract(title, current_lang)

            if page is None:
                continue

            extract = self.shorten_text(page.get("extract"))
            if not extract:
                continue

            if self.repository is not None:
                self.repository.save(
                    page_title=cache_title,
                    language=current_lang,
                    extract=extract,
                    source_url=page.get("url"),
                    ttl_seconds=self.CACHE_TTL_SECONDS,
                )

            return {
                **page,
                "extract": extract,
                "language": current_lang,
                "requested_language": lang,
                "fallback_used": current_lang != lang,
            }

        return None

    def get_cached_content(
        self,
        title: str,
        lang: str,
    ) -> dict[str, Any] | None:
        """Đọc cache hiện có mà không gọi Wikimedia."""
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

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius: int = 10000,
        limit: int = 10,
        lang: str = "vi",
    ) -> list[dict[str, Any]]:
        """Tìm các trang Wikipedia gần vị trí hiện tại."""
        return await self.client.geosearch(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            limit=limit,
            lang=lang,
        )

    async def get_translation_title(
        self,
        page_id: int,
        source_lang: str = "vi",
        target_lang: str = "en",
    ) -> str | None:
        """Lấy tiêu đề trang tương ứng ở ngôn ngữ đích."""
        return await self.client.get_langlinks(
            page_id=page_id,
            source_lang=source_lang,
            target_lang=target_lang,
        )
