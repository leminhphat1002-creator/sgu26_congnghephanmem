"""Lớp 1 (Presentation) của module audio.

POST /audio/tts: tạo giọng nói MP3.
GET /audio/{filename}: tải hoặc phát MP3.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.auth import require_admin
from app.modules.audio.schemas import TTSRequest, TTSResponse
from app.modules.audio.service import AudioService
from app.modules.audio.store import AudioStore

router = APIRouter(tags=["audio"])

_FILENAME_PATTERN = re.compile(r"^[0-9a-f]{64}\.mp3$")


async def get_audio_service(request: Request) -> AudioService:
    # Dùng chung khóa và thời gian nghỉ sau lỗi cho mọi yêu cầu trong một app.
    if not hasattr(request.app.state, "audio_service"):
        request.app.state.audio_service = AudioService()
    return request.app.state.audio_service


@router.post("/audio/tts", response_model=TTSResponse, dependencies=[Depends(require_admin)])
async def create_audio(
    request: TTSRequest,
    service: Annotated[AudioService, Depends(get_audio_service)],
):
    try:
        result = await service.synthesize(
            text=request.text,
            lang=request.lang,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    filename = result["audio_filename"]

    return {
        "lang": result["lang"],
        "language": result["language"],
        "voice": result["voice"],
        "text_hash": result["text_hash"],
        "audio_filename": filename,
        "cache_key": result["cache_key"],
        "cache_hit": result["cache_hit"],
        "audio_url": f"/audio/{filename}",
    }


@router.get("/audio/{filename}")
def get_audio(
    filename: str,
    service: Annotated[AudioService, Depends(get_audio_service)],
):
    if not _FILENAME_PATTERN.fullmatch(filename):
        raise HTTPException(
            status_code=422,
            detail="Tên file MP3 không hợp lệ",
        )

    key = filename.removesuffix(".mp3")
    store: AudioStore = service.store

    if not store.exists(key):
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy file âm thanh",
        )

    path = store._get_path(key)

    return FileResponse(
        path=path,
        media_type="audio/mpeg",
        filename=filename,
        content_disposition_type="inline",
    )
