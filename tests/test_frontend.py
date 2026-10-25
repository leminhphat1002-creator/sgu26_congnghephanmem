from fastapi.testclient import TestClient

from app.main import app


def test_homepage():
    """Trang chủ hiển thị giao diện chọn địa điểm."""
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Tìm địa điểm xung quanh" in response.text
    assert 'id="locationList"' in response.text
    assert 'id="autoGpsButton"' in response.text
    assert response.headers["cache-control"] == "no-cache"


def test_frontend_css():
    """Kiểm tra file CSS được phục vụ thành công."""
    with TestClient(app) as client:
        response = client.get("/static/app/style.css")

    assert response.status_code == 200
    assert ".container" in response.text
    assert ".location-item" in response.text


def test_frontend_javascript():
    """Kiểm tra JavaScript sử dụng API chọn địa điểm."""
    with TestClient(app) as client:
        response = client.get("/static/app/script.js")

    assert response.status_code == 200
    assert "/narration/nearby" in response.text
    assert "/narration/locations/" in response.text
    assert "selectLocation" in response.text
    assert "watchPosition" in response.text
    assert response.headers["cache-control"] == "no-cache"
