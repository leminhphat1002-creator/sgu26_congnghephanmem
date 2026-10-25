"""Nạp bài biên soạn Bát Tràng; giữ chỉnh sửa riêng, chỉ thay đúng bài mẫu cũ.

Chạy: python -m scripts.seed_bat_trang (sau alembic upgrade head).
CLI sao lưu SQLite trước khi ghi. Tọa độ vẫn là dữ liệu minh họa, chưa khảo sát.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_sessionmaker
from app.modules.content.models import PoiNarration
from app.modules.poi.models import Location
from scripts.database_snapshot import snapshot

CONTENT_FILE = Path(__file__).parent / "content" / "bat_trang_narrations.json"


def load_content() -> dict:
    data = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    for poi in data["pois"]:
        if set(poi["narrations"]) != {"vi", "en", "ja"}:
            raise ValueError("Each POI must contain vi, en and ja narrations")
        for row in poi["narrations"].values():
            if not row["content"].strip() or len(row["content"]) > 900:
                raise ValueError("Narrations must contain 1–900 characters")
    return data


def fingerprint(title: str, content: str) -> str:
    return hashlib.sha256((title + "\0" + content).encode()).hexdigest()


def seed(session: Session) -> dict[str, int]:
    """Một giao dịch: thêm bài thiếu, nâng cấp đúng mẫu cũ, giữ bài đã biên tập."""
    data = load_content()
    counts = {"created": 0, "upgraded": 0, "preserved": 0}
    for poi in data["pois"]:
        location = session.scalar(
            select(Location).where(
                Location.source == "bat_trang_demo", Location.name == poi["name"]
            )
        )
        if location is None:
            location = Location(
                name=poi["name"],
                latitude=poi["latitude"],
                longitude=poi["longitude"],
                radius=80,
                source="bat_trang_demo",
                is_ready=True,
            )
            session.add(location)
            session.flush()
        if location.description_source in {
            None,
            "Dữ liệu demo — tọa độ và nội dung cần xác minh.",
        }:
            location.description_source = poi["description"]
        if not location.source_url:
            location.source_url = poi["sources"][0]["url"]
        for language, row in poi["narrations"].items():
            existing = session.scalar(
                select(PoiNarration).where(
                    PoiNarration.location_id == location.id, PoiNarration.language == language
                )
            )
            if existing is None:
                session.add(PoiNarration(location_id=location.id, language=language, **row))
                counts["created"] += 1
            elif fingerprint(existing.title, existing.content) == poi["legacy"][language]:
                existing.title = row["title"]
                existing.content = row["content"]
                counts["upgraded"] += 1
            else:
                counts["preserved"] += 1
    session.commit()
    return counts


def main() -> None:
    # Validate the entire file before creating a backup or changing the database.
    load_content()
    with get_sessionmaker()() as session:
        url = session.get_bind().url
        if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
            database = Path(url.database).resolve()
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            backup = database.parent / "backups" / f"before-narrations-{stamp}.db"
            if snapshot(database, backup):
                print(f"Backup: {backup}")
        print(json.dumps(seed(session)))


if __name__ == "__main__":
    main()
