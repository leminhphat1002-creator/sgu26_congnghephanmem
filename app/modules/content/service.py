"""Lớp Business của Content.

Lấy nội dung Wikimedia, xử lý langlinks, fallback ngôn ngữ,
chuẩn hóa văn bản và quản lý cache SQLite.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.modules.content.repository import ContentRepository
from app.modules.content.wikimedia_client import WikimediaClient


class ContentService:
    """Lấy và xử lý nội dung Wikimedia đa ngôn ngữ."""

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

    def _read_cache(
        self,
        cache_title: str,
        language: str,
        requested_language: str,
    ) -> dict[str, Any] | None:
        """Đọc cache theo tên địa điểm gốc và ngôn ngữ."""
        if self.repository is None:
            return None

        cached = self.repository.get(cache_title, language)

        if cached is None:
            return None

        return {
            "title": cached.page_title,
            "extract": cached.extract,
            "url": cached.source_url,
            "language": cached.language,
            "requested_language": requested_language,
            "fallback_used": language != requested_language,
        }

    def _prepare_content(
        self,
        page: dict[str, Any] | None,
        cache_title: str,
        language: str,
        requested_language: str,
    ) -> dict[str, Any] | None:
        """Làm sạch và lưu nội dung tìm được."""
        if page is None:
            return None

        extract = self.shorten_text(page.get("extract"))

        if not extract:
            return None

        if self.repository is not None:
            self.repository.save(
                page_title=cache_title,
                language=language,
                extract=extract,
                source_url=page.get("url"),
                ttl_seconds=self.CACHE_TTL_SECONDS,
            )

        return {
            **page,
            "extract": extract,
            "language": language,
            "requested_language": requested_language,
            "fallback_used": language != requested_language,
        }

    async def get_content(
        self,
        title: str,
        lang: str = "vi",
    ) -> dict[str, Any] | None:
        """Tìm nội dung theo ngôn ngữ, sử dụng langlinks và fallback."""
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Tên địa điểm không được để trống")

        if lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Ngôn ngữ chưa được hỗ trợ: {lang}")

        title = title.strip()
        cache_title = self.normalize_cache_title(title)

        # 1. Ưu tiên cache đúng ngôn ngữ được yêu cầu.
        cached = self._read_cache(
            cache_title,
            lang,
            lang,
        )

        if cached is not None:
            return cached

        # 2. Thử tiêu đề đầu vào trên Wikipedia ngôn ngữ đích.
        target_page = await self.client.get_extract(title, lang)

        result = self._prepare_content(
            target_page,
            cache_title,
            lang,
            lang,
        )

        if result is not None:
            return result

        # 3. Lấy trang gốc tiếng Việt để tìm liên kết ngôn ngữ.
        source_page = None

        if lang != "vi":
            source_page = await self.client.get_extract(
                title,
                "vi",
            )
        else:
            source_page = target_page

        page_id = None

        if source_page is not None:
            page_id = source_page.get("page_id")

        # 4. Tra tiêu đề tương ứng trong ngôn ngữ được chọn.
        if lang != "vi" and isinstance(page_id, int) and page_id > 0:
            translated_title = await self.client.get_langlinks(
                page_id=page_id,
                source_lang="vi",
                target_lang=lang,
            )

            if translated_title:
                translated_page = await self.client.get_extract(
                    translated_title,
                    lang,
                )

                result = self._prepare_content(
                    translated_page,
                    cache_title,
                    lang,
                    lang,
                )

                if result is not None:
                    return result

        # 5. Nếu vẫn không có, thử tiếng Anh rồi tiếng Việt.
        fallback_order = []

        for fallback_lang in ("en", "vi"):
            if fallback_lang != lang:
                fallback_order.append(fallback_lang)

        for current_lang in fallback_order:
            cached = self._read_cache(
                cache_title,
                current_lang,
                lang,
            )

            if cached is not None:
                return cached

            if current_lang == "vi" and source_page is not None:
                page = source_page
            else:
                # Với tiếng Anh, ưu tiên tiêu đề từ langlinks.
                lookup_title = title

                if current_lang == "en" and isinstance(page_id, int) and page_id > 0:
                    english_title = await self.client.get_langlinks(
                        page_id=page_id,
                        source_lang="vi",
                        target_lang="en",
                    )

                    if english_title:
                        lookup_title = english_title

                page = await self.client.get_extract(
                    lookup_title,
                    current_lang,
                )

            result = self._prepare_content(
                page,
                cache_title,
                current_lang,
                lang,
            )

            if result is not None:
                return result

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

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius: int = 10000,
        limit: int = 10,
        lang: str = "vi",
    ) -> list[dict[str, Any]]:
        """Tìm các trang Wikipedia gần GPS."""
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
        """Lấy tiêu đề tương ứng ở ngôn ngữ đích."""
        return await self.client.get_langlinks(
            page_id=page_id,
            source_lang=source_lang,
            target_lang=target_lang,
        )
