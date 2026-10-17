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

    async def fake_synthesize_mp3(text, language):
        raise RuntimeError("upstream failure")

    monkeypatch.setattr(module, "synthesize_mp3", fake_synthesize_mp3)
    service = AudioService(AudioStore(tmp_path))

    with pytest.raises(RuntimeError, match="tts_unavailable"):
        await service.synthesize("Xin chào")
