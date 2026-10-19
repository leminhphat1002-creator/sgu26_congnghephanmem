"""Lớp 3 (Data Access) của poi.

Nơi duy nhất của poi chạm SQLite: CRUD Location và truy vấn ứng viên theo bounding box.
Model ORM nằm ở models.py cùng thư mục. (Viết ở Tuần 2.)
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.poi.models import Location


def create_location(session: Session, **data) -> Location:
    """Create and persist a location."""
    location = Location(**data)
    session.add(location)
    session.commit()
    session.refresh(location)
    return location


def get_location(session: Session, location_id: int) -> Location | None:
    """Get one location by ID."""
    return session.get(Location, location_id)


def list_locations(session: Session, limit: int = 100) -> list[Location]:
    """List locations ordered by ID."""
    if limit < 1:
        raise ValueError("limit must be positive")

    statement = select(Location).order_by(Location.id).limit(limit)
    return list(session.scalars(statement).all())


def update_location(
    session: Session,
    location_id: int,
    **changes,
) -> Location | None:
    """Update an existing location."""
    location = session.get(Location, location_id)
    if location is None:
        return None

    allowed_fields = {
        "name",
        "description_source",
        "latitude",
        "longitude",
        "radius",
        "source",
        "source_lang",
        "source_title",
        "source_page_id",
        "source_url",
        "last_synced_at",
        "is_ready",
    }

    for field, value in changes.items():
        if field not in allowed_fields:
            raise ValueError(f"Unsupported field: {field}")
        setattr(location, field, value)

    session.commit()
    session.refresh(location)
    return location


def delete_location(session: Session, location_id: int) -> bool:
    """Delete a location. Return False if it does not exist."""
    location = session.get(Location, location_id)
    if location is None:
        return False

    session.delete(location)
    session.commit()
    return True


def find_in_bounding_box(
    session: Session,
    min_latitude: float,
    max_latitude: float,
    min_longitude: float,
    max_longitude: float,
) -> list[Location]:
    """Find GPS-enabled locations inside a bounding box."""
    statement = (
        select(Location)
        .where(
            Location.latitude.is_not(None),
            Location.longitude.is_not(None),
            Location.latitude >= min_latitude,
            Location.latitude <= max_latitude,
            Location.longitude >= min_longitude,
            Location.longitude <= max_longitude,
        )
        .order_by(Location.id)
    )
    return list(session.scalars(statement).all())


def get_location_by_source_page(
    session: Session,
    source_lang: str,
    source_page_id: int,
) -> Location | None:
    """Find a Wikimedia location by source language and page ID."""
    statement = select(Location).where(
        Location.source == "wikimedia",
        Location.source_lang == source_lang,
        Location.source_page_id == source_page_id,
    )
    return session.scalars(statement).first()
