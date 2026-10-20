"""Lớp 1 (Presentation) của module content."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.content.repository import ContentRepository
from app.modules.content.service import ContentService

router = APIRouter(tags=["content"])


def get_content_service(
    db: Annotated[Session, Depends(get_db)],
) -> ContentService:
    repository = ContentRepository(db)
    return ContentService(repository=repository)


@router.get("/content")
async def get_content(
    title: Annotated[str, Query(min_length=1)],
    service: Annotated[ContentService, Depends(get_content_service)],
    lang: str = "vi",
):
    try:
        result = await service.get_content(title, lang)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nội dung Wikimedia",
        )

    return result


@router.delete("/content/cache")
def invalidate_content_cache(
    title: Annotated[str, Query(min_length=1)],
    service: Annotated[ContentService, Depends(get_content_service)],
    lang: str | None = None,
):
    if lang is not None and lang not in ContentService.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail="Ngôn ngữ không được hỗ trợ",
        )

    deleted_count = service.invalidate_content(title, lang)

    return {
        "message": "Đã xử lý yêu cầu xóa cache",
        "deleted_count": deleted_count,
    }
