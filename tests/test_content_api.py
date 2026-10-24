"""Kiểm thử Content API."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_admin
from app.main import app
from app.modules.content.api import get_content_service


@pytest.fixture
def mock_service():
    """Thay ContentService thật bằng mock để không gọi Wikipedia."""
    service = MagicMock()
    service.get_content = AsyncMock()
    service.invalidate_content = MagicMock()

    app.dependency_overrides[get_content_service] = lambda: service

    yield service

    app.dependency_overrides.pop(get_content_service, None)


@pytest.fixture
def client(mock_service):
    with TestClient(app) as test_client:
        yield test_client


def test_get_content_success(client, mock_service):
    """Lấy nội dung thành công."""
    mock_service.get_content.return_value = {
        "title": "Dinh Độc Lập",
        "extract": "Dinh Độc Lập nằm tại Thành phố Hồ Chí Minh.",
        "url": "https://vi.wikipedia.org/wiki/Dinh_Độc_Lập",
        "language": "vi",
        "requested_language": "vi",
        "fallback_used": False,
    }

    response = client.get(
        "/content",
        params={"title": "Dinh Độc Lập", "lang": "vi"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Dinh Độc Lập"
    assert response.json()["language"] == "vi"

    mock_service.get_content.assert_awaited_once_with("Dinh Độc Lập", "vi")


def test_get_content_not_found(client, mock_service):
    """Không tìm thấy nội dung Wikimedia."""
    mock_service.get_content.return_value = None

    response = client.get(
        "/content",
        params={"title": "DiaDiemKhongTonTai", "lang": "vi"},
    )

    assert response.status_code == 404


def test_get_content_invalid_language(client, mock_service):
    """Ngôn ngữ không hợp lệ."""
    mock_service.get_content.side_effect = ValueError("Ngôn ngữ chưa được hỗ trợ: xyz")

    response = client.get(
        "/content",
        params={"title": "Dinh Độc Lập", "lang": "xyz"},
    )

    assert response.status_code == 422


def test_get_content_missing_title(client):
    """Thiếu tên địa điểm."""
    response = client.get(
        "/content",
        params={"lang": "vi"},
    )

    assert response.status_code == 422


def test_delete_content_cache(client, mock_service):
    """Xóa cache thành công."""
    mock_service.invalidate_content.return_value = 1

    response = client.delete(
        "/content/cache",
        params={"title": "Dinh Độc Lập", "lang": "vi"},
    )

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1

    mock_service.invalidate_content.assert_called_once_with("Dinh Độc Lập", "vi")


def test_delete_content_cache_invalid_language(client):
    """Không chấp nhận ngôn ngữ không hỗ trợ."""
    response = client.delete(
        "/content/cache",
        params={"title": "Dinh Độc Lập", "lang": "xyz"},
    )

    assert response.status_code == 422


def test_delete_content_cache_all_languages(client, mock_service):
    """Xóa cache của tất cả ngôn ngữ cho một trang."""
    mock_service.invalidate_content.return_value = 2

    response = client.delete(
        "/content/cache",
        params={"title": "Dinh Độc Lập"},
    )

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2

    mock_service.invalidate_content.assert_called_once_with("Dinh Độc Lập", None)


@pytest.fixture(autouse=True)
def authorized_api_requests():
    app.dependency_overrides[require_admin] = lambda: {"username": "api-test"}
    yield
    app.dependency_overrides.pop(require_admin, None)
