from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import AppError
from app.modules.content.wikimedia_client import WikimediaClient


@pytest.fixture
def client() -> WikimediaClient:
    return WikimediaClient(timeout=2.0)


@pytest.mark.asyncio
async def test_geosearch_returns_results(client: WikimediaClient) -> None:
    payload = {
        "query": {
            "geosearch": [{"pageid": 1, "title": "Chợ Bến Thành", "lat": 10.77, "lon": 106.70}]
        }
    }

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload

    with patch("app.modules.content.wikimedia_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=response)

        results = await client.geosearch(10.77, 106.70)

    assert len(results) == 1
    assert results[0]["title"] == "Chợ Bến Thành"


@pytest.mark.asyncio
async def test_geosearch_rejects_invalid_coordinates(
    client: WikimediaClient,
) -> None:
    with pytest.raises(ValueError, match="Latitude"):
        await client.geosearch(100, 106.70)


@pytest.mark.asyncio
async def test_get_extract_returns_page(client: WikimediaClient) -> None:
    payload = {
        "query": {
            "pages": [
                {
                    "pageid": 10,
                    "title": "Chợ Bến Thành",
                    "extract": "Một khu chợ tại Thành phố Hồ Chí Minh.",
                    "fullurl": "https://vi.wikipedia.org/wiki/Ch%E1%BB%A3_B%E1%BA%BFn_Th%C3%A0nh",
                }
            ]
        }
    }

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload

    with patch("app.modules.content.wikimedia_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=response)

        result = await client.get_extract("Chợ Bến Thành")

    assert result is not None
    assert result["page_id"] == 10
    assert result["extract"] == "Một khu chợ tại Thành phố Hồ Chí Minh."


@pytest.mark.asyncio
async def test_get_extract_returns_none_when_page_missing(
    client: WikimediaClient,
) -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"query": {"pages": [{"missing": True}]}}

    with patch("app.modules.content.wikimedia_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=response)

        result = await client.get_extract("Trang không tồn tại")

    assert result is None


@pytest.mark.asyncio
async def test_get_langlinks_returns_target_title(
    client: WikimediaClient,
) -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "query": {"pages": [{"langlinks": [{"lang": "en", "title": "Ben Thanh Market"}]}]}
    }

    with patch("app.modules.content.wikimedia_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=response)

        result = await client.get_langlinks(10, "vi", "en")

    assert result == "Ben Thanh Market"


@pytest.mark.asyncio
async def test_wikimedia_timeout_raises_app_error(
    client: WikimediaClient,
) -> None:
    with patch("app.modules.content.wikimedia_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )

        with pytest.raises(AppError) as exc_info:
            await client.geosearch(10.77, 106.70)

    assert exc_info.value.code == "timeout"
    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_wikimedia_rate_limit_raises_app_error(
    client: WikimediaClient,
) -> None:
    response = MagicMock()
    response.status_code = 429

    with patch("app.modules.content.wikimedia_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=response)

        with pytest.raises(AppError) as exc_info:
            await client.geosearch(10.77, 106.70)

    assert exc_info.value.code == "rate_limited"
    assert exc_info.value.status_code == 503
