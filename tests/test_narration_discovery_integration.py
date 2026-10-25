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
    # The sample position is the sourced market location, not the old demo cluster.
    response = client.get("/narration/nearby?latitude=20.974974&longitude=105.912077")
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


def test_text_is_available_without_waiting_for_or_calling_tts(environment):
    client, session, audio = environment
    audio.synthesize.side_effect = AssertionError("Text requests must never call TTS")
    location_id = client.get("/narration/catalog").json()[0]["location"]["id"]
    row = session.scalar(
        select(PoiNarration).where(
            PoiNarration.location_id == location_id, PoiNarration.language == "vi"
        )
    )
    row.content = "Bài đã cập nhật, không chờ dịch vụ giọng đọc."
    session.commit()
    result = client.get(f"/narration/locations/{location_id}/text?language=vi")
    assert result.status_code == 200
    assert result.json()["text"] == row.content
    assert result.json()["audio_url"] is None
    audio.synthesize.assert_not_awaited()
    assert client.get("/narration/locations/99999/text").status_code == 404
    assert client.get(f"/narration/locations/{location_id}/text?language=fr").status_code == 422


def test_local_stream_cache_range_and_stale_text_version(environment, tmp_path, monkeypatch):
    from app.modules.audio.offline import OfflineSpeech
    from app.modules.audio.store import AudioStore
    from app.modules.narration.api import get_offline_speech

    client, session, cloud = environment
    speech = OfflineSpeech(AudioStore(tmp_path / "local-audio"))
    monkeypatch.setattr(speech, "check", lambda language: None)
    used = []

    def stream(text, language):
        used.append(language)
        yield b"first-"
        yield b"second"
        speech.store.write(speech.cache_key(text, language), b"first-second")

    monkeypatch.setattr(speech, "stream", stream)
    client.app.dependency_overrides[get_offline_speech] = lambda: speech
    location_id = client.get("/narration/catalog").json()[0]["location"]["id"]
    data = client.get(f"/narration/locations/{location_id}/text?language=vi").json()
    response = client.get(data["stream_url"])
    assert response.content == b"first-second"
    assert response.headers["x-audio-engine"] == "piper-local"
    assert response.headers["content-type"] == "audio/mpeg"
    cached = client.get(data["stream_url"], headers={"Range": "bytes=0-4"})
    assert cached.status_code == 206
    assert cached.content == b"first"
    assert used == ["vi"]
    cloud.synthesize.assert_not_awaited()
    row = session.scalar(
        select(PoiNarration).where(
            PoiNarration.location_id == location_id, PoiNarration.language == "vi"
        )
    )
    row.content = "Updated after the visitor opened the article"
    session.commit()
    assert client.get(data["stream_url"]).status_code == 409
    assert client.get("/narration/locations/99999/speech").status_code == 404
    assert client.get(f"/narration/locations/{location_id}/speech?language=fr").status_code == 422


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
