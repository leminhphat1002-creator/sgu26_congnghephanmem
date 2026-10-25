"""Replace only shipped placeholders, preserving edited content and POI identity."""

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import Base, create_db_engine
from app.modules.content.models import PoiNarration
from app.modules.content.service import ContentService
from app.modules.poi.models import Location
from scripts.seed_bat_trang import load_content, seed


def test_upgrade_keeps_edited_translations_coordinates_and_is_repeatable(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'guide.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        location = Location(
            name="Chợ gốm Bát Tràng",
            source="bat_trang_demo",
            latitude=20.9,
            longitude=105.9,
            is_ready=True,
        )
        session.add(location)
        session.flush()
        legacy = PoiNarration(
            location_id=location.id,
            language="vi",
            title=location.name,
            content=(
                "Chợ gốm là điểm dừng trong hành trình khám phá Bát Tràng. Hãy quan sát hình "
                "dáng, màu men và hoa văn trên các sản phẩm để cảm nhận sự đa dạng của đồ gốm. "
                "Khi mua hàng, bạn nên hỏi người bán về chất liệu, cách sử dụng và cách đóng "
                "gói. Đây là bài thuyết minh mẫu phục vụ đồ án. "
            ),
        )
        edited = PoiNarration(
            location_id=location.id, language="en", title="My title", content="My own narration"
        )
        session.add_all([legacy, edited])
        session.commit()
        result = seed(session)
        assert result == {"created": 13, "upgraded": 1, "preserved": 1}
        assert "tháng 10 năm 2004" in legacy.content
        assert (edited.title, edited.content) == ("My title", "My own narration")
        assert (location.latitude, location.longitude) == (20.9, 105.9)
        assert session.scalar(select(func.count()).select_from(Location)) == 5
        assert session.scalar(select(func.count()).select_from(PoiNarration)) == 15
        assert seed(session) == {"created": 0, "upgraded": 0, "preserved": 15}
    engine.dispose()


def test_all_curated_narrations_fit_without_runtime_truncation():
    data = load_content()
    assert len(data["pois"]) == 5
    for poi in data["pois"]:
        assert poi["sources"]
        for row in poi["narrations"].values():
            assert ContentService.shorten_text(row["content"]) == row["content"]


def previous_catalog(session):
    fixture = Path(__file__).parent / "fixtures" / "bat_trang_catalog_v1.json"
    previous = json.loads(fixture.read_text(encoding="utf-8"))
    locations = []
    for poi in previous["pois"]:
        location = Location(
            name=poi["name"],
            description_source=poi["description"],
            latitude=poi["latitude"],
            longitude=poi["longitude"],
            source="bat_trang_demo",
            source_url=poi["sources"][0]["url"],
            is_ready=True,
        )
        session.add(location)
        session.flush()
        for language, article in poi["narrations"].items():
            session.add(PoiNarration(location_id=location.id, language=language, **article))
        locations.append(location)
    session.commit()
    return locations


def test_catalog_upgrade_corrects_stock_gps_and_replaces_themes_without_duplicates(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'catalog.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        old = previous_catalog(session)
        ids = [row.id for row in old]
        # Administrator changes remain authoritative even after a subsequent seed.
        old[0].latitude, old[0].longitude = 20.974, 105.913
        old[0].description_source = "My own description"
        old[0].source_url = "https://example.org/my-source"
        edited = session.scalar(
            select(PoiNarration).where(
                PoiNarration.location_id == old[0].id, PoiNarration.language == "en"
            )
        )
        edited.content = "My own edited guide"
        session.commit()
        result = seed(session)
        assert result == {"created": 0, "upgraded": 6, "preserved": 9}
        assert (old[0].latitude, old[0].longitude) == (20.974, 105.913)
        assert old[0].description_source == "My own description"
        assert old[0].source_url == "https://example.org/my-source"
        assert edited.content == "My own edited guide"
        for location, poi in zip(old[1:], load_content()["pois"][1:], strict=True):
            assert location.name == poi["name"]
            assert (location.latitude, location.longitude) == (poi["latitude"], poi["longitude"])
            assert location.source_title == poi["key"]
        assert [row.id for row in session.scalars(select(Location).order_by(Location.id))] == ids
        assert seed(session) == {"created": 0, "upgraded": 0, "preserved": 15}
        assert session.scalar(select(func.count()).select_from(PoiNarration)) == 15
    engine.dispose()


def test_edited_experience_stop_is_not_silently_renamed_to_pagoda(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'edited.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        old = previous_catalog(session)
        article = session.scalar(
            select(PoiNarration).where(
                PoiNarration.location_id == old[-1].id, PoiNarration.language == "vi"
            )
        )
        article.content = "An administrator's own workshop content"
        session.commit()
        with pytest.raises(ValueError, match="Edited thematic stop"):
            seed(session)
        session.rollback()
        assert old[-1].name == "Không gian trải nghiệm làm gốm"
        assert article.content == "An administrator's own workshop content"
        assert session.scalar(select(func.count()).select_from(Location)) == 5
    engine.dispose()
