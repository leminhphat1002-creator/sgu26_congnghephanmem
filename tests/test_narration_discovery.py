"""Khám phá POI chỉ đọc SQLite, không tạo địa điểm từ Internet."""

import asyncio
from math import degrees
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.db import Base, create_db_engine
from app.modules.content.models import PoiNarration
from app.modules.narration.service import NarrationService
from app.modules.poi.models import Location
from app.modules.poi.service import EARTH_RADIUS_METERS


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


def test_nearby_is_sorted_and_filters_unpublished_and_beyond_500_meters(environment):
    service, session, content = environment
    latitude, longitude = 20.9784, 105.9146
    locations = [
        Location(
            name=name,
            latitude=latitude + degrees(distance / EARTH_RADIUS_METERS),
            longitude=longitude,
            is_ready=is_ready,
        )
        for name, distance, is_ready in [
            ("Ngoài vùng", 501, True),
            ("Ranh giới", 500, True),
            ("Trong vùng", 499, True),
            ("Gần", 0, True),
            ("Ẩn", 0, False),
        ]
    ]
    session.add_all(locations)
    session.flush()
    session.add_all(
        PoiNarration(
            location_id=location.id, language="vi", title=location.name, content="Nội dung"
        )
        for location in locations
    )
    session.add(Location(name="Chưa có bài", latitude=latitude, longitude=longitude, is_ready=True))
    session.commit()
    result = asyncio.run(service.discover_nearby_locations(latitude, longitude))
    assert [item["location"]["name"] for item in result] == ["Gần", "Trong vùng", "Ranh giới"]
    assert [item["distance_meters"] for item in result] == [0, 499, 500]
    assert result[0]["should_activate"] is True
    content.search_nearby.assert_not_awaited()
    assert session.query(Location).count() == 6


def test_far_away_does_not_discover_or_synthesize(environment):
    service, session, content = environment
    assert asyncio.run(service.discover_nearby_locations(0, 0)) == []
    assert asyncio.run(service.detect(0, 0))["status"] == "no_location"
    assert session.query(Location).count() == 0
    content.search_nearby.assert_not_awaited()
