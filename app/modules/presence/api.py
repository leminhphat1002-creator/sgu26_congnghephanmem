"""Tín hiệu khách công khai, số liệu chỉ dành cho người quản lý."""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.auth import check_origin
from app.modules.presence.service import COOKIE_NAME

router = APIRouter(prefix="/api/presence", tags=["presence"])


class SharedLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90, strict=True, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, strict=True, allow_inf_nan=False)


class HeartbeatUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: SharedLocation | None


@router.post("/heartbeat", status_code=204)
async def heartbeat(request: Request, response: Response):
    check_origin(request)
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 1024:
            raise HTTPException(413, "Dữ liệu phiên khách quá lớn.")
        body.extend(chunk)
    try:
        update = HeartbeatUpdate.model_validate_json(body) if body else None
    except ValidationError as exc:
        raise HTTPException(422, "Vị trí chia sẻ không hợp lệ.") from exc
    location = update.location if update else None
    try:
        token = request.app.state.visitor_presence.heartbeat(
            request.cookies.get(COOKIE_NAME),
            location=(location.latitude, location.longitude) if location else None,
            update_location=update is not None,
        )
    except OverflowError as exc:
        raise HTTPException(429, "Tạm thời chưa cập nhật được trạng thái truy cập.") from exc
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/api/presence",
    )
    response.headers["Cache-Control"] = "no-store"
