"""Lớp 1 (Presentation) của module content."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.db import get_db
from app.modules.content.repository import ContentRepository
from app.modules.content.service import ContentService
from app.modules.poi import repository as poi_repository

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
            detail="Không tìm thấy nội dung thuyết minh",
        )

    return result


@router.delete("/content/cache", dependencies=[Depends(require_admin)])
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


@router.get("/locations/{location_id}/narrations/{language}")
def get_location_narration_cache(
    location_id: int,
    language: str,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[ContentService, Depends(get_content_service)],
):
    """Xem cache nội dung của một địa điểm."""
    if language not in ContentService.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail="Ngôn ngữ không được hỗ trợ",
        )

    location = poi_repository.get_location(session, location_id)

    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy địa điểm",
        )

    title = location.source_title or location.name
    cached = service.get_cached_content(title, language)

    if cached is None:
        raise HTTPException(
            status_code=404,
            detail="Địa điểm chưa có cache nội dung cho ngôn ngữ này",
        )

    return {
        "location_id": location.id,
        "location_name": location.name,
        **cached,
    }


@router.delete(
    "/locations/{location_id}/narrations/{language}", dependencies=[Depends(require_admin)]
)
def delete_location_narration_cache(
    location_id: int,
    language: str,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[ContentService, Depends(get_content_service)],
):
    """Xóa cache nội dung theo địa điểm và ngôn ngữ."""
    if language not in ContentService.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail="Ngôn ngữ không được hỗ trợ",
        )

    location = poi_repository.get_location(session, location_id)

    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy địa điểm",
        )

    title = location.source_title or location.name
    deleted_count = service.invalidate_content(title, language)

    return {
        "location_id": location.id,
        "language": language,
        "deleted_count": deleted_count,
        "message": "Đã xử lý yêu cầu xóa cache nội dung",
    }
