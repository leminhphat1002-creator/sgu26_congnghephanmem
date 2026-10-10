"""Lớp 1 (Presentation) của module narration (điều phối, thay vai trò Gateway).

Nhiệm vụ: POST /narration/detect nhận GPS và ngôn ngữ, trả kết quả thuyết minh.
Không chứa nghiệp vụ. (Viết ở Tuần 5.)
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["narration"])
