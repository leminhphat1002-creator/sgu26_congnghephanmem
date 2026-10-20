from unittest.mock import AsyncMock

import pytest

from app.modules.content.service import ContentService


@pytest.fixture
def client():
    mock = AsyncMock()
    return mock


@pytest.fixture
def service(client):
    return ContentService(client=client)


def test_clean_text_normalizes_whitespace():
    assert ContentService.clean_text("  Xin \n chào   bạn  ") == "Xin chào bạn"


def test_shorten_text_keeps_short_text():
    text = "Đây là một địa điểm du lịch."
    assert ContentService.shorten_text(text) == text


def test_shorten_text_limits_long_text():
    text = ("Đây là một câu mô tả địa điểm. " * 50).strip()

    result = ContentService.shorten_text(text)

    assert len(result) <= ContentService.MAX_EXTRACT_LENGTH
    assert result


@pytest.mark.asyncio
async def test_get_content_uses_requested_language(service, client):
    client.get_extract.return_value = {
        "page_id": 1,
        "title": "Chợ Bến Thành",
        "extract": "Một khu chợ nổi tiếng.",
        "url": "https://vi.wikipedia.org/",
    }

    result = await service.get_content("Chợ Bến Thành", "vi")

    assert result is not None
    assert result["language"] == "vi"
    assert result["requested_language"] == "vi"
    assert result["fallback_used"] is False
    client.get_extract.assert_awaited_once_with("Chợ Bến Thành", "vi")


@pytest.mark.asyncio
async def test_get_content_falls_back_to_english(service, client):
    """Nếu không có nội dung Nhật, thử tiếng Anh."""

    async def fake_extract(title, lang):
        if lang == "en":
            return {
                "page_id": 2,
                "title": "Ben Thanh Market",
                "extract": "A famous market in Ho Chi Minh City.",
                "url": "https://en.wikipedia.org/",
            }
        return None

    client.get_extract.side_effect = fake_extract

    result = await service.get_content("Chợ Bến Thành", "ja")

    assert result is not None
    assert result["language"] == "en"
    assert result["requested_language"] == "ja"
    assert result["fallback_used"] is True
    assert client.get_extract.await_count == 3


@pytest.mark.asyncio
async def test_get_content_returns_none_when_all_languages_missing(service, client):
    client.get_extract.return_value = None

    result = await service.get_content("Không tồn tại", "vi")

    assert result is None
    assert client.get_extract.await_count == 2


@pytest.mark.asyncio
async def test_get_content_rejects_empty_title(service):
    with pytest.raises(ValueError, match="không được để trống"):
        await service.get_content("   ")


@pytest.mark.asyncio
async def test_get_content_rejects_unsupported_language(service):
    with pytest.raises(ValueError, match="chưa được hỗ trợ"):
        await service.get_content("Test", "fr")


@pytest.mark.asyncio
async def test_search_nearby_delegates_to_client(service, client):
    client.geosearch.return_value = [{"title": "Chợ Bến Thành"}]

    result = await service.search_nearby(10.77, 106.70)

    assert result == [{"title": "Chợ Bến Thành"}]
    client.geosearch.assert_awaited_once_with(
        latitude=10.77,
        longitude=106.70,
        radius=10000,
        limit=10,
        lang="vi",
    )


@pytest.mark.asyncio
async def test_get_translation_title_delegates_to_client(service, client):
    client.get_langlinks.return_value = "Ben Thanh Market"

    result = await service.get_translation_title(1, "vi", "en")

    assert result == "Ben Thanh Market"
    client.get_langlinks.assert_awaited_once_with(
        page_id=1,
        source_lang="vi",
        target_lang="en",
    )


@pytest.mark.asyncio
async def test_get_content_japanese_via_langlinks(service, client):
    """Tìm đúng bài Nhật thông qua liên kết từ Wikipedia Việt."""

    async def fake_extract(title, lang):
        if lang == "vi" and title == "Dinh Độc Lập":
            return {
                "page_id": 123,
                "title": "Dinh Độc Lập",
                "extract": "Một công trình lịch sử.",
                "url": "https://vi.wikipedia.org/wiki/Dinh",
            }

        if lang == "ja" and title == "統一会堂":
            return {
                "page_id": 456,
                "title": "統一会堂",
                "extract": "ベトナムのホーチミン市にある歴史的建造物です。",
                "url": "https://ja.wikipedia.org/wiki/統一会堂",
            }

        return None

    client.get_extract.side_effect = fake_extract
    client.get_langlinks.return_value = "統一会堂"

    result = await service.get_content("Dinh Độc Lập", "ja")

    assert result is not None
    assert result["language"] == "ja"
    assert result["requested_language"] == "ja"
    assert result["fallback_used"] is False
    assert result["title"] == "統一会堂"

    client.get_langlinks.assert_awaited_once_with(
        page_id=123,
        source_lang="vi",
        target_lang="ja",
    )


@pytest.mark.asyncio
async def test_japanese_missing_langlink_uses_english(service, client):
    """Không có trang Nhật tương ứng thì fallback tiếng Anh."""

    async def fake_extract(title, lang):
        if lang == "vi":
            return {
                "page_id": 123,
                "title": "Dinh Độc Lập",
                "extract": "Một công trình lịch sử.",
                "url": "https://vi.wikipedia.org/wiki/Dinh",
            }

        if lang == "en" and title == "Reunification Palace":
            return {
                "page_id": 789,
                "title": "Reunification Palace",
                "extract": "A historic landmark in Ho Chi Minh City.",
                "url": "https://en.wikipedia.org/wiki/Reunification_Palace",
            }

        return None

    async def fake_langlinks(page_id, source_lang, target_lang):
        if target_lang == "en":
            return "Reunification Palace"
        return None

    client.get_extract.side_effect = fake_extract
    client.get_langlinks.side_effect = fake_langlinks

    result = await service.get_content("Dinh Độc Lập", "ja")

    assert result is not None
    assert result["language"] == "en"
    assert result["requested_language"] == "ja"
    assert result["fallback_used"] is True
