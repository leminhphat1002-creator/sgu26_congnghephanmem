"""Nạp bài biên soạn Bát Tràng; giữ chỉnh sửa riêng, chỉ thay đúng bài mẫu cũ.

Chạy: python -m scripts.seed_bat_trang (sau alembic upgrade head).
CLI sao lưu SQLite trước khi ghi. Vị trí tham khảo trực tuyến, chưa khảo sát thực địa.
"""

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import get_sessionmaker
from app.modules.content.models import PoiNarration
from app.modules.poi.models import Location
from scripts.database_snapshot import snapshot

CONTENT_FILE = Path(__file__).parent / "content" / "bat_trang_narrations.json"


def load_content() -> dict:
    data = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    keys = set()
    for poi in data["pois"]:
        if poi["key"] in keys:
            raise ValueError("Duplicate catalog key")
        keys.add(poi["key"])
        lat, lon = poi["latitude"], poi["longitude"]
        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
            and 20.965 < lat < 20.995
            and 105.900 < lon < 105.930
        ):
            raise ValueError("Catalog coordinate outside the Bat Trang map")
        reference = poi["coordinate_reference"]
        if reference["field_surveyed"] or not reference["source_url"].startswith("https://"):
            raise ValueError("Expected a sourced online reference, not a field survey")
        if set(poi["narrations"]) != {"vi", "en", "ja"}:
            raise ValueError("Each POI must contain vi, en and ja narrations")
        for row in poi["narrations"].values():
            if not row["content"].strip() or len(row["content"]) > 900:
                raise ValueError("Narrations must contain 1–900 characters")
    return data


def fingerprint(title: str, content: str) -> str:
    return hashlib.sha256((title + "\0" + content).encode()).hexdigest()


def known_narration(poi: dict, row: PoiNarration) -> bool:
    hashes = poi["legacy"].get(row.language, [])
    if isinstance(hashes, str):
        hashes = [hashes]
    current = poi["narrations"].get(row.language)
    if current:
        hashes = [*hashes, fingerprint(current["title"], current["content"])]
    return fingerprint(row.title, row.content) in hashes


def seed(session: Session) -> dict[str, int]:
    """Một giao dịch: thêm bài thiếu, nâng cấp đúng mẫu cũ, giữ bài đã biên tập."""
    data = load_content()
    counts = {"created": 0, "upgraded": 0, "preserved": 0}
    for poi in data["pois"]:
        previous = poi.get("previous_locations", [])
        old_names = {row["name"] for row in previous}
        candidates = session.scalars(
            select(Location).where(
                Location.source == "bat_trang_demo",
                or_(
                    Location.source_title == poi["key"],
                    Location.name.in_([poi["name"], *old_names]),
                ),
            )
        ).all()
        if len(candidates) > 1:
            raise ValueError(f"Ambiguous catalog identity: {poi['key']}")
        location = candidates[0] if candidates else None
        old_coordinates = {(row["latitude"], row["longitude"]) for row in previous}
        if location and poi.get("replaces_theme") and location.name in old_names:
            articles = session.scalars(
                select(PoiNarration).where(PoiNarration.location_id == location.id)
            ).all()
            old_descriptions = {row["description"] for row in previous}
            if (
                any(not known_narration(poi, article) for article in articles)
                or (location.latitude, location.longitude) not in old_coordinates
                or location.description_source
                not in {
                    None,
                    "Dữ liệu demo — tọa độ và nội dung cần xác minh.",
                    *old_descriptions,
                }
            ):
                raise ValueError("Edited thematic stop needs review before replacing its identity")
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
        current_coordinates = (location.latitude, location.longitude)
        new_coordinates = (poi["latitude"], poi["longitude"])
        if current_coordinates in old_coordinates:
            location.latitude, location.longitude = new_coordinates
        if location.name in old_names:
            location.name = poi["name"]
        if not location.source_title:
            location.source_title = poi["key"]
        old_descriptions = {row["description"] for row in previous}
        if location.description_source in {
            None,
            "Dữ liệu demo — tọa độ và nội dung cần xác minh.",
            *old_descriptions,
        } and current_coordinates in old_coordinates | {new_coordinates}:
            location.description_source = poi["description"]
        old_urls = {url for row in previous for url in row["source_urls"]}
        if not location.source_url or location.source_url in old_urls:
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
            elif known_narration(poi, existing) and (existing.title, existing.content) != (
                row["title"],
                row["content"],
            ):
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
            backup = database.parent / "backups" / f"before-catalog-{stamp}.db"
            if snapshot(database, backup):
                print(f"Backup: {backup}")
        print(json.dumps(seed(session)))


if __name__ == "__main__":
    main()
