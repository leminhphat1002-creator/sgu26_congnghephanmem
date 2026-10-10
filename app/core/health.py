"""Router GET /health, tách khỏi main.py để main không chứa logic."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Kiểm tra service còn sống")
def health() -> dict[str, str]:
    return {"status": "ok"}
