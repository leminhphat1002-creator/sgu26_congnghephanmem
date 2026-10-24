"""Kiểm thử nội dung SQLite, ngôn ngữ và dữ liệu lâu dài."""

import asyncio

import pytest
from sqlalchemy.orm import Session

from app.core.db import Base, create_db_engine
from app.modules.content.models import PoiNarration
from app.modules.content.repository import ContentRepository
from app.modules.content.service import ContentService
from app.modules.poi.models import Location


@pytest.fixture
def environment(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'content.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        location = Location(name="Chợ gốm", is_ready=True)
        session.add(location)
        session.flush()
        session.add_all(
            [
                PoiNarration(
                    location_id=location.id,
                    language="vi",
                    title="Chợ gốm",
                    content="Nội dung Việt.",
                ),
                PoiNarration(
                    location_id=location.id,
                    language="en",
                    title="Market",
                    content="English content.",
                ),
            ]
        )
        session.commit()
        yield ContentService(ContentRepository(session)), location.id, session
    engine.dispose()


def test_requested_language_and_title_lookup(environment):
    service, location_id, _ = environment
    result = asyncio.run(service.get_content("  CHỢ GỐM  ", "vi"))
    assert result["extract"] == "Nội dung Việt."
    assert result["fallback_used"] is False
    assert asyncio.run(service.get_location_content(location_id, "en"))["title"] == "Market"


def test_fallback_english_then_vietnamese(environment):
    service, location_id, session = environment
    result = asyncio.run(service.get_location_content(location_id, "ja"))
    assert result["language"] == "en"
    assert result["requested_language"] == "ja"
    assert result["fallback_used"] is True
    for row in session.query(PoiNarration).filter_by(language="en"):
        session.delete(row)
    session.commit()
    assert asyncio.run(service.get_location_content(location_id, "ja"))["language"] == "vi"


def test_missing_content(environment):
    service, _, _ = environment
    assert asyncio.run(service.get_location_content(999)) is None
    assert asyncio.run(service.get_content("missing")) is None


def test_invalid_input(environment):
    service, location_id, _ = environment
    with pytest.raises(ValueError):
        asyncio.run(service.get_content(" "))
    with pytest.raises(ValueError):
        asyncio.run(service.get_location_content(location_id, "fr"))


def test_clean_and_shorten():
    assert ContentService.clean_text(" <b>Xin</b>  chào ") == "Xin chào"
    assert ContentService.shorten_text("Nội dung ngắn.") == "Nội dung ngắn."
    assert len(ContentService.shorten_text("Một câu mô tả. " * 150)) <= 901


def test_cache_invalidation_does_not_delete_curated_content(environment):
    service, location_id, _ = environment
    service.invalidate_content("Chợ gốm")
    assert asyncio.run(service.get_location_content(location_id))["extract"] == "Nội dung Việt."
