"""Data Access: thao tác SQLite cho Location."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.poi.models import Location
from app.modules.poi.schemas import LocationCreate


class LocationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: LocationCreate) -> Location:
        location = Location(**data.model_dump(), source="manual")
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    def get(self, location_id: int) -> Location | None:
        return self.db.get(Location, location_id)

    def list(self, limit: int = 100, offset: int = 0) -> list[Location]:
        stmt = select(Location).order_by(Location.id).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def delete(self, location: Location) -> None:
        self.db.delete(location)
        self.db.commit()

    def candidates(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> list[Location]:
        stmt = select(Location).where(
            Location.latitude.is_not(None),
            Location.longitude.is_not(None),
            Location.latitude >= min_lat,
            Location.latitude <= max_lat,
            Location.longitude >= min_lon,
            Location.longitude <= max_lon,
        )
        return list(self.db.scalars(stmt).all())
