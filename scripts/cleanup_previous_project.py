"""Dọn dữ liệu đồ án cũ đã xác định; mặc định chỉ xem trước.

python -m scripts.cleanup_previous_project --apply
Sao lưu SQLite và MP3 trước khi xóa. Không đổi tài khoản hoặc dữ liệu Bát Tràng.
"""

import argparse
import json
import re
import shutil
import sqlite3
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.modules.audio.service import AudioService
from app.modules.audio.store import AudioStore
from app.modules.audio.tts_client import VOICE_BY_LANGUAGE
from app.modules.content.service import ContentService

LEGACY_NAMES = (
    "Dinh Độc Lập",
    "Dinh Norodom",
    "Quận 1",
    "Sự kiện 30 tháng 4 năm 1975",
    "Công viên 30 tháng 4",
    "Trụ sở Tòa án nhân dân Thành phố Hồ Chí Minh",
    "Nhạc viện Thành phố Hồ Chí Minh",
    "Trường Trung học phổ thông Lê Quý Đôn, Thành phố Hồ Chí Minh",
    "Công viên Bách Tùng Diệp",
    "Bến Thành (phường)",
    "Công viên Tao Đàn",
    "Thư viện Khoa học Tổng hợp Thành phố Hồ Chí Minh",
    "Bảo tàng Thành phố Hồ Chí Minh",
    "Chợ Bến Thành",
    "Nhà thờ Đức Bà Sài Gòn",
)


def normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip().casefold()


def cleanup(database_path: Path, audio_roots: list[Path], apply: bool = False) -> dict:
    database_path = database_path.resolve(strict=True)
    names = {normalized(name) for name in LEGACY_NAMES}
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        locations = list(db.execute("SELECT id,name,source_title FROM locations ORDER BY id"))
        old_ids = {row["id"] for row in locations if normalized(row["name"]) in names}
        old_cache = [
            row["id"]
            for row in db.execute("SELECT id,page_title FROM narration_cache")
            if normalized(row["page_title"]) in names
        ]
        old_id_text = {str(value) for value in old_ids}
        old_events = [
            row["id"]
            for row in db.execute("SELECT id,target FROM activity_events")
            if row["target"].split("/")[0] in old_id_text
        ]
        keep_keys = set()
        for row in db.execute("SELECT location_id,language,content FROM poi_narrations"):
            if row["location_id"] in old_ids or row["language"] not in VOICE_BY_LANGUAGE:
                continue
            text = ContentService.shorten_text(row["content"])
            if text:
                key = AudioStore.cache_key(
                    AudioService.normalize_text(text),
                    row["language"],
                    VOICE_BY_LANGUAGE[row["language"]],
                )
                keep_keys.add(key)
        old_audio = []
        for root in dict.fromkeys(path.resolve() for path in audio_roots):
            if not root.is_dir():
                continue
            for path in root.glob("*.mp3"):
                if path.is_symlink() or not re.fullmatch(r"[0-9a-f]{64}\.mp3", path.name):
                    continue
                if path.resolve().parent != root:
                    raise ValueError("Audio file escaped its configured directory")
                if path.stem not in keep_keys:
                    old_audio.append(path)
        report = {
            "locations": len(old_ids),
            "cache": len(old_cache),
            "events": len(old_events),
            "audio": len(old_audio),
            "kept_locations": len(locations) - len(old_ids),
            "backup": None,
        }
        if not apply or not any((old_ids, old_cache, old_events, old_audio)):
            return report
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
        backup = database_path.parent / "backups" / ("previous-project-" + stamp)
        backup.mkdir(parents=True)
        with sqlite3.connect(backup / database_path.name) as target:
            db.backup(target)
        manifest = []
        for index, path in enumerate(old_audio):
            folder = backup / f"audio-{index}"
            folder.mkdir()
            shutil.copy2(path, folder / path.name)
            manifest.append(
                {"original": str(path), "backup": str((folder / path.name).relative_to(backup))}
            )
        (backup / "manifest.json").write_text(
            json.dumps(
                {"removed_location_ids": sorted(old_ids), "audio_files": manifest},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        db.execute("BEGIN IMMEDIATE")
        current = list(db.execute("SELECT id,name,source_title FROM locations ORDER BY id"))
        if [tuple(row) for row in current] != [tuple(row) for row in locations]:
            db.rollback()
            raise RuntimeError("Locations changed during backup; rerun cleanup")
        db.executemany("DELETE FROM locations WHERE id=?", [(value,) for value in old_ids])
        db.executemany("DELETE FROM narration_cache WHERE id=?", [(value,) for value in old_cache])
        db.executemany("DELETE FROM activity_events WHERE id=?", [(value,) for value in old_events])
        db.commit()
        for path in old_audio:
            path.unlink()
        report["backup"] = str(backup)
        return report


def main():
    parser = argparse.ArgumentParser(description="Remove identified previous-project data")
    parser.add_argument("--apply", action="store_true", help="Back up and apply the cleanup")
    args = parser.parse_args()
    settings = get_settings()
    url = make_url(settings.database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        parser.error("A file-based SQLite database is required")
    result = cleanup(
        Path(url.database), [Path(settings.audio_dir), Path("audio_cache")], args.apply
    )
    print("Applied:" if args.apply else "Preview:", result)


if __name__ == "__main__":
    main()
