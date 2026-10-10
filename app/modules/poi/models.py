"""Lớp 3 (Data Access): model ORM Location.

Chỉ repository.py được dùng model này; các lớp trên làm việc với schema (DTO).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        # Trong SQLite, NULL được coi là khác nhau nên bản ghi nhập tay (source_page_id NULL)
        # không bị ràng buộc này chặn; chỉ bài Wikimedia trùng nhau mới bị từ chối.
        UniqueConstraint("source", "source_lang", "source_page_id", name="uq_location_source"),
    )

    # Khóa nội bộ tự tăng, không phụ thuộc id bài Wikimedia.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description_source: Mapped[str | None] = mapped_column(Text, nullable=True)

    # NULL cho bản ghi nhập tay chưa có GPS (không gán 0,0); loại khỏi phát hiện tự động.
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Bán kính kích hoạt (mét), mặc định 80 (cấu hình demo).
    radius: Mapped[float] = mapped_column(Float, nullable=False, default=80.0, server_default="80")

    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual", server_default="manual"
    )
    source_lang: Mapped[str | None] = mapped_column(String(8), nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_page_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_ready: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
