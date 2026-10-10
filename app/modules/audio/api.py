"""Lớp 1 (Presentation) của module audio.

Nhiệm vụ: POST /audio/tts và GET /audio/{filename} (MP3, cùng origin với ứng dụng).
Không chứa nghiệp vụ, không gọi edge_tts trực tiếp. (Viết ở Tuần 4.)
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["audio"])
