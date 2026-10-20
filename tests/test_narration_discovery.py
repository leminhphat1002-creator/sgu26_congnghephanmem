"""Kiểm thử POI Discovery từ Wikimedia sang SQLite."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, create_db_engine
from app.modules.narration.service import NarrationService
from app.modules.poi import repository as poi_repository
from app.modules.poi.models import Location


@pytest.fixture
def discovery_environment(tmp_path):
    """Dùng SQLite tạm và Wikimedia giả lập."""
    database_url = f"sqlite:///{(tmp_path / 'discovery.db').as_posix()}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(bind=engine)

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    with session_factory() as session:
        content_service = MagicMock()
        content_service.search_nearby = AsyncMock(return_value=[])

        audio_service = MagicMock()

        service = NarrationService(
            session=session,
            content_service=content_service,
            audio_service=audio_service,
        )

        yield service, session, content_service

    engine.dispose()


def wikipedia_poi(latitude=10.7769, longitude=106.6955):
    """Kết quả Geosearch giả lập."""
    return {
        "pageid": 123456,
        "title": "Dinh Độc Lập",
        "lat": latitude,
        "lon": longitude,
    }


def test_discover_new_location(discovery_environment):
    """Tìm thấy POI mới và lưu vào SQLite."""
    service, session, content = discovery_environment

    content.search_nearby.return_value = [wikipedia_poi()]

    result = asyncio.run(
        service.discover_location(
            latitude=10.7769,
            longitude=106.6955,
            language="vi",
        )
    )

    assert result is not None
    assert result.name == "Dinh Độc Lập"
    assert result.source == "wikimedia"
    assert result.source_page_id == 123456
    assert result.is_ready is True

    saved = poi_repository.get_location(
        session,
        result.id,
    )

    assert saved is not None
    assert saved.name == "Dinh Độc Lập"

    content.search_nearby.assert_awaited_once_with(
        latitude=10.7769,
        longitude=106.6955,
        radius=500,
        limit=20,
        lang="vi",
    )


def test_discover_outside_activation_radius(discovery_environment):
    """Không lưu POI nằm ngoài bán kính 80 mét."""
    service, session, content = discovery_environment

    # Lệch khoảng 222 mét theo vĩ độ.
    content.search_nearby.return_value = [wikipedia_poi(latitude=10.7789)]

    result = asyncio.run(
        service.discover_location(
            latitude=10.7769,
            longitude=106.6955,
            language="vi",
        )
    )

    assert result is None

    assert session.query(Location).count() == 0


def test_discover_existing_location_no_duplicate(
    discovery_environment,
):
    """POI Wikimedia đã tồn tại thì không tạo trùng."""
    service, session, content = discovery_environment

    existing = poi_repository.create_location(
        session,
        name="Dinh Độc Lập",
        latitude=10.7769,
        longitude=106.6955,
        radius=80.0,
        source="wikimedia",
        source_lang="vi",
        source_title="Dinh Độc Lập",
        source_page_id=123456,
        is_ready=True,
    )

    content.search_nearby.return_value = [wikipedia_poi()]

    result = asyncio.run(
        service.discover_location(
            latitude=10.7769,
            longitude=106.6955,
            language="vi",
        )
    )

    assert result is not None
    assert result.id == existing.id

    # SQLite vẫn chỉ có một địa điểm.
    assert session.query(Location).count() == 1
