"""Thêm các POI mẫu vào database; chạy lặp lại không tạo bản ghi trùng."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.poi.models import Location

SAMPLE_POIS = [
    {
        "name": "Chợ Bến Thành",
        "description_source": "Địa điểm tham quan tại trung tâm TP. Hồ Chí Minh.",
        "latitude": 10.7725,
        "longitude": 106.6980,
        "radius": 80.0,
        "source": "manual",
        "is_ready": True,
    },
    {
        "name": "Nhà thờ Đức Bà Sài Gòn",
        "description_source": "Nhà thờ nổi tiếng tại trung tâm TP. Hồ Chí Minh.",
        "latitude": 10.7798,
        "longitude": 106.6990,
        "radius": 80.0,
        "source": "manual",
        "is_ready": True,
    },
    {
        "name": "Dinh Độc Lập",
        "description_source": "Di tích lịch sử tại TP. Hồ Chí Minh.",
        "latitude": 10.7770,
        "longitude": 106.6953,
        "radius": 80.0,
        "source": "manual",
        "is_ready": True,
    },
]


def main() -> None:
    """Insert missing sample POIs."""
    session_factory = get_sessionmaker()

    with session_factory() as session:
        inserted = 0
        skipped = 0

        for data in SAMPLE_POIS:
            existing = session.scalar(
                select(Location).where(
                    Location.name == data["name"],
                    Location.source == "manual",
                )
            )

            if existing is not None:
                print(f"Đã tồn tại, bỏ qua: {data['name']}")
                skipped += 1
                continue

            session.add(Location(**data))
            print(f"Đã thêm: {data['name']}")
            inserted += 1

        session.commit()

    print(f"Hoàn tất seed POI: thêm {inserted}, bỏ qua {skipped}.")


if __name__ == "__main__":
    main()
