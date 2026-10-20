"""Kiểm thử GET/DELETE cache thuyết minh theo ID địa điểm."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base, create_db_engine, get_db
from app.main import app
from app.modules.content.models import NarrationCache  # noqa: F401
from app.modules.content.repository import ContentRepository
from app.modules.poi.models import Location  # noqa: F401


@pytest.fixture
def test_environment(tmp_path) -> Iterator[tuple[TestClient, sessionmaker]]:
    """SQLite riêng cho mỗi bài test, không dùng database thật."""
    database_url = f"sqlite:///{(tmp_path / 'cache_test.db').as_posix()}"
    engine = create_db_engine(database_url)

    Base.metadata.create_all(bind=engine)

    testing_sessionmaker = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db() -> Iterator[Session]:
        with testing_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, testing_sessionmaker
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def create_location(client: TestClient) -> int:
    """Tạo địa điểm mẫu qua POI API."""
    response = client.post(
        "/locations",
        json={
            "name": "Dinh Độc Lập",
            "source_title": "Dinh Độc Lập",
            "source_lang": "vi",
            "source": "manual",
            "latitude": 10.7769,
            "longitude": 106.6955,
            "radius": 100,
            "is_ready": True,
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def save_cache(testing_sessionmaker: sessionmaker) -> None:
    """Tạo cache bằng repository thật, không gọi Wikimedia."""
    with testing_sessionmaker() as session:
        repository = ContentRepository(session)

        repository.save(
            page_title="dinh độc lập",
            language="vi",
            extract="Dinh Độc Lập là một địa điểm lịch sử.",
            source_url="https://vi.wikipedia.org/wiki/Dinh_Độc_Lập",
            ttl_seconds=3600,
        )


def test_get_location_cache_success(test_environment):
    """GET trả về cache đã lưu."""
    client, session_factory = test_environment

    location_id = create_location(client)
    save_cache(session_factory)

    response = client.get(f"/locations/{location_id}/narrations/vi")

    assert response.status_code == 200

    data = response.json()

    assert data["location_id"] == location_id
    assert data["location_name"] == "Dinh Độc Lập"
    assert data["title"] == "dinh độc lập"
    assert data["language"] == "vi"
    assert "địa điểm lịch sử" in data["extract"]
    assert "expires_at" in data


def test_get_location_cache_not_found(test_environment):
    """Địa điểm có tồn tại nhưng chưa có cache."""
    client, _ = test_environment

    location_id = create_location(client)

    response = client.get(f"/locations/{location_id}/narrations/vi")

    assert response.status_code == 404


def test_get_location_not_found(test_environment):
    """Không tìm thấy ID địa điểm."""
    client, _ = test_environment

    response = client.get("/locations/999999999/narrations/vi")

    assert response.status_code == 404


def test_delete_location_cache_success(test_environment):
    """DELETE xóa cache và GET sau đó trả về 404."""
    client, session_factory = test_environment

    location_id = create_location(client)
    save_cache(session_factory)

    response = client.delete(f"/locations/{location_id}/narrations/vi")

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1

    after_delete = client.get(f"/locations/{location_id}/narrations/vi")

    assert after_delete.status_code == 404


def test_unsupported_language(test_environment):
    """GET và DELETE từ chối ngôn ngữ không hỗ trợ."""
    client, _ = test_environment

    location_id = create_location(client)

    get_response = client.get(f"/locations/{location_id}/narrations/xyz")

    delete_response = client.delete(f"/locations/{location_id}/narrations/xyz")

    assert get_response.status_code == 422
    assert delete_response.status_code == 422
