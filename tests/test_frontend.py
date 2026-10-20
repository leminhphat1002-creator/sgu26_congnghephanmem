"""Kiểm tra FastAPI phục vụ giao diện demo GPS."""

from fastapi.testclient import TestClient

from app.main import app


def test_homepage():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Phát hiện và thuyết minh" in response.text


def test_frontend_css():
    with TestClient(app) as client:
        response = client.get("/static/app/style.css")

    assert response.status_code == 200
    assert ".container" in response.text


def test_frontend_javascript():
    with TestClient(app) as client:
        response = client.get("/static/app/script.js")

    assert response.status_code == 200
    assert "/narration/detect" in response.text
