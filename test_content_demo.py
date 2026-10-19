import asyncio

from app.modules.content.service import ContentService


async def main():
    service = ContentService()
    result = await service.get_content("Chợ Bến Thành", "vi")

    if result is None:
        print("Không tìm thấy nội dung.")
        return

    print("Tiêu đề:", result.get("title"))
    print("Ngôn ngữ:", result.get("language"))
    print("Có fallback không:", result.get("fallback_used"))
    print("Nội dung:", result.get("extract"))


if __name__ == "__main__":
    asyncio.run(main())
