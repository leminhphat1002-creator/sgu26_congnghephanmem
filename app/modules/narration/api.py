"""Lớp Presentation: API phát hiện và thuyết minh địa điểm."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.audio.api import get_audio_service
from app.modules.audio.service import AudioService
from app.modules.content.api import get_content_service
from app.modules.content.service import ContentService
from app.modules.narration.schemas import (
    NarrationDetectRequest,
    NarrationDetectResponse,
)
from app.modules.narration.service import NarrationService

router = APIRouter(tags=["narration"])


def get_narration_service(
    session: Annotated[Session, Depends(get_db)],
    content_service: Annotated[ContentService, Depends(get_content_service)],
    audio_service: Annotated[AudioService, Depends(get_audio_service)],
) -> NarrationService:
    """Khởi tạo dịch vụ điều phối các module."""
    return NarrationService(
        session=session,
        content_service=content_service,
        audio_service=audio_service,
    )


@router.post(
    "/narration/detect",
    response_model=NarrationDetectResponse,
)
async def detect_narration(
    request: NarrationDetectRequest,
    service: Annotated[NarrationService, Depends(get_narration_service)],
):
    """Nhận GPS và ngôn ngữ, trả về kết quả thuyết minh."""
    try:
        return await service.detect(
            latitude=request.latitude,
            longitude=request.longitude,
            language=request.language,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
