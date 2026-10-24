"""Xác thực phiên quản trị và chống yêu cầu ghi giả mạo."""

import hashlib
import hmac
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.admin.repository import AdminRepository

COOKIE_NAME = "bat_trang_admin"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        # Chỉ chấp nhận đúng origin đã mở giao diện, không tin X-Forwarded-Host.
        if (
            urlsplit(origin).netloc != request.url.netloc
            or urlsplit(origin).scheme != request.url.scheme
        ):
            raise HTTPException(403, "Nguồn yêu cầu không hợp lệ.")


def require_admin(request: Request, db: Annotated[Session, Depends(get_db)]) -> dict:
    token = request.cookies.get(COOKIE_NAME, "")
    if not token or len(token) > 100:
        raise HTTPException(401, "Vui lòng đăng nhập quản trị.")
    identity = AdminRepository(db).identity(token_hash(token))
    if identity is None:
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        if not hmac.compare_digest(
            request.headers.get("x-csrf-token", "").encode(), identity["csrf_token"].encode()
        ):
            raise HTTPException(403, "Thiếu hoặc sai mã xác thực yêu cầu.")
    return identity
