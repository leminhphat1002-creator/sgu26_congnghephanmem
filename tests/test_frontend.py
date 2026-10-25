import gzip

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


def test_map_compression_reduces_transfer_and_keeps_original_content():
    """Compress the large static map, keeping content negotiation and revalidation."""
    with TestClient(app) as client:
        plain = client.get(
            "/static/app/bat-trang-basemap.geojson", headers={"Accept-Encoding": "identity"}
        )
        with client.stream(
            "GET", "/static/app/bat-trang-basemap.geojson", headers={"Accept-Encoding": "gzip"}
        ) as compressed:
            encoded = b"".join(compressed.iter_raw())
        page = client.get("/", headers={"Accept-Encoding": "gzip"})
    assert compressed.status_code == plain.status_code == 200
    assert gzip.decompress(encoded) == plain.content
    assert compressed.headers["content-encoding"] == "gzip"
    assert "accept-encoding" in compressed.headers["vary"].lower()
    assert len(encoded) < len(plain.content) // 2
    assert compressed.headers["cache-control"] == "no-cache"
    assert "content-encoding" not in plain.headers
    assert "content-encoding" not in page.headers  # Compression is confined to static files.
