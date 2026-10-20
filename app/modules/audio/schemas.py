"""Schema yêu cầu và kết quả của Audio API."""

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    lang: str = "vi"


class TTSResponse(BaseModel):
    lang: str
    language: str
    voice: str
    text_hash: str
    audio_filename: str
    cache_key: str
    cache_hit: bool
    audio_url: str
