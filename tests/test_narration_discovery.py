"""Khám phá POI chỉ đọc SQLite, không tạo địa điểm từ Internet."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.db import Base, create_db_engine
from app.modules.narration.service import NarrationService
from app.modules.poi.models import Location


@pytest.fixture
def environment(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'nearby.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        content = MagicMock()
        content.search_nearby = AsyncMock(side_effect=AssertionError("Không được gọi Wikipedia"))
        service = NarrationService(session, content, MagicMock())
        yield service, session, content
    engine.dispose()


def test_nearby_is_sorted_and_filters_unready(environment):
    service, session, content = environment
    session.add_all(
        [
            Location(name="Xa", latitude=20.980, longitude=105.9146, is_ready=True),
            Location(name="Gần", latitude=20.9784, longitude=105.9146, is_ready=True),
            Location(name="Ẩn", latitude=20.9784, longitude=105.9146, is_ready=False),
            Location(name="Ngoài vùng", latitude=21.1, longitude=105.9146, is_ready=True),
        ]
    )
    session.commit()
    result = asyncio.run(service.discover_nearby_locations(20.9784, 105.9146))
    assert [item["location"]["name"] for item in result] == ["Gần", "Xa"]
    assert result[0]["should_activate"] is True
    content.search_nearby.assert_not_awaited()
    assert session.query(Location).count() == 4


def test_far_away_does_not_discover_or_synthesize(environment):
    service, session, content = environment
    assert asyncio.run(service.discover_nearby_locations(0, 0)) == []
    assert asyncio.run(service.detect(0, 0))["status"] == "no_location"
    assert session.query(Location).count() == 0
    content.search_nearby.assert_not_awaited()
