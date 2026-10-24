"""Lớp 3 (Data Access) của content: đọc/ghi bảng NarrationCache trong SQLite. (Tuần 3.)"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.content.models import NarrationCache, PoiNarration


class ContentRepository:
    """Truy cập cache nội dung Wikimedia."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self,
        page_title: str,
        language: str,
    ) -> NarrationCache | None:
        """Lấy cache còn hạn; xóa bản ghi hết hạn nếu tìm thấy."""
        statement = select(NarrationCache).where(
            NarrationCache.page_title == page_title,
            NarrationCache.language == language,
        )
        cached = self.session.scalar(statement)

        if cached is None:
            return None

        if cached.expires_at <= datetime.now(UTC).replace(tzinfo=None):
            self.session.delete(cached)
            self.session.commit()
            return None

        return cached

    def save(
        self,
        page_title: str,
        language: str,
        extract: str,
        source_url: str | None = None,
        ttl_seconds: int = 3600,
    ) -> NarrationCache:
        """Lưu nội dung và thời điểm hết hạn."""
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds phải lớn hơn 0")

        cached = self.session.scalar(
            select(NarrationCache).where(
                NarrationCache.page_title == page_title,
                NarrationCache.language == language,
            )
        )

        now = datetime.now(UTC).replace(tzinfo=None)
        expires_at = now + timedelta(seconds=ttl_seconds)

        if cached is None:
            cached = NarrationCache(
                page_title=page_title,
                language=language,
                extract=extract,
                source_url=source_url,
                created_at=now,
                expires_at=expires_at,
            )
            self.session.add(cached)
        else:
            cached.extract = extract
            cached.source_url = source_url
            cached.created_at = now
            cached.expires_at = expires_at

        self.session.commit()
        self.session.refresh(cached)
        return cached

    def invalidate(
        self,
        page_title: str,
        language: str | None = None,
    ) -> int:
        """Xóa cache theo tiêu đề, tùy chọn giới hạn theo ngôn ngữ."""
        statement = delete(NarrationCache).where(NarrationCache.page_title == page_title)

        if language is not None:
            statement = statement.where(NarrationCache.language == language)

        result = self.session.execute(statement)
        self.session.commit()
        return result.rowcount or 0

    def get_narration(self, location_id: int, language: str) -> dict | None:
        row = self.session.scalar(
            select(PoiNarration).where(
                PoiNarration.location_id == location_id, PoiNarration.language == language
            )
        )
        if row is None:
            return None
        return {"title": row.title, "extract": row.content, "language": row.language, "url": None}

    def find_location_id(self, title: str) -> int | None:
        from app.modules.poi.models import Location

        # Python casefold hỗ trợ tên tiếng Việt, không phụ thuộc SQLite NOCASE.
        normalized = title.strip().casefold()
        for row in self.session.scalars(select(Location)):
            if normalized in {
                row.name.strip().casefold(),
                (row.source_title or "").strip().casefold(),
            }:
                return row.id
        return None
