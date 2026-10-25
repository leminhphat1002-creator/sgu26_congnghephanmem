"""Incremental audio, cancellation, integrity and cache without cloud TTS."""

import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.modules.audio.offline import OfflineSpeech
from app.modules.audio.store import AudioStore


def local_speech(tmp_path, monkeypatch):
    speech = OfflineSpeech(AudioStore(tmp_path / "audio"), tmp_path / "models")
    calls = []

    def synthesize(text):
        calls.append(text)
        for _ in range(3):
            yield SimpleNamespace(audio_int16_bytes=b"\0\0" * 8000)

    voice = SimpleNamespace(config=SimpleNamespace(sample_rate=22050), synthesize=synthesize)
    monkeypatch.setattr(speech, "_load_voice", lambda language: voice)
    return speech, calls


def test_partial_stream_is_not_cached_and_can_close_on_another_worker(tmp_path, monkeypatch):
    speech, calls = local_speech(tmp_path, monkeypatch)
    stream = speech.stream("First sentence. Second sentence.", "vi")
    with ThreadPoolExecutor() as executor:
        assert executor.submit(next, stream).result(timeout=3)
    key = speech.cache_key("First sentence. Second sentence.", "vi")
    assert not speech.store.exists(key)
    stream.close()  # A cancelled request must release the synthesis lock across threads.
    complete = b"".join(speech.stream("First sentence. Second sentence.", "vi"))
    assert speech.store.read(key) == complete
    assert b"".join(speech.stream("First sentence. Second sentence.", "vi")) == complete
    assert len(calls) == 2


def test_concurrent_listeners_reuse_completed_audio(tmp_path, monkeypatch):
    speech, calls = local_speech(tmp_path, monkeypatch)

    def listen():
        return b"".join(speech.stream("Same narration", "en"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = executor.submit(listen), executor.submit(listen)
        assert first.result(timeout=3) == second.result(timeout=3)
    assert calls == ["Same narration"]


def test_model_integrity_check_fails_without_download(tmp_path, monkeypatch):
    speech = OfflineSpeech(AudioStore(tmp_path / "audio"), tmp_path / "models")
    speech.model_dir.mkdir()
    speech.manifest = {
        "voices": {
            "vi": {
                "files": [{"filename": "voice.onnx", "sha256": hashlib.sha256(b"ok").hexdigest()}]
            }
        }
    }
    monkeypatch.setattr("app.modules.audio.offline.importlib.util.find_spec", lambda name: True)
    with pytest.raises(AppError, match="chưa có mô hình"):
        speech.check("vi")
    (speech.model_dir / "voice.onnx").write_bytes(b"tampered")
    with pytest.raises(AppError, match="checksum"):
        speech.check("vi")
    (speech.model_dir / "voice.onnx").write_bytes(b"ok")
    speech.check("vi")


@pytest.mark.asyncio
async def test_async_stream_cancel_releases_slot_and_many_listeners_do_not_starve_workers(
    tmp_path, monkeypatch
):
    speech, calls = local_speech(tmp_path, monkeypatch)
    partial = speech.stream_async("Cancelled narration", "vi")
    assert await anext(partial)
    await partial.aclose()
    assert not speech.store.exists(speech.cache_key("Cancelled narration", "vi"))

    async def listen():
        return b"".join([part async for part in speech.stream_async("Shared narration", "vi")])

    results = await asyncio.wait_for(asyncio.gather(*(listen() for _ in range(45))), timeout=10)
    assert len(set(results)) == 1
    assert calls == ["Cancelled narration", "Shared narration"]
