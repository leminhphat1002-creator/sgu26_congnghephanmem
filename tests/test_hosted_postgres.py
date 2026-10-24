"""Run against a disposable PostgreSQL service in CI; never use a production database."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import create_db_engine, get_db
from app.main import create_app
from app.modules.admin.models import AdminUser
from app.modules.poi.models import Location
from scripts.start_hosted import prepare_database


@pytest.mark.skipif(
    not os.environ.get("TEST_POSTGRES_URL"), reason="PostgreSQL service is available in CI"
)
def test_postgres_migration_bootstrap_login_and_dashboard(monkeypatch):
    database_url = os.environ["TEST_POSTGRES_URL"]
    url = make_url(database_url)
    assert url.database == "bat_trang_test" and url.host in {"127.0.0.1", "localhost"}
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INITIAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "postgres-test-password")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    get_settings.cache_clear()
    try:
        prepare_database()
        engine = create_db_engine(database_url)
        with Session(engine) as session:
            application = create_app()

            def database():
                yield session

            application.dependency_overrides[get_db] = database
            with TestClient(application) as client:
                assert len(client.get("/narration/catalog").json()) == 5
                response = client.post(
                    "/api/admin/login",
                    json={"username": "admin", "password": "postgres-test-password"},
                )
                assert response.status_code == 200
                dashboard = client.get("/api/admin/dashboard")
                assert dashboard.status_code == 200
                assert dashboard.json()["narrations"] == 15
                assert len(dashboard.json()["daily"]) == 7
            original_hash = session.scalar(select(AdminUser.password_hash))
            session.delete(session.scalar(select(Location)))
            session.commit()
        monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "different-secret-password")
        prepare_database()
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(Location)) == 4
            assert session.scalar(select(AdminUser.password_hash)) == original_hash
        engine.dispose()
    finally:
        get_settings.cache_clear()
