"""Lớp 1 (Presentation) của module poi.

Nhiệm vụ: nhận request, validate đầu vào, gọi service, trả response và mã lỗi HTTP cho
/locations, /locations/nearby, /locations/discover. Không chứa nghiệp vụ, không truy cập
CSDL, không gọi HTTP ra ngoài. (Viết ở Tuần 4.)
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["poi"])
