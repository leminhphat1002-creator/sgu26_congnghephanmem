"""Lớp 3 (Data Access): client gọi Wikimedia API bằng httpx.

Nhiệm vụ: geosearch, extracts, langlinks với timeout hữu hạn, User-Agent từ cấu hình,
phân biệt lỗi upstream (timeout, rate_limited, upstream_error) với kết quả rỗng.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError

WIKIMEDIA_API = "https://{lang}.wikipedia.org/w/api.php"
SUPPORTED_LANGUAGES = {"vi", "en", "ja"}


class WikimediaClient:
    """Client truy vấn geosearch, extracts và liên kết ngôn ngữ."""

    def __init__(self, timeout: float | None = None) -> None:
        settings = get_settings()
        self.timeout = timeout if timeout is not None else settings.wikimedia_timeout_s
        self.user_agent = settings.wikimedia_user_agent

    async def _request(
        self,
        lang: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Gửi request và chuyển lỗi Wikimedia thành AppError."""
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError("Ngôn ngữ Wikimedia chưa được hỗ trợ")

        headers = {"User-Agent": self.user_agent}
        url = WIKIMEDIA_API.format(lang=lang)

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            ) as client:
                response = await client.get(
                    url,
                    params={
                        "format": "json",
                        "formatversion": 2,
                        **params,
                    },
                )

                if response.status_code == 429:
                    raise AppError(
                        "rate_limited",
                        "Wikimedia giới hạn số lượng yêu cầu",
                        503,
                    )

                response.raise_for_status()
                data = response.json()

        except AppError:
            raise
        except httpx.TimeoutException as exc:
            raise AppError(
                "timeout",
                "Wikimedia phản hồi quá thời gian cho phép",
                504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise AppError(
                    "rate_limited",
                    "Wikimedia giới hạn số lượng yêu cầu",
                    503,
                ) from exc

            raise AppError(
                "upstream_error",
                f"Wikimedia trả về HTTP {exc.response.status_code}",
                502,
            ) from exc
        except httpx.RequestError as exc:
            raise AppError(
                "upstream_error",
                "Không thể kết nối Wikimedia",
                502,
            ) from exc
        except ValueError as exc:
            raise AppError(
                "upstream_error",
                "Dữ liệu Wikimedia không phải JSON hợp lệ",
                502,
            ) from exc

        if not isinstance(data, dict):
            raise AppError(
                "upstream_error",
                "Dữ liệu Wikimedia không đúng định dạng",
                502,
            )

        if "error" in data:
            error = data["error"]

            if isinstance(error, dict) and error.get("code") in {
                "ratelimited",
                "maxlag",
            }:
                raise AppError(
                    "rate_limited",
                    "Wikimedia giới hạn số lượng yêu cầu",
                    429,
                )

            raise AppError(
                "upstream_error",
                "Wikimedia trả về lỗi API",
                502,
            )

        return data

    async def geosearch(
        self,
        latitude: float,
        longitude: float,
        radius: int = 10000,
        limit: int = 10,
        lang: str = "vi",
    ) -> list[dict[str, Any]]:
        """Tìm các trang Wikipedia gần tọa độ GPS."""
        if not -90 <= latitude <= 90:
            raise ValueError("Latitude phải nằm trong khoảng -90 đến 90")

        if not -180 <= longitude <= 180:
            raise ValueError("Longitude phải nằm trong khoảng -180 đến 180")

        if not 1 <= radius <= 10000:
            raise ValueError("Radius phải nằm trong khoảng 1 đến 10000")

        if not 1 <= limit <= 50:
            raise ValueError("Limit phải nằm trong khoảng 1 đến 50")

        data = await self._request(
            lang,
            {
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{latitude}|{longitude}",
                "gsradius": radius,
                "gsnamespace": 0,
                "gsprop": "type|name|dim",
                "gslimit": limit,
            },
        )

        query = data.get("query", {})
        results = query.get("geosearch", []) if isinstance(query, dict) else []

        return results if isinstance(results, list) else []

    async def get_extract(
        self,
        title: str,
        lang: str = "vi",
    ) -> dict[str, Any] | None:
        """Lấy nội dung Wikipedia, hỗ trợ tên không phân biệt hoa thường."""
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Title không được để trống")

        title = title.strip()

        async def fetch_page(page_title: str) -> dict[str, Any] | None:
            data = await self._request(
                lang,
                {
                    "action": "query",
                    "prop": "extracts|info",
                    "exintro": 1,
                    "explaintext": 1,
                    "inprop": "url",
                    "redirects": 1,
                    "titles": page_title,
                },
            )

            query = data.get("query", {})
            pages = query.get("pages", []) if isinstance(query, dict) else []

            if not isinstance(pages, list) or not pages:
                return None

            page = pages[0]

            if not isinstance(page, dict) or page.get("missing"):
                return None

            return {
                "page_id": page.get("pageid"),
                "title": page.get("title", page_title),
                "extract": page.get("extract", ""),
                "url": page.get("fullurl"),
            }

        # Thử truy xuất trang theo tiêu đề nhập vào.
        page = await fetch_page(title)

        if page is not None:
            return page

        # Nếu không tìm thấy, sử dụng Wikimedia Search API.
        search_data = await self._request(
            lang,
            {
                "action": "query",
                "list": "search",
                "srsearch": title,
                "srnamespace": 0,
                "srlimit": 10,
            },
        )

        query = search_data.get("query", {})
        results = query.get("search", []) if isinstance(query, dict) else []

        if not isinstance(results, list):
            return None

        # Chỉ chấp nhận kết quả trùng tên khi bỏ qua hoa/thường.
        for result in results:
            if not isinstance(result, dict):
                continue

            candidate = result.get("title", "")

            if isinstance(candidate, str) and candidate.casefold() == title.casefold():
                return await fetch_page(candidate)

        return None

    async def get_langlinks(
        self,
        page_id: int,
        source_lang: str = "vi",
        target_lang: str = "en",
    ) -> str | None:
        """Tìm tiêu đề trang tương ứng trong ngôn ngữ đích."""
        if page_id < 1:
            raise ValueError("page_id phải lớn hơn 0")

        if source_lang not in SUPPORTED_LANGUAGES:
            raise ValueError("Ngôn ngữ nguồn chưa được hỗ trợ")

        if target_lang not in SUPPORTED_LANGUAGES:
            raise ValueError("Ngôn ngữ đích chưa được hỗ trợ")

        data = await self._request(
            source_lang,
            {
                "action": "query",
                "prop": "langlinks",
                "pageids": page_id,
                "lllang": target_lang,
                "lllimit": 1,
            },
        )

        query = data.get("query", {})
        pages = query.get("pages", []) if isinstance(query, dict) else []

        if not isinstance(pages, list) or not pages:
            return None

        page = pages[0]

        if not isinstance(page, dict):
            return None

        links = page.get("langlinks", [])

        if not isinstance(links, list) or not links:
            return None

        link = links[0]

        return link.get("title") if isinstance(link, dict) else None
