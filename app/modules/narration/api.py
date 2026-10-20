"""Lớp Presentation: API phát hiện và thuyết minh địa điểm."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import AppError
from app.modules.audio.api import get_audio_service
from app.modules.audio.service import AudioService
from app.modules.content.api import get_content_service
from app.modules.content.service import ContentService
from app.modules.narration.schemas import (
    NarrationDetectRequest,
    NarrationDetectResponse,
)
from app.modules.narration.service import NarrationService
from app.modules.poi.schemas import LocationRead
from app.modules.poi.service import choose_activation, find_nearby

router = APIRouter(tags=["narration"])
logger = logging.getLogger(__name__)


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


@router.post(
    "/narration/locations/{location_id}",
    response_model=NarrationDetectResponse,
)
async def narrate_selected_location(
    location_id: int,
    service: Annotated[
        NarrationService,
        Depends(get_narration_service),
    ],
    language: str = Query(default="vi", pattern="^(vi|en|ja)$"),
):
    """Thuyết minh địa điểm do người dùng chọn."""

    try:
        return await service.narrate_location(
            location_id=location_id,
            language=language,
        )
    except ValueError as exc:
        message = str(exc)

        if message == "Không tìm thấy địa điểm":
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=422,
            detail=message,
        ) from exc


@router.get("/narration/nearby")
async def discover_nearby_pois(
    service: Annotated[
        NarrationService,
        Depends(get_narration_service),
    ],
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
):
    """Tìm nhiều POI Wikimedia, dự phòng bằng SQLite nếu lỗi."""

    try:
        return await service.discover_nearby_locations(
            latitude=latitude,
            longitude=longitude,
        )

    except (TimeoutError, AppError) as exc:
        logger.warning(
            "Wikimedia Discovery thất bại: %s: %s",
            type(exc).__name__,
            exc,
        )

        # Wikimedia lỗi vẫn trả các POI đã lưu trong SQLite.
        nearby = find_nearby(
            session=service.session,
            latitude=latitude,
            longitude=longitude,
            search_radius_meters=500,
        )

        return [
            {
                "location": LocationRead.model_validate(location).model_dump(),
                "distance_meters": round(distance, 2),
                "should_activate": choose_activation(
                    distance,
                    location.radius,
                ),
            }
            for location, distance in nearby
        ]
