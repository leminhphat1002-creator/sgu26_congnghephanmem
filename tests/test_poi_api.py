"""Kiểm thử các endpoint POI với SQLite độc lập."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth import require_admin
from app.core.db import Base, create_db_engine, get_db
from app.main import app
from app.modules.poi import models  # noqa: F401


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    database_url = f"sqlite:///{(tmp_path / 'poi_test.db').as_posix()}"
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
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_list_locations_returns_200(client):
    response = client.get("/locations")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_location_success(client):
    payload = {
        "name": "Test POI API",
        "description_source": "Địa điểm dùng để kiểm thử",
        "latitude": 10.777,
        "longitude": 106.695,
        "radius": 80,
        "source": "manual",
        "is_ready": True,
    }

    response = client.post("/locations", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == payload["name"]
    assert response.json()["latitude"] == payload["latitude"]


def test_create_location_rejects_invalid_latitude(client):
    payload = {
        "name": "Invalid Location",
        "latitude": 100,
        "longitude": 106.695,
    }

    response = client.post("/locations", json=payload)

    assert response.status_code == 422


def test_get_missing_location_returns_404(client):
    response = client.get("/locations/999999999")

    assert response.status_code == 404


def test_nearby_rejects_invalid_coordinates(client):
    response = client.get(
        "/locations/nearby",
        params={
            "latitude": 100,
            "longitude": 106.695,
            "radius": 500,
        },
    )

    assert response.status_code == 422


@pytest.fixture(autouse=True)
def authorized_api_requests():
    app.dependency_overrides[require_admin] = lambda: {"username": "api-test"}
    yield
    app.dependency_overrides.pop(require_admin, None)
