"""API đăng nhập và quản trị; chỉ trang đăng nhập được truy cập công khai."""

import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.auth import COOKIE_NAME, check_origin, require_admin, token_hash
from app.core.db import get_db
from app.modules.admin.passwords import hash_password, verify_password
from app.modules.admin.repository import AdminRepository
from app.modules.admin.service import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])
Database = Annotated[Session, Depends(get_db)]
Identity = Annotated[dict, Depends(require_admin)]
_attempts: dict[str, deque] = defaultdict(deque)
_attempt_lock = threading.Lock()
_dummy_hash = hash_password("dummy-password-never-used")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class NarrationInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=900)

    @field_validator("title", "content")
    @classmethod
    def not_blank(cls, value: str):
        if not value.strip():
            raise ValueError("Không được để trống nội dung.")
        return value.strip()


def check_login_limit(request: Request):
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _attempt_lock:
        for old_key in list(_attempts):
            queue = _attempts[old_key]
            while queue and queue[0] < now - 60:
                queue.popleft()
            if not queue:
                del _attempts[old_key]
        queue = _attempts[key]
        if len(queue) >= 5:
            raise HTTPException(429, "Thử quá nhiều lần. Vui lòng chờ 1 phút.")
        queue.append(now)


@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response, db: Database):
    check_origin(request)
    check_login_limit(request)
    repository = AdminRepository(db)
    user = repository.user(data.username.strip())
    valid = verify_password(data.password, user.password_hash if user else _dummy_hash)
    if not user or not valid:
        raise HTTPException(401, "Tên đăng nhập hoặc mật khẩu không đúng.")
    old = request.cookies.get(COOKIE_NAME)
    if old:
        repository.revoke(token_hash(old))
    token, csrf_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    repository.create_session(token_hash(token), user.id, csrf_token)
    repository.record(user.username, "login")
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=8 * 3600,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"username": user.username, "csrf_token": csrf_token}


@router.get("/me")
def me(identity: Identity, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return identity


@router.post("/logout")
def logout(request: Request, response: Response, identity: Identity, db: Database):
    repository = AdminRepository(db)
    repository.revoke(token_hash(request.cookies.get(COOKIE_NAME, "")))
    repository.record(identity["username"], "logout")
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Đã đăng xuất."}


@router.get("/dashboard")
def dashboard(request: Request, identity: Identity, db: Database):
    result = AdminService(AdminRepository(db)).dashboard()
    result.update(request.app.state.visitor_presence.snapshot())
    return result


@router.get("/presence")
def presence(request: Request, identity: Identity):
    return request.app.state.visitor_presence.snapshot()


@router.get("/locations")
def locations(identity: Identity, db: Database):
    return AdminRepository(db).locations()


@router.get("/locations/{location_id}/narrations")
def narrations(location_id: int, identity: Identity, db: Database):
    service = AdminService(AdminRepository(db))
    service.require_location(location_id)
    return service.repository.narrations(location_id)


@router.put("/locations/{location_id}/narrations/{language}")
def save_narration(
    location_id: int,
    language: Literal["vi", "en", "ja"],
    data: NarrationInput,
    identity: Identity,
    db: Database,
):
    AdminService(AdminRepository(db)).save_narration(
        location_id, language, data.title, data.content, identity["username"]
    )
    return {"message": "Đã lưu nội dung thuyết minh."}


@router.delete("/locations/{location_id}/narrations/{language}")
def delete_narration(
    location_id: int, language: Literal["vi", "en", "ja"], identity: Identity, db: Database
):
    service = AdminService(AdminRepository(db))
    service.require_location(location_id)
    if not service.repository.delete_narration(location_id, language):
        raise HTTPException(404, "Chưa có bản thuyết minh này.")
    service.repository.record(identity["username"], "delete_narration", f"{location_id}/{language}")
    return {"message": "Đã xóa bản thuyết minh."}
