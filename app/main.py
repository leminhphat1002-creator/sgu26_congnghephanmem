"""Điểm vào ứng dụng FastAPI và giao diện demo GPS."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.health import router as health_router
from app.core.logging import setup_logging
from app.modules.audio.api import router as audio_router
from app.modules.content.api import router as content_router
from app.modules.narration.api import router as narration_router
from app.modules.poi.api import router as poi_router

STATIC_DIR = Path(__file__).resolve().parent / "static"
FRONTEND_DIR = STATIC_DIR / "app"


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="Thuyết minh tự động đa ngôn ngữ",
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

    return app


app = create_app()
