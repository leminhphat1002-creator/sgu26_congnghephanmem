"""Kiểm thử POST /narration/detect."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.narration.api import get_narration_service


@pytest.fixture
def mock_service():
    """Mock NarrationService, không gọi Wikipedia hay Edge TTS."""
    service = MagicMock()
    service.detect = AsyncMock()

    app.dependency_overrides[get_narration_service] = lambda: service

    yield service

    app.dependency_overrides.pop(get_narration_service, None)


@pytest.fixture
def client(mock_service):
    with TestClient(app) as test_client:
        yield test_client


def test_detect_success(client, mock_service):
    """GPS hợp lệ và phát hiện được địa điểm."""
    mock_service.detect.return_value = {
        "status": "success",
        "location_id": 6,
        "location_name": "Dinh Độc Lập",
        "distance_meters": 0.0,
        "requested_language": "vi",
        "content_language": "vi",
        "fallback_used": False,
        "text": "Dinh Độc Lập là một di tích lịch sử.",
        "audio_url": "/audio/test.mp3",
        "cache_hit": False,
        "message": "Tạo thuyết minh thành công.",
    }

    response = client.post(
        "/narration/detect",
        json={
            "latitude": 10.7769,
            "longitude": 106.6955,
            "language": "vi",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["location_id"] == 6
    assert response.json()["content_language"] == "vi"
    assert response.json()["audio_url"] == "/audio/test.mp3"

    mock_service.detect.assert_awaited_once_with(
        latitude=10.7769,
        longitude=106.6955,
        language="vi",
    )


def test_detect_no_location(client, mock_service):
    """Không tìm thấy địa điểm gần GPS."""
    mock_service.detect.return_value = {
        "status": "no_location",
        "requested_language": "vi",
        "message": "Không tìm thấy địa điểm phù hợp.",
    }

    response = client.post(
        "/narration/detect",
        json={
            "latitude": 0,
            "longitude": 0,
            "language": "vi",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "no_location"
    assert response.json()["audio_url"] is None


def test_detect_no_content(client, mock_service):
    """Có địa điểm nhưng không tìm được nội dung."""
    mock_service.detect.return_value = {
        "status": "no_content",
        "location_id": 6,
        "location_name": "Dinh Độc Lập",
        "distance_meters": 0,
        "requested_language": "vi",
        "message": "Không tìm thấy nội dung thuyết minh.",
    }

    response = client.post(
        "/narration/detect",
        json={
            "latitude": 10.7769,
            "longitude": 106.6955,
            "language": "vi",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "no_content"
    assert response.json()["audio_url"] is None


def test_detect_invalid_latitude(client, mock_service):
    """Latitude ngoài khoảng -90 đến 90."""
    response = client.post(
        "/narration/detect",
        json={
            "latitude": 100,
            "longitude": 106.6955,
            "language": "vi",
        },
    )

    assert response.status_code == 422
    mock_service.detect.assert_not_awaited()


def test_detect_invalid_longitude(client, mock_service):
    """Longitude ngoài khoảng -180 đến 180."""
    response = client.post(
        "/narration/detect",
        json={
            "latitude": 10.7769,
            "longitude": 200,
            "language": "vi",
        },
    )

    assert response.status_code == 422
    mock_service.detect.assert_not_awaited()


def test_detect_invalid_language(client, mock_service):
    """Từ chối ngôn ngữ không được hỗ trợ."""
    response = client.post(
        "/narration/detect",
        json={
            "latitude": 10.7769,
            "longitude": 106.6955,
            "language": "fr",
        },
    )

    assert response.status_code == 422
    mock_service.detect.assert_not_awaited()


def test_detect_default_language(client, mock_service):
    """Mặc định sử dụng tiếng Việt khi không truyền language."""
    mock_service.detect.return_value = {
        "status": "no_location",
        "requested_language": "vi",
    }

    response = client.post(
        "/narration/detect",
        json={
            "latitude": 10.7769,
            "longitude": 106.6955,
        },
    )

    assert response.status_code == 200
    mock_service.detect.assert_awaited_once_with(
        latitude=10.7769,
        longitude=106.6955,
        language="vi",
    )
