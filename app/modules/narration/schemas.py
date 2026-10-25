"""Schema request/response cho Narration API Tuần 5."""

from pydantic import BaseModel, Field


class NarrationDetectRequest(BaseModel):
    """Dữ liệu GPS và ngôn ngữ từ người dùng."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    language: str = Field(default="vi", pattern="^(vi|en|ja)$")


class NarrationDetectResponse(BaseModel):
    """Kết quả thuyết minh tự động."""

    status: str
    location_id: int | None = None
    location_name: str | None = None
    distance_meters: float | None = None

    requested_language: str
    content_language: str | None = None
    fallback_used: bool = False

    text: str | None = None
    audio_url: str | None = None
    stream_url: str | None = None
    cache_hit: bool | None = None
    message: str | None = None
