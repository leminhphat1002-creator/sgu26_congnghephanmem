from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.db import create_db_engine

ROOT = Path(__file__).resolve().parents[1]


def _alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


@pytest.fixture
def db_url(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


def test_upgrade_twice_is_safe_and_creates_locations(db_url):
    config = _alembic_config()
    command.upgrade(config, "head")
    command.upgrade(config, "head")  # chạy lặp không được lỗi

    engine = create_db_engine(db_url)
    inspector = inspect(engine)
    assert "locations" in inspector.get_table_names()
    columns = {col["name"]: col for col in inspector.get_columns("locations")}
    assert columns["latitude"]["nullable"] is True
    assert columns["longitude"]["nullable"] is True
    engine.dispose()


def test_defaults_and_unique_source_constraint(db_url):
    command.upgrade(_alembic_config(), "head")
    engine = create_db_engine(db_url)

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO locations (name) VALUES ('Nhập tay')"))
        row = conn.execute(text("SELECT radius, source, is_ready FROM locations")).one()
        assert row.radius == 80
        assert row.source == "manual"
        assert not row.is_ready

    insert_wiki = text(
        "INSERT INTO locations (name, source, source_lang, source_page_id) "
        "VALUES ('Bài A', 'wikimedia', 'vi', 123)"
    )
    with engine.begin() as conn:
        conn.execute(insert_wiki)
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(insert_wiki)
    engine.dispose()


def test_curated_migration_preserves_old_data(db_url):
    config = _alembic_config()
    command.upgrade(config, "36f391114b26")
    engine = create_db_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO locations (name) VALUES ('Existing POI')"))
    command.upgrade(config, "head")
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT name FROM locations WHERE id=1")) == "Existing POI"
        conn.execute(
            text(
                "INSERT INTO poi_narrations (location_id, language, title, content) "
                "VALUES (1, 'vi', 'Title', 'Persistent content')"
            )
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO poi_narrations (location_id, language, title, content) "
                "VALUES (1, 'vi', 'Duplicate', 'Duplicate')"
            )
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO poi_narrations (location_id, language, title, content) "
                "VALUES (999, 'en', 'Orphan', 'Orphan')"
            )
        )
    command.downgrade(config, "36f391114b26")
    assert "poi_narrations" not in inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM locations")) == 1
    command.upgrade(config, "head")
    engine.dispose()
