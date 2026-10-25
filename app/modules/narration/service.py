"""Điều phối địa điểm và nội dung SQLite với dịch vụ tạo MP3."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.audio.service import AudioService
from app.modules.content.service import ContentService
from app.modules.poi import repository as poi_repository
from app.modules.poi.service import (
    choose_activation,
    find_nearby,
)

logger = logging.getLogger(__name__)


class NarrationService:
    """Điều phối quá trình thuyết minh tự động."""

    CONTENT_TIMEOUT_SECONDS = 12
    AUDIO_TIMEOUT_SECONDS = 20

    SEARCH_RADIUS_METERS = 500

    def __init__(
        self,
        session: Session,
        content_service: ContentService,
        audio_service: AudioService,
    ) -> None:
        self.session = session
        self.content_service = content_service
        self.audio_service = audio_service

    async def detect(
        self,
        latitude: float,
        longitude: float,
        language: str = "vi",
    ) -> dict[str, Any]:
        """Phát hiện POI, lấy nội dung và tạo thuyết minh."""

        if language not in ContentService.SUPPORTED_LANGUAGES:
            raise ValueError("Ngôn ngữ không được hỗ trợ")

        # 1. Tìm các POI có sẵn trong SQLite.
        nearby = find_nearby(
            session=self.session,
            latitude=latitude,
            longitude=longitude,
            search_radius_meters=self.SEARCH_RADIUS_METERS,
        )

        selected_location = None
        selected_distance = None

        # 2. Chọn POI gần nhất đủ điều kiện kích hoạt.
        for location, distance in nearby:
            if not location.is_ready:
                continue

            if choose_activation(distance, location.radius):
                selected_location = location
                selected_distance = distance
                break

        if selected_location is None:
            return {
                "status": "no_location",
                "requested_language": language,
                "message": ("Không tìm thấy địa điểm đủ điều kiện " "kích hoạt thuyết minh."),
            }

        location_id = selected_location.id
        location_name = selected_location.name
        distance_meters = round(selected_distance, 2)

        # Tên dùng trong thông báo và nhật ký.
        title = selected_location.source_title or location_name

        # Lấy nội dung biên soạn theo ID địa điểm.
        try:
            content = await asyncio.wait_for(
                self.content_service.get_location_content(
                    location_id=location_id,
                    lang=language,
                ),
                timeout=self.CONTENT_TIMEOUT_SECONDS,
            )

        except TimeoutError:
            logger.warning(
                "Hết thời gian chờ database: %s",
                title,
            )

            return {
                "status": "no_content",
                "location_id": location_id,
                "location_name": location_name,
                "distance_meters": distance_meters,
                "requested_language": language,
                "message": ("Hết thời gian chờ nội dung database."),
            }

        except AppError as exc:
            logger.warning(
                "database lỗi với %s: %s",
                title,
                exc.code,
            )

            return {
                "status": "no_content",
                "location_id": location_id,
                "location_name": location_name,
                "distance_meters": distance_meters,
                "requested_language": language,
                "message": ("Dịch vụ nội dung đang gặp sự cố."),
            }

        # 6. Có POI nhưng không có nội dung thuyết minh.
        if content is None:
            return {
                "status": "no_content",
                "location_id": location_id,
                "location_name": location_name,
                "distance_meters": distance_meters,
                "requested_language": language,
                "message": ("Không tìm thấy nội dung thuyết minh."),
            }

        text = content["extract"]
        content_language = content["language"]

        # 7. Chuẩn bị kết quả thuyết minh văn bản.
        result = {
            "status": "success",
            "location_id": location_id,
            "location_name": location_name,
            "distance_meters": distance_meters,
            "requested_language": language,
            "content_language": content_language,
            "fallback_used": content.get(
                "fallback_used",
                False,
            ),
            "text": text,
            "audio_url": None,
            "cache_hit": None,
            "message": "Tạo thuyết minh thành công.",
        }

        # 8. Tạo MP3 hoặc lấy lại MP3 đã cache.
        try:
            audio = await asyncio.wait_for(
                self.audio_service.synthesize(
                    text=text,
                    lang=content_language,
                ),
                timeout=self.AUDIO_TIMEOUT_SECONDS,
            )

        except (TimeoutError, AppError) as exc:
            logger.warning(
                "Không thể tạo MP3 cho %s: %s",
                title,
                exc,
            )

            result["status"] = "text_only"
            result["message"] = "Đã lấy nội dung, nhưng hiện " "chưa tạo được âm thanh."

            return result

        # 9. Trả nội dung cùng đường dẫn phát MP3.
        result["audio_url"] = f"/audio/{audio['audio_filename']}"
        result["cache_hit"] = audio["cache_hit"]

        return result

    async def narrate_location(
        self,
        location_id: int,
        language: str = "vi",
        *,
        include_audio: bool = True,
    ) -> dict[str, Any]:
        """Thuyết minh địa điểm người dùng chọn theo ID, không cần kích hoạt GPS."""
        if language not in ContentService.SUPPORTED_LANGUAGES:
            raise ValueError("Ngôn ngữ không được hỗ trợ")

        location = poi_repository.get_location(self.session, location_id)
        if location is None:
            raise ValueError("Không tìm thấy địa điểm")
        if not location.is_ready:
            raise ValueError("Địa điểm chưa sẵn sàng thuyết minh")

        result = {
            "location_id": location.id,
            "location_name": location.name,
            "distance_meters": None,
            "requested_language": language,
        }

        try:
            content = await asyncio.wait_for(
                self.content_service.get_location_content(location_id=location.id, lang=language),
                timeout=self.CONTENT_TIMEOUT_SECONDS,
            )
        except (TimeoutError, AppError) as exc:
            logger.warning("Không thể lấy nội dung POI %s: %s", location_id, exc)
            content = None

        if content is None:
            return {
                **result,
                "status": "no_content",
                "message": "Không có nội dung thuyết minh.",
            }

        text = content["extract"]
        content_language = content["language"]
        result.update(
            status="success",
            content_language=content_language,
            fallback_used=content.get("fallback_used", False),
            text=text,
            audio_url=None,
            cache_hit=None,
            message="Đã tạo nội dung thuyết minh.",
        )

        # Nội dung SQLite trả ngay; giao diện chuẩn bị giọng đọc ở yêu cầu riêng.
        if not include_audio:
            return result

        try:
            audio = await asyncio.wait_for(
                self.audio_service.synthesize(text=text, lang=content_language),
                timeout=self.AUDIO_TIMEOUT_SECONDS,
            )
        except (TimeoutError, AppError) as exc:
            logger.warning("Không thể tạo MP3 cho POI %s: %s", location_id, exc)
            result["status"] = "text_only"
            result["message"] = "Có văn bản nhưng chưa tạo được MP3."
            return result

        result["audio_url"] = f"/audio/{audio['audio_filename']}"
        result["cache_hit"] = audio["cache_hit"]
        return result

    async def discover_nearby_locations(
        self,
        latitude: float,
        longitude: float,
    ) -> list[dict[str, Any]]:
        """Tìm địa điểm sẵn sàng trong SQLite, không khám phá từ Internet."""
        nearby = find_nearby(self.session, latitude, longitude, self.SEARCH_RADIUS_METERS)
        from app.modules.poi.schemas import LocationRead

        return [
            {
                "location": LocationRead.model_validate(location).model_dump(),
                "distance_meters": round(distance, 2),
                "should_activate": choose_activation(distance, location.radius),
            }
            for location, distance in nearby
            if location.is_ready
        ]

    def list_catalog(self) -> list[dict]:
        from app.modules.poi.schemas import LocationRead

        return [
            {
                "location": LocationRead.model_validate(location).model_dump(),
                "distance_meters": None,
                "should_activate": False,
            }
            for location in poi_repository.list_narratable_locations(self.session)
        ]
