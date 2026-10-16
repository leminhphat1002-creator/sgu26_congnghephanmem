"""Business logic POI: validate GPS, Haversine, tìm địa điểm lân cận."""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.modules.poi.models import Location
from app.modules.poi.repository import LocationRepository
from app.modules.poi.schemas import LocationCreate, NearbyLocation

EARTH_RADIUS_M = 6_371_000.0


def validate_coordinates(latitude: float, longitude: float) -> None:
    if not -90 <= latitude <= 90:
        raise AppError("invalid_latitude", "Vĩ độ phải nằm trong khoảng -90 đến 90.", 422)
    if not -180 <= longitude <= 180:
        raise AppError("invalid_longitude", "Kinh độ phải nằm trong khoảng -180 đến 180.", 422)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoảng cách cung lớn giữa hai tọa độ GPS, trả về mét."""
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)
    p1, p2 = radians(lat1), radians(lat2)
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(min(1.0, a)))


class LocationService:
    def __init__(self, db: Session) -> None:
        self.repo = LocationRepository(db)

    def create(self, data: LocationCreate) -> Location:
        if data.latitude is not None and data.longitude is not None:
            validate_coordinates(data.latitude, data.longitude)
        elif data.latitude is not None or data.longitude is not None:
            raise AppError("incomplete_coordinates", "Phải cung cấp cả latitude và longitude.", 422)
        return self.repo.create(data)

    def list(self, limit: int = 100, offset: int = 0) -> list[Location]:
        return self.repo.list(limit, offset)

    def get(self, location_id: int) -> Location:
        location = self.repo.get(location_id)
        if location is None:
            raise AppError("location_not_found", "Không tìm thấy địa điểm.", 404)
        return location

    def delete(self, location_id: int) -> None:
        self.repo.delete(self.get(location_id))

    def find_nearby(self, latitude: float, longitude: float, search_radius_m: float = 500.0) -> list[NearbyLocation]:
        validate_coordinates(latitude, longitude)
        if not 0 < search_radius_m <= 100_000:
            raise AppError("invalid_radius", "Bán kính tìm kiếm phải lớn hơn 0 và không quá 100000 mét.", 422)

        # Bounding box chỉ giảm số ứng viên; Haversine quyết định khoảng cách chính xác.
        lat_delta = search_radius_m / 111_000
        lon_scale = max(abs(cos(radians(latitude))), 0.01)
        lon_delta = min(180.0, search_radius_m / (111_000 * lon_scale))
        candidates = self.repo.candidates(
            max(-90, latitude - lat_delta), min(90, latitude + lat_delta),
            max(-180, longitude - lon_delta), min(180, longitude + lon_delta),
        )
        found = []
        for item in candidates:
            distance = haversine_distance_m(latitude, longitude, item.latitude, item.longitude)
            if distance <= search_radius_m:
                found.append(NearbyLocation.model_validate(item, from_attributes=True).model_copy(update={"distance_m": round(distance, 2)}))
        return sorted(found, key=lambda item: item.distance_m)

    def choose_activation(self, latitude: float, longitude: float) -> NearbyLocation | None:
        """Chọn địa điểm sẵn sàng nằm trong bán kính kích hoạt riêng của nó."""
        candidates = self.find_nearby(latitude, longitude, 500.0)
        eligible = [item for item in candidates if item.is_ready and item.distance_m <= item.radius]
        return eligible[0] if eligible else None
