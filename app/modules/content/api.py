"""Lớp 1 (Presentation) của module content.

Nhiệm vụ: endpoint debug xem hoặc vô hiệu hóa cache nội dung theo ngôn ngữ
(GET, DELETE /locations/{id}/narrations/{language}). Không chứa nghiệp vụ. (Viết ở Tuần 4.)
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["content"])
