
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_locations_returns_200():
    response = client.get("/locations")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_location_success():
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


def test_create_location_rejects_invalid_latitude():
    payload = {
        "name": "Invalid Location",
        "latitude": 100,
        "longitude": 106.695,
    }

    response = client.post("/locations", json=payload)

    assert response.status_code == 422


def test_get_missing_location_returns_404():
    response = client.get("/locations/999999999")

    assert response.status_code == 404


def test_nearby_rejects_invalid_coordinates():
    response = client.get(
        "/locations/nearby",
        params={
            "latitude": 100,
            "longitude": 106.695,
            "radius": 500,
        },
    )

    assert response.status_code == 422
