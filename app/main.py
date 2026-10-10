"""Điểm vào của ứng dụng: tạo FastAPI, đăng ký router. Không chứa logic nghiệp vụ."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.health import router as health_router
from app.core.logging import setup_logging
from app.modules.audio.api import router as audio_router
from app.modules.content.api import router as content_router
from app.modules.narration.api import router as narration_router
from app.modules.poi.api import router as poi_router


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="Thuyết minh tự động đa ngôn ngữ",
        version="0.1.0",
        description="Modular monolith 1 service, kiến trúc 3 lớp (đồ án CNPM).",
    )
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(poi_router)
    app.include_router(content_router)
    app.include_router(audio_router)
    app.include_router(narration_router)
    return app


app = create_app()
