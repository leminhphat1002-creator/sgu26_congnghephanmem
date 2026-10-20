"""Kiểm thử nghiệp vụ điều phối NarrationService."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.narration import service as narration_module
from app.modules.narration.service import NarrationService


@pytest.fixture
def setup_service(monkeypatch):
    """Tạo service giả lập, không gọi API ngoài."""
    session = MagicMock()

    content_service = MagicMock()
    content_service.get_content = AsyncMock()
    content_service.search_nearby = AsyncMock(return_value=[])

    audio_service = MagicMock()
    audio_service.synthesize = AsyncMock()

    service = NarrationService(
        session=session,
        content_service=content_service,
        audio_service=audio_service,
    )

    # Danh sách POI giả lập do test tự điều khiển.
    nearby_mock = MagicMock(return_value=[])
    monkeypatch.setattr(
        narration_module,
        "find_nearby",
        nearby_mock,
    )

    return service, content_service, audio_service, nearby_mock


def make_location(
    location_id=1,
    name="Dinh Độc Lập",
    radius=80,
    is_ready=True,
):
    """Tạo địa điểm mẫu."""
    return SimpleNamespace(
        id=location_id,
        name=name,
        source_title=name,
        radius=radius,
        is_ready=is_ready,
    )


def test_detect_success(setup_service):
    """Có POI hợp lệ, tạo được nội dung và MP3."""
    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(), 20.0)]

    content.get_content.return_value = {
        "extract": "Nội dung thuyết minh Dinh Độc Lập.",
        "language": "vi",
        "fallback_used": False,
    }

    audio.synthesize.return_value = {
        "audio_filename": "example.mp3",
        "cache_hit": False,
    }

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "success"
    assert result["location_id"] == 1
    assert result["distance_meters"] == 20.0
    assert result["audio_url"] == "/audio/example.mp3"
    assert result["cache_hit"] is False

    content.get_content.assert_awaited_once_with(
        title="Dinh Độc Lập",
        lang="vi",
    )
    audio.synthesize.assert_awaited_once_with(
        text="Nội dung thuyết minh Dinh Độc Lập.",
        lang="vi",
    )


def test_detect_no_location(setup_service):
    """Không có POI gần GPS thì không gọi Wikimedia/TTS."""
    service, content, audio, nearby = setup_service

    nearby.return_value = []

    result = asyncio.run(service.detect(0, 0, "vi"))

    assert result["status"] == "no_location"
    content.get_content.assert_not_awaited()
    audio.synthesize.assert_not_awaited()


def test_detect_outside_activation_radius(setup_service):
    """POI nằm ngoài bán kính kích hoạt."""
    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(radius=80), 150.0)]

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "no_location"
    content.get_content.assert_not_awaited()
    audio.synthesize.assert_not_awaited()


def test_detect_no_content(setup_service):
    """Có POI nhưng không tìm thấy nội dung Wikimedia."""
    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(), 10.0)]
    content.get_content.return_value = None

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "no_content"
    assert result["location_id"] == 1
    audio.synthesize.assert_not_awaited()


def test_detect_skips_not_ready_location(setup_service):
    """Bỏ qua POI chưa sẵn sàng và chọn POI hợp lệ tiếp theo."""
    service, content, audio, nearby = setup_service

    nearby.return_value = [
        (make_location(location_id=1, is_ready=False), 5.0),
        (make_location(location_id=2, name="Địa điểm B"), 20.0),
    ]

    content.get_content.return_value = {
        "extract": "Thông tin địa điểm B.",
        "language": "vi",
        "fallback_used": False,
    }

    audio.synthesize.return_value = {
        "audio_filename": "location_b.mp3",
        "cache_hit": True,
    }

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "success"
    assert result["location_id"] == 2
    assert result["location_name"] == "Địa điểm B"
    assert result["cache_hit"] is True


def test_detect_language_fallback(setup_service):
    """TTS dùng ngôn ngữ nội dung thực tế khi fallback."""
    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(), 10.0)]

    content.get_content.return_value = {
        "extract": "English narration text.",
        "language": "en",
        "fallback_used": True,
    }

    audio.synthesize.return_value = {
        "audio_filename": "english.mp3",
        "cache_hit": False,
    }

    result = asyncio.run(service.detect(10.7769, 106.6955, "ja"))

    assert result["status"] == "success"
    assert result["requested_language"] == "ja"
    assert result["content_language"] == "en"
    assert result["fallback_used"] is True

    audio.synthesize.assert_awaited_once_with(
        text="English narration text.",
        lang="en",
    )


def test_detect_content_timeout(setup_service):
    """Wikimedia timeout thì không gọi Edge TTS."""
    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(), 10.0)]

    content.get_content.side_effect = TimeoutError()

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "no_content"
    audio.synthesize.assert_not_awaited()


def test_detect_tts_unavailable(setup_service):
    """Edge TTS bị lỗi thì vẫn trả nội dung văn bản."""
    from app.core.exceptions import AppError

    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(), 10.0)]

    content.get_content.return_value = {
        "extract": "Nội dung thuyết minh.",
        "language": "vi",
        "fallback_used": False,
    }

    audio.synthesize.side_effect = AppError(
        "tts_unavailable",
        "Không thể tạo MP3",
        503,
    )

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "text_only"
    assert result["text"] == "Nội dung thuyết minh."
    assert result["audio_url"] is None


def test_detect_content_upstream_error(setup_service):
    """Wikimedia bị lỗi upstream thì trả no_content."""
    from app.core.exceptions import AppError

    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(), 10.0)]

    content.get_content.side_effect = AppError(
        "upstream_error",
        "Wikimedia không khả dụng",
        502,
    )

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "no_content"
    audio.synthesize.assert_not_awaited()


def test_detect_real_content_timeout(setup_service, monkeypatch):
    """Kiểm tra timeout thật khi Wikimedia phản hồi chậm."""
    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(), 10.0)]

    monkeypatch.setattr(service, "CONTENT_TIMEOUT_SECONDS", 0.01)

    async def slow_content(*args, **kwargs):
        await asyncio.sleep(0.1)
        return None

    content.get_content.side_effect = slow_content

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "no_content"
    audio.synthesize.assert_not_awaited()


def test_detect_real_audio_timeout(setup_service, monkeypatch):
    """Kiểm tra timeout thật khi Edge TTS phản hồi chậm."""
    service, content, audio, nearby = setup_service

    nearby.return_value = [(make_location(), 10.0)]

    content.get_content.return_value = {
        "extract": "Nội dung thuyết minh Dinh Độc Lập.",
        "language": "vi",
        "fallback_used": False,
    }

    monkeypatch.setattr(service, "AUDIO_TIMEOUT_SECONDS", 0.01)

    async def slow_audio(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {"audio_filename": "test.mp3", "cache_hit": False}

    audio.synthesize.side_effect = slow_audio

    result = asyncio.run(service.detect(10.7769, 106.6955, "vi"))

    assert result["status"] == "text_only"
    assert result["text"] == "Nội dung thuyết minh Dinh Độc Lập."
    assert result["audio_url"] is None
