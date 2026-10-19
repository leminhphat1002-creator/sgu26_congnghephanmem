import asyncio

import pytest

from app.modules.audio.service import AudioService
from app.modules.audio.store import AudioStore


@pytest.mark.asyncio
async def test_synthesize_generates_and_caches_audio(tmp_path, monkeypatch):
    import app.modules.audio.service as module

    calls = 0

    async def fake_synthesize_mp3(text, language):
        nonlocal calls
        calls += 1
        return b"fake-mp3"

    monkeypatch.setattr(module, "synthesize_mp3", fake_synthesize_mp3)
    service = AudioService(AudioStore(tmp_path))

    first = await service.synthesize("  Xin   chào  ", "vi")
    second = await service.synthesize("Xin chào", "vi")

    assert first["audio"] == b"fake-mp3"
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert calls == 1


@pytest.mark.asyncio
async def test_synthesize_rejects_empty_text(tmp_path):
    service = AudioService(AudioStore(tmp_path))

    with pytest.raises(ValueError, match="không được để trống"):
        await service.synthesize("   ")


@pytest.mark.asyncio
async def test_synthesize_rejects_unsupported_language(tmp_path):
    service = AudioService(AudioStore(tmp_path))

    with pytest.raises(ValueError, match="chưa được hỗ trợ"):
        await service.synthesize("Hello", "fr")


@pytest.mark.asyncio
async def test_synthesize_reports_tts_unavailable(tmp_path, monkeypatch):
    import app.modules.audio.service as module
    from app.core.exceptions import AppError

    async def fake_synthesize_mp3(text, language):
        raise RuntimeError("upstream failure")

    monkeypatch.setattr(module, "synthesize_mp3", fake_synthesize_mp3)
    service = AudioService(AudioStore(tmp_path))

    with pytest.raises(AppError) as exc_info:
        await service.synthesize("Xin chào")

    assert exc_info.value.code == "tts_unavailable"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_synthesize_regenerates_audio_when_cache_file_is_deleted(tmp_path, monkeypatch):
    import app.modules.audio.service as module

    calls = 0

    async def fake_synthesize_mp3(text, language):
        nonlocal calls
        calls += 1
        return b"fake-mp3"

    monkeypatch.setattr(module, "synthesize_mp3", fake_synthesize_mp3)

    store = AudioStore(tmp_path)
    service = AudioService(store)

    first = await service.synthesize("Xin chao", "vi")
    assert first["cache_hit"] is False
    assert calls == 1

    # Xóa file cache để mô phỏng cache bị mất.
    cache_path = tmp_path / f"{first['cache_key']}.mp3"
    assert cache_path.is_file()
    cache_path.unlink()

    second = await service.synthesize("Xin chao", "vi")

    assert second["cache_hit"] is False
    assert second["audio"] == b"fake-mp3"
    assert calls == 2
    assert cache_path.is_file()


@pytest.mark.asyncio
async def test_concurrent_requests_generate_audio_only_once(tmp_path, monkeypatch):
    import app.modules.audio.service as module

    calls = 0

    async def fake_synthesize_mp3(text, language):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return b"fake-mp3"

    monkeypatch.setattr(module, "synthesize_mp3", fake_synthesize_mp3)
    service = AudioService(AudioStore(tmp_path))

    first, second = await asyncio.gather(
        service.synthesize("Xin chao", "vi"),
        service.synthesize("Xin chao", "vi"),
    )

    assert calls == 1
    assert first["audio"] == b"fake-mp3"
    assert second["audio"] == b"fake-mp3"
    assert sorted([first["cache_hit"], second["cache_hit"]]) == [
        False,
        True,
    ]
