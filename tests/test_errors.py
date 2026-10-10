from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import AppError, register_exception_handlers


def test_app_error_uses_detail_code_message_format():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise AppError("tts_unavailable", "Dịch vụ TTS tạm thời lỗi", status_code=503)

    response = TestClient(app).get("/boom")
    assert response.status_code == 503
    assert response.json() == {
        "detail": {"code": "tts_unavailable", "message": "Dịch vụ TTS tạm thời lỗi"}
    }
