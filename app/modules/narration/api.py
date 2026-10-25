"""Lớp Presentation: API phát hiện và thuyết minh địa điểm."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.admin.repository import AdminRepository
from app.modules.audio.api import get_audio_service
from app.modules.audio.offline import OfflineSpeech
from app.modules.audio.service import AudioService
from app.modules.content.api import get_content_service
from app.modules.content.service import ContentService
from app.modules.narration.schemas import (
    NarrationDetectRequest,
    NarrationDetectResponse,
)
from app.modules.narration.service import NarrationService

router = APIRouter(tags=["narration"])


async def get_offline_speech(
    request: Request, audio: Annotated[AudioService, Depends(get_audio_service)]
) -> OfflineSpeech:
    if not hasattr(request.app.state, "offline_speech"):
        request.app.state.offline_speech = OfflineSpeech(audio.store)
    return request.app.state.offline_speech


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
        result = await service.detect(
            latitude=request.latitude,
            longitude=request.longitude,
            language=request.language,
        )
        AdminRepository(service.session).record(
            "visitor", "narration", str(result.get("location_id") or ""), result["status"]
        )
        return result
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
        result = await service.narrate_location(
            location_id=location_id,
            language=language,
        )
        AdminRepository(service.session).record(
            "visitor", "narration", str(location_id), result["status"]
        )
        return result
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


@router.get("/narration/locations/{location_id}/text", response_model=NarrationDetectResponse)
async def selected_location_text(
    location_id: int,
    service: Annotated[NarrationService, Depends(get_narration_service)],
    language: str = Query(default="vi", pattern="^(vi|en|ja)$"),
):
    """Trả bài viết ngay, không phụ thuộc mạng hoặc dịch vụ tạo giọng đọc."""
    try:
        result = await service.narrate_location(
            location_id=location_id, language=language, include_audio=False
        )
        if result.get("text"):
            version = hashlib.sha256(result["text"].encode()).hexdigest()
            result["stream_url"] = (
                f"/narration/locations/{location_id}/speech?language={language}&version={version}"
            )
            AdminRepository(service.session).record(
                "visitor", "narration", str(location_id), "local"
            )
        return result
    except ValueError as exc:
        status = 404 if str(exc) == "Không tìm thấy địa điểm" else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/narration/locations/{location_id}/speech")
async def stream_selected_speech(
    location_id: int,
    service: Annotated[NarrationService, Depends(get_narration_service)],
    speech: Annotated[OfflineSpeech, Depends(get_offline_speech)],
    language: str = Query(default="vi", pattern="^(vi|en|ja)$"),
    version: str | None = Query(default=None, pattern="^[0-9a-f]{64}$"),
):
    """Phát giọng cục bộ khi nhấn Play, không phải chờ API tạo MP3 qua mạng."""
    try:
        result = await service.narrate_location(location_id, language, include_audio=False)
    except ValueError as exc:
        status = 404 if str(exc) == "Không tìm thấy địa điểm" else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    text = result.get("text")
    if not text:
        raise HTTPException(404, "Không có nội dung thuyết minh")
    if version and version != hashlib.sha256(text.encode()).hexdigest():
        raise HTTPException(409, "Bài viết vừa thay đổi; hãy tải lại bài trước khi nghe.")
    actual_language = result["content_language"]
    key = speech.cache_key(text, actual_language)
    headers = {"X-Audio-Engine": "piper-local", "Cache-Control": "no-store"}
    if speech.store.exists(key):
        return FileResponse(speech.store._get_path(key), media_type="audio/mpeg", headers=headers)
    await asyncio.to_thread(speech.check, actual_language)
    return StreamingResponse(
        speech.stream_async(text, actual_language), media_type="audio/mpeg", headers=headers
    )


@router.get("/narration/nearby")
async def discover_nearby_pois(
    service: Annotated[
        NarrationService,
        Depends(get_narration_service),
    ],
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
):
    """Tìm POI trong SQLite trong bán kính 500m."""
    return await service.discover_nearby_locations(latitude, longitude)


@router.get("/narration/catalog")
def narration_catalog(
    service: Annotated[NarrationService, Depends(get_narration_service)],
):
    """Danh sách tham quan từ xa, không yêu cầu GPS."""
    return service.list_catalog()
