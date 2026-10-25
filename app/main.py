"""Điểm vào ứng dụng FastAPI và giao diện demo GPS."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.health import router as health_router
from app.core.logging import setup_logging
from app.modules.admin.api import router as admin_router
from app.modules.audio.api import router as audio_router
from app.modules.content.api import router as content_router
from app.modules.narration.api import router as narration_router
from app.modules.poi.api import router as poi_router
from app.modules.sharing.api import router as sharing_router

STATIC_DIR = Path(__file__).resolve().parent / "static"
FRONTEND_DIR = STATIC_DIR / "app"


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="Bát Tràng Audio Guide",
        version="0.1.0",
        description="Modular monolith 1 service, kiến trúc 3 lớp.",
    )

    register_exception_handlers(app)

    # Đăng ký các API hiện có.
    app.include_router(health_router)
    app.include_router(poi_router)
    app.include_router(content_router)
    app.include_router(audio_router)
    app.include_router(narration_router)
    app.include_router(admin_router)
    app.include_router(sharing_router)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Map tiles require an origin Referer; admin/API responses keep the stricter policy.
        response.headers["Referrer-Policy"] = (
            "strict-origin-when-cross-origin" if request.url.path == "/" else "same-origin"
        )
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path == "/" or request.url.path.startswith("/static/app/"):
            response.headers["Cache-Control"] = "no-cache"
        if request.url.path.startswith(("/admin", "/api/admin")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                "form-action 'self'; base-uri 'self'"
            )
        return response

    # Phục vụ CSS, JavaScript và các tài nguyên tĩnh.
    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )

    # Trang giao diện demo GPS.
    @app.get("/", include_in_schema=False)
    def frontend():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/admin", include_in_schema=False)
    def admin_frontend():
        return FileResponse(STATIC_DIR / "admin" / "index.html")

    @app.get("/share", include_in_schema=False)
    def share_frontend():
        return FileResponse(FRONTEND_DIR / "share.html")

    return app


app = create_app()
