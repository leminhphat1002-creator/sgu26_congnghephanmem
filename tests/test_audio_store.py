import pytest

from app.modules.audio.store import AudioStore


def test_cache_key_is_stable(tmp_path):
    store = AudioStore(tmp_path)

    key1 = store.cache_key("Xin chào", "vi", "voice")
    key2 = store.cache_key("Xin chào", "vi", "voice")
    key3 = store.cache_key("Hello", "en", "voice")

    assert key1 == key2
    assert key1 != key3


def test_cache_miss_and_hit(tmp_path):
    store = AudioStore(tmp_path)
    key = store.cache_key("Hello", "en", "voice")

    assert store.read(key) is None

    store.write(key, b"fake-mp3-data")

    assert store.exists(key)
    assert store.read(key) == b"fake-mp3-data"


def test_reject_empty_data(tmp_path):
    store = AudioStore(tmp_path)
    key = store.cache_key("Hello", "en", "voice")

    with pytest.raises(ValueError):
        store.write(key, b"")


@pytest.mark.parametrize(
    "key",
    ["../secret", "invalid", "A" * 64, ""],
)
def test_reject_invalid_key(tmp_path, key):
    store = AudioStore(tmp_path)

    with pytest.raises(ValueError):
        store.read(key)


def test_empty_cache_file_is_treated_as_miss(tmp_path):
    store = AudioStore(tmp_path)
    key = store.cache_key("Hello", "en", "voice")

    (tmp_path / f"{key}.mp3").write_bytes(b"")

    assert store.read(key) is None
    assert not store.exists(key)


def test_write_replaces_existing_file(tmp_path):
    store = AudioStore(tmp_path)
    key = store.cache_key("Hello", "en", "voice")

    store.write(key, b"first")
    store.write(key, b"second")

    assert store.read(key) == b"second"
    assert list(tmp_path.glob(".audio-*.tmp")) == []
