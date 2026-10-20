"""Kiểm thử Audio API mà không gọi Edge TTS thật."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.audio.api import get_audio_service
from app.modules.audio.service import AudioService
from app.modules.audio.store import AudioStore


@pytest.fixture
def audio_service(tmp_path, monkeypatch):
    """Tạo AudioService dùng thư mục cache riêng cho test."""
    store = AudioStore(root=tmp_path / "audio_cache")
    service = AudioService(store=store)

    fake_tts = AsyncMock(return_value=b"ID3fake-mp3-data")

    monkeypatch.setattr(
        "app.modules.audio.service.synthesize_mp3",
        fake_tts,
    )

    app.dependency_overrides[get_audio_service] = lambda: service

    yield service, fake_tts

    app.dependency_overrides.pop(get_audio_service, None)


@pytest.fixture
def client(audio_service):
    with TestClient(app) as test_client:
        yield test_client


def test_create_audio_success(client, audio_service):
    """Tạo MP3 thành công."""
    _, fake_tts = audio_service

    response = client.post(
        "/audio/tts",
        json={
            "text": "Xin chào Việt Nam",
            "lang": "vi",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["lang"] == "vi"
    assert data["language"] == "vi"
    assert data["audio_filename"].endswith(".mp3")
    assert data["audio_url"].startswith("/audio/")
    assert data["cache_hit"] is False

    fake_tts.assert_awaited_once()


def test_audio_cache_hit(client, audio_service):
    """Gọi cùng nội dung hai lần chỉ tạo MP3 một lần."""
    _, fake_tts = audio_service

    payload = {
        "text": "Kiểm tra bộ nhớ cache",
        "lang": "vi",
    }

    first = client.post("/audio/tts", json=payload)
    second = client.post("/audio/tts", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200

    assert first.json()["cache_hit"] is False
    assert second.json()["cache_hit"] is True

    assert first.json()["audio_filename"] == second.json()["audio_filename"]

    assert fake_tts.await_count == 1


def test_get_audio_success(client):
    """Lấy file MP3 đã được tạo."""
    created = client.post(
        "/audio/tts",
        json={
            "text": "Kiểm tra tải âm thanh",
            "lang": "vi",
        },
    )

    assert created.status_code == 200

    audio_url = created.json()["audio_url"]
    response = client.get(audio_url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"ID3fake-mp3-data"


def test_create_audio_invalid_language(client):
    """Không chấp nhận ngôn ngữ không hỗ trợ."""
    response = client.post(
        "/audio/tts",
        json={
            "text": "Hello",
            "lang": "xyz",
        },
    )

    assert response.status_code == 422


def test_create_audio_empty_text(client):
    """Không cho phép văn bản rỗng."""
    response = client.post(
        "/audio/tts",
        json={
            "text": "",
            "lang": "vi",
        },
    )

    assert response.status_code == 422


def test_create_audio_too_long(client):
    """Không chấp nhận văn bản vượt 1200 ký tự."""
    response = client.post(
        "/audio/tts",
        json={
            "text": "A" * 1201,
            "lang": "vi",
        },
    )

    assert response.status_code == 422


def test_get_audio_not_found(client):
    """File hợp lệ về tên nhưng không tồn tại."""
    filename = "a" * 64 + ".mp3"

    response = client.get(f"/audio/{filename}")

    assert response.status_code == 404


def test_get_audio_invalid_filename(client):
    """Từ chối tên file không đúng định dạng."""
    response = client.get("/audio/invalid.mp3")

    assert response.status_code == 422


def test_create_audio_tts_unavailable(client, audio_service):
    """Trả về 503 khi dịch vụ TTS gặp lỗi."""
    _, fake_tts = audio_service
    fake_tts.side_effect = RuntimeError("TTS failed")

    response = client.post(
        "/audio/tts",
        json={
            "text": "Kiểm tra lỗi dịch vụ",
            "lang": "vi",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "tts_unavailable"
