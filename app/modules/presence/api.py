"""Tín hiệu khách công khai, số liệu chỉ dành cho người quản lý."""

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.auth import check_origin
from app.modules.presence.service import COOKIE_NAME

router = APIRouter(prefix="/api/presence", tags=["presence"])


@router.post("/heartbeat", status_code=204)
def heartbeat(request: Request, response: Response):
    check_origin(request)
    try:
        token = request.app.state.visitor_presence.heartbeat(request.cookies.get(COOKIE_NAME))
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
