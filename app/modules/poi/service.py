"""Lớp 2 (Business) của poi.

Nhiệm vụ: Haversine, find_nearby, choose_activation (radius kích hoạt mặc định 80m),
discover (hỏi SQLite trước, thiếu thì nhờ module content), validate tọa độ.
Không biết FastAPI Request/Response. (Viết ở Tuần 2-3.)
"""
from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.modules.poi import repository
from app.modules.poi.models import Location

EARTH_RADIUS_METERS = 6_371_000
DEFAULT_RADIUS_METERS = 80.0
DEFAULT_SEARCH_RADIUS_METERS = 500.0


def haversine(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    """Calculate the distance between two GPS coordinates in meters."""
    for latitude in (latitude1, latitude2):
        if not -90 <= latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90")

    for longitude in (longitude1, longitude2):
        if not -180 <= longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180")

    lat1, lon1, lat2, lon2 = map(radians, (latitude1, longitude1, latitude2, longitude2))

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    a = min(1.0, max(0.0, a))

    return 2 * EARTH_RADIUS_METERS * asin(sqrt(a))


def choose_activation(
    distance_meters: float,
    radius_meters: float = DEFAULT_RADIUS_METERS,
) -> bool:
    """Return whether the user is inside the POI activation radius."""
    if distance_meters < 0:
        raise ValueError("Distance cannot be negative")
    if radius_meters <= 0:
        raise ValueError("Activation radius must be positive")

    return distance_meters <= radius_meters


def find_nearby(
    session: Session,
    latitude: float,
    longitude: float,
    search_radius_meters: float = DEFAULT_SEARCH_RADIUS_METERS,
) -> list[tuple[Location, float]]:
    """Find GPS-enabled POIs within the search radius, nearest first."""
    # Validate GPS even when the database contains no locations.
    haversine(latitude, longitude, latitude, longitude)

    if search_radius_meters <= 0:
        raise ValueError("Search radius must be positive")

    latitude_delta = search_radius_meters / 111_000
    cosine_latitude = max(abs(cos(radians(latitude))), 1e-6)
    longitude_delta = min(
        180.0,
        search_radius_meters / (111_000 * cosine_latitude),
    )

    min_latitude = max(-90.0, latitude - latitude_delta)
    max_latitude = min(90.0, latitude + latitude_delta)
    min_longitude = max(-180.0, longitude - longitude_delta)
    max_longitude = min(180.0, longitude + longitude_delta)

    candidates = repository.find_in_bounding_box(
        session,
        min_latitude,
        max_latitude,
        min_longitude,
        max_longitude,
    )

    nearby: list[tuple[Location, float]] = []
    for location in candidates:
        # GPS coordinates may be NULL for manually entered locations.
        if location.latitude is None or location.longitude is None:
            continue

        distance = haversine(
            latitude,
            longitude,
            location.latitude,
            location.longitude,
        )
        if distance <= search_radius_meters:
            nearby.append((location, distance))

    return sorted(nearby, key=lambda item: item[1])
