"""DTO cho API và ranh giới giữa các lớp của module POI."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description_source: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius: float = Field(default=80.0, gt=0, le=100_000)
    is_ready: bool = False


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description_source: str | None
    latitude: float | None
    longitude: float | None
    radius: float
    source: str
    source_lang: str | None
    source_title: str | None
    source_page_id: int | None
    source_url: str | None
    is_ready: bool


class NearbyLocation(LocationRead):
    distance_m: float


class NearbyResponse(BaseModel):
    items: list[NearbyLocation]
    count: int
    latitude: float
    longitude: float
    search_radius_m: float
