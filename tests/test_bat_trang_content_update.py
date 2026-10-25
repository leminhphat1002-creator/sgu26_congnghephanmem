"""Replace only shipped placeholders, preserving edited content and POI identity."""

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
