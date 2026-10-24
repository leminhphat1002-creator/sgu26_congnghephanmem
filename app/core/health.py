"""Router GET /health, tách khỏi main.py để main không chứa logic."""

from __future__ import annotations

import os

from fastapi import APIRouter, Response

router = APIRouter(tags=["health"])


@router.get("/health", summary="Kiểm tra service còn sống")
def health(response: Response) -> dict[str, str]:
    response.headers["X-App-Revision"] = os.environ.get("APP_REVISION", "development")
    return {"status": "ok"}
