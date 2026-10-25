"""Tạo trước giọng đọc cục bộ từ bài trong DB để khách nghe ngay từ cache.

Chạy: python -m scripts.prepare_narration_audio
Không sửa DB; bỏ qua bài đã có. Không gọi dịch vụ giọng đọc Internet.
"""

import asyncio

from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.audio.offline import OfflineSpeech
from app.modules.audio.service import AudioService
from app.modules.content.models import PoiNarration
from app.modules.content.service import ContentService
from app.modules.poi.models import Location


async def main() -> int:
    service = AudioService()
    speech = OfflineSpeech(service.store)
    with get_sessionmaker()() as session:
        rows = session.scalars(
            select(PoiNarration)
            .join(Location, Location.id == PoiNarration.location_id)
            .where(Location.is_ready.is_(True))
            .order_by(PoiNarration.location_id, PoiNarration.language)
        ).all()
    failed = 0
    for row in rows:
        if row.language not in speech.manifest["voices"] or not row.content.strip():
            continue
        text = service.normalize_text(ContentService.shorten_text(row.content))
        key = speech.cache_key(text, row.language)
        label = f"POI {row.location_id} / {row.language}"
        if speech.store.exists(key):
            print(f"{label}: cached", flush=True)
            continue
        try:
            audio = await asyncio.to_thread(b"".join, speech.stream(text, row.language))
            print(f"{label}: ready locally ({len(audio)} bytes)", flush=True)
        except Exception as exc:
            failed += 1
            print(f"{label}: failed ({type(exc).__name__}); rerun later", flush=True)
    print(f"Finished. Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
