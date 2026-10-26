"""Real authentication, CSRF, CRUD, QR and dashboard integration tests."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import COOKIE_NAME
from app.core.db import Base, create_db_engine, get_db
from app.main import create_app
from app.modules.admin.api import _attempts
from app.modules.admin.models import ActivityEvent, AdminSession, AdminUser
from app.modules.admin.passwords import hash_password, verify_password
from app.modules.admin.repository import utcnow
from app.modules.audio.api import get_audio_service
from scripts.seed_bat_trang import seed

PASSWORD = "test-only-secure-password"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    _attempts.clear()
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    engine = create_db_engine(f"sqlite:///{tmp_path / 'admin.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        session.add(AdminUser(username="admin", password_hash=hash_password(PASSWORD)))
        session.commit()
        application = create_app()

        def database():
            yield session

        audio = AsyncMock()
        audio.synthesize.return_value = {"audio_filename": "test.mp3", "cache_hit": True}
        application.dependency_overrides[get_db] = database
        application.dependency_overrides[get_audio_service] = lambda: audio
        with TestClient(application) as client:
            yield client, session
    engine.dispose()
    _attempts.clear()


def login(client):
    response = client.post("/api/admin/login", json={"username": "admin", "password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_password_hashes_have_unique_salts():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first != second
    assert PASSWORD not in first
    assert verify_password(PASSWORD, first)
    assert not verify_password("wrong", first)


def test_anonymous_can_browse_but_not_mutate(environment):
    client, _ = environment
    assert client.get("/").status_code == 200
    assert len(client.get("/narration/catalog").json()) == 5
    assert client.post("/narration/locations/1").status_code == 200
    for path in ["/api/admin/me", "/api/admin/dashboard", "/api/admin/locations"]:
        assert client.get(path).status_code == 401
    assert client.post("/locations", json={"name": "Unauthorized"}).status_code == 401
    assert client.put("/locations/1", json={"name": "Unauthorized"}).status_code == 401
    assert client.delete("/locations/1").status_code == 401
    assert client.delete("/content/cache?title=x").status_code == 401
    assert client.delete("/locations/1/narrations/vi").status_code == 401
    assert client.post("/audio/tts", json={"text": "x", "lang": "vi"}).status_code == 401
    assert (
        client.put(
            "/api/admin/locations/1/narrations/vi", json={"title": "x", "content": "x"}
        ).status_code
        == 401
    )


def test_login_csrf_logout_revokes_cookie(environment):
    client, session = environment
    headers = login(client)
    cookie = client.cookies.get(COOKIE_NAME)
    assert session.scalar(select(AdminSession)).token_hash != cookie
    assert client.get("/api/admin/me").json()["username"] == "admin"
    assert client.put("/locations/1", json={"name": "Blocked"}).status_code == 403
    assert (
        client.put(
            "/locations/1", json={"name": "Blocked"}, headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/locations/1",
            json={"name": "Blocked"},
            headers={**headers, "Origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/locations/1", json={"description_source": "Updated"}, headers=headers
        ).status_code
        == 200
    )
    assert client.post("/api/admin/logout", headers=headers).status_code == 200
    client.cookies.set(COOKIE_NAME, cookie)
    assert client.get("/api/admin/dashboard").status_code == 401


def test_expired_session_is_rejected(environment):
    client, session = environment
    login(client)
    row = session.scalar(select(AdminSession))
    row.expires_at = utcnow() - timedelta(seconds=1)
    session.commit()
    assert client.get("/api/admin/me").status_code == 401


def test_login_rate_limit_and_origin(environment):
    client, _ = environment
    data = {"username": "admin", "password": "wrong"}
    assert (
        client.post(
            "/api/admin/login", json=data, headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
    for _ in range(5):
        assert client.post("/api/admin/login", json=data).status_code == 401
    assert client.post("/api/admin/login", json=data).status_code == 429


def test_admin_crud_and_narration_validation(environment):
    client, _ = environment
    headers = login(client)
    created = client.post(
        "/locations", json={"name": "Disposable POI", "is_ready": True}, headers=headers
    )
    assert created.status_code == 201
    location_id = created.json()["id"]
    path = f"/api/admin/locations/{location_id}/narrations/vi"
    assert (
        client.put(
            path, json={"title": "Title", "content": "New content"}, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/admin/locations/{location_id}/narrations").json()[0]["content"]
        == "New content"
    )
    assert any(
        row["location"]["id"] == location_id for row in client.get("/narration/catalog").json()
    )
    assert (
        client.put(path, json={"title": "Title", "content": " "}, headers=headers).status_code
        == 422
    )
    assert (
        client.put(path, json={"title": "Title", "content": "x" * 901}, headers=headers).status_code
        == 422
    )
    assert client.put("/locations/1", json={"name": None}, headers=headers).status_code == 422
    assert client.put("/locations/1", json={"latitude": None}, headers=headers).status_code == 422
    assert client.delete(path, headers=headers).status_code == 200
    assert client.delete(f"/locations/{location_id}", headers=headers).status_code == 204
    assert client.get(f"/locations/{location_id}").status_code == 404


def test_dashboard_counts_real_usage(environment):
    client, session = environment
    login(client)
    first = client.get("/api/admin/dashboard").json()
    assert first["locations"] == 5
    assert first["narrations"] == 15
    assert first["languages"] == {"vi": 5, "en": 5, "ja": 5}
    client.post("/narration/locations/1?language=ja")
    result = client.get("/api/admin/dashboard")
    assert result.headers["cache-control"] == "no-store"
    assert result.json()["requests_today"] == first["requests_today"] + 1
    assert sum(row["count"] for row in result.json()["daily"]) == 1
    event = session.scalar(select(ActivityEvent).where(ActivityEvent.action == "narration"))
    assert event.actor == "visitor" and event.target == "1" and event.status == "success"


def test_presence_counts_browsers_separately_from_usage_and_requires_admin(environment):
    client, _ = environment
    assert client.get("/api/admin/presence").status_code == 401
    login(client)
    assert client.get("/api/admin/presence").json()["active_visitors"] == 0
    before = client.get("/api/admin/dashboard").json()["requests_today"]
    for _ in range(3):
        response = client.post("/api/presence/heartbeat")
        assert response.status_code == 204
        assert response.content == b""
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "Path=/api/presence" in response.headers["set-cookie"]
        assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/admin/dashboard").json()["active_visitors"] == 1
    with TestClient(client.app) as second_browser:
        assert second_browser.post("/api/presence/heartbeat").status_code == 204
    result = client.get("/api/admin/dashboard").json()
    assert result["active_visitors"] == 2
    assert result["active_window_seconds"] == 120
    assert result["requests_today"] == before


def test_presence_heartbeat_is_public_but_rejects_foreign_origin(environment):
    client, _ = environment
    assert (
        client.post(
            "/api/presence/heartbeat", headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
    assert client.app.state.visitor_presence.snapshot()["active_visitors"] == 0

    # This path must work without opening or writing the application database.
    def no_database():
        raise AssertionError("Heartbeat must not access SQLite")

    client.app.dependency_overrides[get_db] = no_database
    assert client.post("/api/presence/heartbeat").status_code == 204
    assert client.app.state.visitor_presence.snapshot()["active_visitors"] == 1


def test_qr_is_public_and_configurable(environment, monkeypatch):
    client, _ = environment
    assert client.get("/api/share").json()["url"] == "http://testserver/"
    monkeypatch.setenv("PUBLIC_BASE_URL", "")
    assert client.get("/api/share").json()["url"] == "http://testserver/"
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://guide.example.com")
    assert client.get("/api/share").json()["url"] == "https://guide.example.com/"
    response = client.get("/share/qr.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in response.text or ":svg" in response.text
    assert "<script" not in response.text
    png = client.get("/share/qr.png")
    assert png.status_code == 200
    assert png.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert client.get("/share").status_code == 200
    monkeypatch.setenv("PUBLIC_BASE_URL", "javascript:alert(1)")
    assert client.get("/api/share").status_code == 503


def test_cookie_and_security_headers(environment):
    client, _ = environment
    response = client.post("/api/admin/login", json={"username": "admin", "password": PASSWORD})
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    response = client.get("/admin")
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
