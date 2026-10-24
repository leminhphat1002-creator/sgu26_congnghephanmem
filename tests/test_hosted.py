"""Optional PostgreSQL bootstrap and Windows public URL configuration."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import Base, create_db_engine
from app.main import create_app
from app.modules.admin.models import AdminUser
from app.modules.admin.passwords import verify_password
from app.modules.poi.models import Location
from scripts.start_hosted import initialize


def test_postgresql_connection_string_uses_psycopg(monkeypatch):
    value = "postgresql://user:encoded%40password@db.example/test?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", value)
    assert Settings.from_env().database_url == value.replace(
        "postgresql://", "postgresql+psycopg://"
    )
    monkeypatch.setenv("DATABASE_URL", value.replace("postgresql://", "postgres://"))
    assert Settings.from_env().database_url.startswith("postgresql+psycopg://")


def test_bootstrap_preserves_admin_edits_and_deleted_locations(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'hosted.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        with pytest.raises(ValueError, match="INITIAL_ADMIN_PASSWORD"):
            initialize(session, "admin", None, True)
        initialize(session, "admin", "test-only-initial-password", True)
        user = session.scalar(select(AdminUser))
        assert verify_password("test-only-initial-password", user.password_hash)
        saved_hash = user.password_hash
        session.delete(session.scalar(select(Location)))
        session.commit()
        initialize(session, "other-user", "another-test-password", True)
        assert session.scalar(select(func.count()).select_from(Location)) == 4
        assert session.scalar(select(func.count()).select_from(AdminUser)) == 1
        session.refresh(user)
        assert user.password_hash == saved_hash
    engine.dispose()


def test_windows_public_url_is_used_for_qr_and_revision_header(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bat-trang.example.test")
    monkeypatch.setenv("APP_REVISION", "b" * 40)
    with TestClient(create_app()) as client:
        assert client.get("/api/share").json()["url"] == "https://bat-trang.example.test/"
        assert client.get("/health").headers["x-app-revision"] == "b" * 40
