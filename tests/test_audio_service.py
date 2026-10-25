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


@pytest.mark.asyncio
async def test_tts_failure_backoff_still_serves_cache_and_recovers(tmp_path, monkeypatch):
    import app.modules.audio.service as module
    from app.core.exceptions import AppError

    clock = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    calls = 0

    async def upstream(text, language):
        nonlocal calls
        calls += 1
        if text == "fails":
            raise RuntimeError("service offline")
        return b"cached audio"

    monkeypatch.setattr(module, "synthesize_mp3", upstream)
    service = AudioService(AudioStore(tmp_path))
    await service.synthesize("cached", "vi")
    with pytest.raises(AppError, match="không khả dụng"):
        await service.synthesize("fails", "vi")
    with pytest.raises(AppError) as error:
        await service.synthesize("another article", "vi")
    assert error.value.code == "tts_cooldown"
    assert calls == 2
    assert (await service.synthesize("cached", "vi"))["cache_hit"]
    clock[0] += service.RETRY_COOLDOWN_SECONDS + 1
    assert not (await service.synthesize("another article", "vi"))["cache_hit"]
    assert calls == 3


@pytest.mark.asyncio
async def test_upstream_timeout_is_bounded_and_followed_by_cooldown(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import app.modules.audio.service as module
    from app.core.exceptions import AppError

    monkeypatch.setattr(module, "get_settings", lambda: SimpleNamespace(tts_timeout_s=0.01))

    async def stalled(*args):
        await asyncio.Event().wait()

    monkeypatch.setattr(module, "synthesize_mp3", stalled)
    service = AudioService(AudioStore(tmp_path))
    with pytest.raises(AppError) as error:
        await service.synthesize("new text", "vi")
    assert isinstance(error.value.__cause__, TimeoutError)
    with pytest.raises(AppError) as error:
        await service.synthesize("new text", "vi")
    assert error.value.code == "tts_cooldown"
