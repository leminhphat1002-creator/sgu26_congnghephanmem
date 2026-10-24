"""Tích hợp catalog từ xa, GPS, seed và thuyết minh SQLite."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.db import Base, create_db_engine, get_db
from app.core.exceptions import AppError
from app.main import create_app
from app.modules.audio.api import get_audio_service
from app.modules.content.models import PoiNarration
from app.modules.poi.models import Location
from scripts.seed_bat_trang import seed


@pytest.fixture
def environment(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'integration.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        seed(session)
        application = create_app()
        application.dependency_overrides[require_admin] = lambda: {"username": "integration-test"}

        def database():
            yield session

        audio = AsyncMock()
        audio.synthesize.return_value = {"audio_filename": "sample.mp3", "cache_hit": True}
        application.dependency_overrides[get_db] = database
        application.dependency_overrides[get_audio_service] = lambda: audio
        with TestClient(application) as client:
            yield client, session, audio
    engine.dispose()


def test_seed_is_idempotent_and_keeps_edits(environment):
    _, session, _ = environment
    assert session.scalar(select(func.count()).select_from(Location)) == 5
    assert session.scalar(select(func.count()).select_from(PoiNarration)) == 15
    row = session.scalar(select(PoiNarration))
    row.content = "Nội dung đã biên tập"
    session.commit()
    seed(session)
    session.refresh(row)
    assert row.content == "Nội dung đã biên tập"


def test_remote_catalog_and_selected_narration(environment):
    client, _, audio = environment
    response = client.get("/narration/catalog")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 5
    assert all(row["distance_meters"] is None for row in rows)
    result = client.post(f"/narration/locations/{rows[0]['location']['id']}?language=ja")
    assert result.status_code == 200
    assert result.json()["content_language"] == "ja"
    assert result.json()["distance_meters"] is None
    assert result.json()["audio_url"] == "/audio/sample.mp3"
    assert audio.synthesize.await_args.kwargs["lang"] == "ja"


def test_real_gps_far_away_and_demo_nearby(environment):
    client, _, audio = environment
    assert client.get("/narration/nearby?latitude=0&longitude=0").json() == []
    response = client.get("/narration/nearby?latitude=20.9784&longitude=105.9146")
    assert len(response.json()) == 5
    audio.synthesize.assert_not_awaited()
    assert client.get("/narration/nearby?latitude=100&longitude=0").status_code == 422


def test_text_survives_tts_failure(environment):
    client, _, audio = environment
    audio.synthesize.side_effect = AppError("tts_unavailable", "Unavailable", 503)
    location_id = client.get("/narration/catalog").json()[0]["location"]["id"]
    result = client.post(f"/narration/locations/{location_id}?language=en").json()
    assert result["status"] == "text_only"
    assert result["text"]
    assert result["audio_url"] is None
    assert client.post("/narration/locations/99999").status_code == 404


def test_delete_location_cascades_narrations(environment):
    client, session, _ = environment
    location_id = client.get("/narration/catalog").json()[0]["location"]["id"]
    assert client.delete(f"/locations/{location_id}").status_code == 204
    assert (
        session.scalar(
            select(func.count())
            .select_from(PoiNarration)
            .where(PoiNarration.location_id == location_id)
        )
        == 0
    )
