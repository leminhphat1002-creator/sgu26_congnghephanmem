import pytest

from app.modules.audio.tts_client import VOICE_BY_LANGUAGE, synthesize_mp3


@pytest.mark.parametrize("language", ["vi", "en", "ja"])
def test_voice_mapping(language):
    assert VOICE_BY_LANGUAGE[language]


@pytest.mark.asyncio
async def test_unsupported_language():
    with pytest.raises(ValueError, match="chưa được hỗ trợ"):
        await synthesize_mp3("Hello", "fr")


@pytest.mark.asyncio
async def test_empty_text():
    with pytest.raises(ValueError, match="không được để trống"):
        await synthesize_mp3("   ", "en")


@pytest.mark.asyncio
async def test_invalid_timeout():
    with pytest.raises(ValueError, match="Timeout"):
        await synthesize_mp3("Hello", "en", timeout=0)
