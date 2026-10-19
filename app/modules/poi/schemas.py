"""Lớp 1 (Presentation): schema (DTO) của poi.

Dùng cho đầu vào/đầu ra của API và cho dữ liệu đi qua ranh giới giữa các lớp. Không trả
thẳng model ORM ra ngoài lớp Data Access. (Viết ở Tuần 2.)
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocationCreate(BaseModel):
    """Validate data when creating a location."""

    name: str = Field(min_length=1, max_length=255)
    description_source: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius: float = Field(default=80.0, gt=0)
    source: str = "manual"
    source_lang: str | None = None
    source_title: str | None = None
    source_page_id: int | None = None
    source_url: str | None = None
    is_ready: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value


class LocationUpdate(BaseModel):
    """Validate fields that can be updated."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description_source: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius: float | None = Field(default=None, gt=0)
    source: str | None = None
    source_lang: str | None = None
    source_title: str | None = None
    source_page_id: int | None = None
    source_url: str | None = None
    is_ready: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Name cannot be empty")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value


class LocationRead(BaseModel):
    """Represent a location returned by the application."""

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
    source_page_id: str | None
    source_url: str | None
    is_ready: bool
