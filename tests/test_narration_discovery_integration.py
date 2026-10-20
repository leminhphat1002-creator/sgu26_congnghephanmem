"""Kiểm thử tích hợp Narration với POI Discovery và SQLite."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base, create_db_engine, get_db
from app.main import app
from app.modules.narration.api import get_narration_service
from app.modules.narration.service import NarrationService
from app.modules.poi.models import Location  # noqa: F401


@pytest.fixture
def environment(tmp_path) -> Iterator[dict]:
    """Tạo SQLite riêng và mock các dịch vụ bên ngoài."""
    database_url = f"sqlite:///{(tmp_path / 'integration.db').as_posix()}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(bind=engine)

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    content = MagicMock()
    content.search_nearby = AsyncMock(
        return_value=[
            {
                "pageid": 123456,
                "title": "Dinh Độc Lập",
                "lat": 10.7769,
                "lon": 106.6955,
            }
        ]
    )
    content.get_content = AsyncMock(
        return_value={
            "extract": "Dinh Độc Lập là một di tích lịch sử.",
            "language": "vi",
            "fallback_used": False,
        }
    )

    audio = MagicMock()
    audio.synthesize = AsyncMock(
        return_value={
            "audio_filename": "test.mp3",
            "cache_hit": False,
        }
    )

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    def override_narration_service() -> Iterator[NarrationService]:
        with session_factory() as session:
            yield NarrationService(
                session=session,
                content_service=content,
                audio_service=audio,
            )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_narration_service] = override_narration_service

    try:
        with TestClient(app) as client:
            yield {
                "client": client,
                "session_factory": session_factory,
                "content": content,
                "audio": audio,
            }
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_narration_service, None)
        engine.dispose()


def test_detect_discovers_and_creates_audio(environment):
    """SQLite trống -> Wikimedia -> SQLite -> Audio."""
    client = environment["client"]

    response = client.post(
        "/narration/detect",
        json={
            "latitude": 10.7769,
            "longitude": 106.6955,
            "language": "vi",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["location_name"] == "Dinh Độc Lập"
    assert data["content_language"] == "vi"
    assert data["audio_url"] == "/audio/test.mp3"

    with environment["session_factory"]() as session:
        locations = session.query(Location).all()

        assert len(locations) == 1
        assert locations[0].source == "wikimedia"
        assert locations[0].source_page_id == 123456

    environment["content"].search_nearby.assert_awaited_once()
    environment["audio"].synthesize.assert_awaited_once()


def test_detect_reuses_discovered_location(environment):
    """Lần thứ hai sử dụng POI SQLite, không tạo trùng."""
    client = environment["client"]

    payload = {
        "latitude": 10.7769,
        "longitude": 106.6955,
        "language": "vi",
    }

    first = client.post("/narration/detect", json=payload)
    second = client.post("/narration/detect", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "success"
    assert second.json()["status"] == "success"

    assert first.json()["location_id"] == second.json()["location_id"]

    with environment["session_factory"]() as session:
        assert session.query(Location).count() == 1

    # Discovery chỉ được gọi ở request đầu tiên.
    assert environment["content"].search_nearby.await_count == 1


def test_detect_discovery_outside_radius(environment):
    """Không kích hoạt POI Wikimedia cách GPS hơn 80 mét."""
    client = environment["client"]

    environment["content"].search_nearby.return_value = [
        {
            "pageid": 654321,
            "title": "Địa điểm xa",
            "lat": 10.7789,
            "lon": 106.6955,
        }
    ]

    response = client.post(
        "/narration/detect",
        json={
            "latitude": 10.7769,
            "longitude": 106.6955,
            "language": "vi",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "no_location"

    with environment["session_factory"]() as session:
        assert session.query(Location).count() == 0

    environment["audio"].synthesize.assert_not_awaited()
