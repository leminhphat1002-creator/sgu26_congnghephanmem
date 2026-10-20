"""Lớp Business của Narration: điều phối POI, Content và Audio.

Quy trình:
1. Nhận GPS và ngôn ngữ.
2. Tìm POI trong SQLite.
3. Nếu chưa có POI phù hợp, tìm từ Wikimedia Geosearch.
4. Kiểm tra bán kính kích hoạt.
5. Lấy nội dung Wikimedia hoặc cache SQLite.
6. Tạo MP3 bằng Edge TTS hoặc lấy từ cache.
7. Trả kết quả thuyết minh.
"""

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
    haversine,
)

logger = logging.getLogger(__name__)


class NarrationService:
    """Điều phối quá trình thuyết minh tự động."""

    CONTENT_TIMEOUT_SECONDS = 12
    AUDIO_TIMEOUT_SECONDS = 20

    SEARCH_RADIUS_METERS = 500
    ACTIVATION_RADIUS_METERS = 80
    DISCOVERY_LIMIT = 20

    def __init__(
        self,
        session: Session,
        content_service: ContentService,
        audio_service: AudioService,
    ) -> None:
        self.session = session
        self.content_service = content_service
        self.audio_service = audio_service

    async def discover_location(
        self,
        latitude: float,
        longitude: float,
        language: str = "vi",
    ) -> Any | None:
        """Tìm và lưu POI Wikimedia khi SQLite chưa có POI phù hợp."""

        # 1. Tìm các bài Wikipedia có tọa độ gần GPS.
        results = await asyncio.wait_for(
            self.content_service.search_nearby(
                latitude=latitude,
                longitude=longitude,
                radius=self.SEARCH_RADIUS_METERS,
                limit=self.DISCOVERY_LIMIT,
                lang=language,
            ),
            timeout=self.CONTENT_TIMEOUT_SECONDS,
        )

        candidates = []

        # 2. Kiểm tra dữ liệu và tính khoảng cách thực tế.
        for item in results:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            page_id = item.get("pageid")
            poi_latitude = item.get("lat")
            poi_longitude = item.get("lon")

            if (
                not isinstance(title, str)
                or not title.strip()
                or not isinstance(page_id, int)
                or isinstance(page_id, bool)
                or not isinstance(poi_latitude, int | float)
                or isinstance(poi_latitude, bool)
                or not isinstance(poi_longitude, int | float)
                or isinstance(poi_longitude, bool)
            ):
                continue

            try:
                distance = haversine(
                    latitude,
                    longitude,
                    float(poi_latitude),
                    float(poi_longitude),
                )
            except ValueError:
                continue

            # Chỉ chọn địa điểm trong bán kính kích hoạt.
            if not choose_activation(
                distance,
                self.ACTIVATION_RADIUS_METERS,
            ):
                continue

            candidates.append((distance, item))

        # 3. Ưu tiên địa điểm gần GPS nhất.
        candidates.sort(key=lambda candidate: candidate[0])

        # 4. Kiểm tra trùng và lưu vào SQLite nếu cần.
        for _, item in candidates:
            page_id = item["pageid"]

            existing = poi_repository.get_location_by_source_page(
                self.session,
                source_lang=language,
                source_page_id=page_id,
            )

            if existing is not None:
                if (
                    existing.is_ready
                    and existing.latitude is not None
                    and existing.longitude is not None
                ):
                    distance = haversine(
                        latitude,
                        longitude,
                        existing.latitude,
                        existing.longitude,
                    )

                    if choose_activation(
                        distance,
                        existing.radius,
                    ):
                        return existing

                continue

            location = poi_repository.create_location(
                self.session,
                name=item["title"],
                latitude=float(item["lat"]),
                longitude=float(item["lon"]),
                radius=self.ACTIVATION_RADIUS_METERS,
                source="wikimedia",
                source_lang=language,
                source_title=item["title"],
                source_page_id=page_id,
                is_ready=True,
            )

            logger.info(
                "Đã khám phá POI Wikimedia: id=%s, title=%s",
                location.id,
                location.name,
            )

            return location

        return None

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

        # 3. Nếu SQLite không có POI phù hợp, thử Wikimedia.
        if selected_location is None:
            try:
                discovered = await self.discover_location(
                    latitude=latitude,
                    longitude=longitude,
                    language=language,
                )
            except (TimeoutError, AppError) as exc:
                logger.warning(
                    "Không thể khám phá POI từ Wikimedia: %s",
                    exc,
                )
                discovered = None

            if discovered is not None:
                selected_location = discovered
                selected_distance = haversine(
                    latitude,
                    longitude,
                    discovered.latitude,
                    discovered.longitude,
                )

        # 4. Không tìm thấy POI trong SQLite và Wikimedia.
        if selected_location is None:
            return {
                "status": "no_location",
                "requested_language": language,
                "message": ("Không tìm thấy địa điểm đủ điều kiện " "kích hoạt thuyết minh."),
            }

        location_id = selected_location.id
        location_name = selected_location.name
        distance_meters = round(selected_distance, 2)

        # Ưu tiên tiêu đề gốc từ Wikimedia.
        title = selected_location.source_title or location_name

        # 5. Lấy nội dung Wikipedia hoặc cache SQLite.
        try:
            content = await asyncio.wait_for(
                self.content_service.get_content(
                    title=title,
                    lang=language,
                ),
                timeout=self.CONTENT_TIMEOUT_SECONDS,
            )

        except TimeoutError:
            logger.warning(
                "Hết thời gian chờ Wikimedia: %s",
                title,
            )

            return {
                "status": "no_content",
                "location_id": location_id,
                "location_name": location_name,
                "distance_meters": distance_meters,
                "requested_language": language,
                "message": ("Hết thời gian chờ nội dung Wikimedia."),
            }

        except AppError as exc:
            logger.warning(
                "Wikimedia lỗi với %s: %s",
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
