"""Cleanup backs up old project data while retaining Bat Trang and admin access."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.db import Base, create_db_engine
from app.modules.admin.models import ActivityEvent, AdminSession, AdminUser
from app.modules.audio.store import AudioStore
from app.modules.audio.tts_client import VOICE_BY_LANGUAGE
from app.modules.content.models import NarrationCache, PoiNarration
from app.modules.content.service import ContentService
from app.modules.poi.models import Location
from scripts.cleanup_previous_project import cleanup
from scripts.seed_bat_trang import seed


def test_cleanup_preserves_bat_trang_and_admin_and_is_repeatable(tmp_path):
    db_path = tmp_path / "app.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        legacy = Location(name="Dinh Độc Lập", source="manual", is_ready=True)
        session.add(legacy)
        session.flush()
        old_id = legacy.id
        session.add(
            PoiNarration(location_id=old_id, language="vi", title="Old", content="Old content")
        )
        session.add(
            NarrationCache(
                page_title="DINH ĐỘC LẬP",
                language="vi",
                extract="Old cache",
                expires_at=datetime.now() + timedelta(days=1),
            )
        )
        session.add(AdminUser(id=1, username="owner", password_hash="preserve-this-hash"))
        session.flush()
        session.add(
            AdminSession(
                user_id=1,
                token_hash="session",
                csrf_token="csrf",
                expires_at=datetime.now() + timedelta(hours=1),
            )
        )
        session.add_all(
            [
                ActivityEvent(
                    created_at=datetime.now(),
                    actor="visitor",
                    action="narration",
                    target=str(old_id),
                ),
                ActivityEvent(created_at=datetime.now(), actor="owner", action="login", target=""),
            ]
        )
        session.commit()
        narration = session.query(PoiNarration).filter_by(language="vi").first()
        keep_key = AudioStore.cache_key(
            ContentService.shorten_text(narration.content), "vi", VOICE_BY_LANGUAGE["vi"]
        )
    audio_root = tmp_path / "audio"
    audio_root.mkdir()
    kept_audio = audio_root / f"{keep_key}.mp3"
    kept_audio.write_bytes(b"keep-bat-trang")
    old_audio = audio_root / ("a" * 64 + ".mp3")
    old_audio.write_bytes(b"old-project-audio")
    preview = cleanup(db_path, [audio_root])
    assert preview["locations"] == preview["cache"] == preview["events"] == preview["audio"] == 1
    assert old_audio.exists()
    result = cleanup(db_path, [audio_root], apply=True)
    backup = Path(result["backup"])
    with sqlite3.connect(backup / "app.db") as saved:
        assert saved.execute("SELECT count(*) FROM locations").fetchone()[0] == 6
    assert any(path.read_bytes() == b"old-project-audio" for path in backup.rglob("*.mp3"))
    assert not old_audio.exists()
    assert kept_audio.read_bytes() == b"keep-bat-trang"
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT count(*) FROM locations").fetchone()[0] == 5
        assert db.execute("SELECT count(*) FROM poi_narrations").fetchone()[0] == 15
        assert db.execute("SELECT count(*) FROM narration_cache").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM admin_sessions").fetchone()[0] == 1
        assert (
            db.execute("SELECT password_hash FROM admin_users").fetchone()[0]
            == "preserve-this-hash"
        )
        assert db.execute("SELECT count(*) FROM activity_events").fetchone()[0] == 1
    second = cleanup(db_path, [audio_root], apply=True)
    assert second["locations"] == second["audio"] == 0
    assert second["backup"] is None
    engine.dispose()
