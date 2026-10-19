[1mdiff --git a/app/modules/audio/service.py b/app/modules/audio/service.py[m
[1mindex c50f382..01e4633 100644[m
[1m--- a/app/modules/audio/service.py[m
[1m+++ b/app/modules/audio/service.py[m
[36m@@ -1,22 +1,23 @@[m
[31m-"""Lớp 2 (Business) của audio.[m
[31m-[m
[31m-Nhiệm vụ: synthesize(text, lang) có cache (chuẩn hóa văn bản, tính key, cache hit/miss,[m
[31m-khóa theo key), lỗi tts_unavailable. audio không import module nào khác. (Viết ở Tuần 3.)"""[m
[32m+[m[32m"""Lớp 2 (Business) của audio: tạo giọng nói và quản lý cache MP3."""[m
 [m
 from __future__ import annotations[m
 [m
 import asyncio[m
[32m+[m[32mimport hashlib[m
 import logging[m
 import re[m
 [m
[32m+[m[32mfrom app.core.exceptions import AppError[m
 from app.modules.audio.store import AudioStore[m
 from app.modules.audio.tts_client import VOICE_BY_LANGUAGE, synthesize_mp3[m
 [m
 logger = logging.getLogger(__name__)[m
 [m
[32m+[m[32mMAX_TEXT_LENGTH = 1200[m
[32m+[m
 [m
 class AudioService:[m
[31m-    """Generate speech and cache MP3 files."""[m
[32m+[m[32m    """Tạo giọng nói, quản lý cache và tránh tạo trùng MP3."""[m
 [m
     def __init__(self, store: AudioStore | None = None) -> None:[m
         self.store = store or AudioStore()[m
[36m@@ -25,54 +26,82 @@[m [mclass AudioService:[m
 [m
     @staticmethod[m
     def normalize_text(text: str) -> str:[m
[32m+[m[32m        """Chuẩn hóa khoảng trắng và kiểm tra giới hạn văn bản."""[m
         if not isinstance(text, str):[m
             raise ValueError("Văn bản không hợp lệ")[m
[31m-        return re.sub(r"\s+", " ", text).strip()[m
[32m+[m
[32m+[m[32m        normalized = re.sub(r"\s+", " ", text).strip()[m
[32m+[m
[32m+[m[32m        if not normalized:[m
[32m+[m[32m            raise ValueError("Văn bản không được để trống")[m
[32m+[m
[32m+[m[32m        if len(normalized) > MAX_TEXT_LENGTH:[m
[32m+[m[32m            raise ValueError(f"Văn bản không được vượt quá {MAX_TEXT_LENGTH} ký tự")[m
[32m+[m
[32m+[m[32m        return normalized[m
 [m
     async def _get_lock(self, key: str) -> asyncio.Lock:[m
[32m+[m[32m        """Lấy khóa riêng cho từng cache key."""[m
         async with self._locks_guard:[m
             if key not in self._locks:[m
                 self._locks[key] = asyncio.Lock()[m
             return self._locks[key][m
 [m
     async def synthesize(self, text: str, lang: str = "vi") -> dict:[m
[32m+[m[32m        """Tạo MP3 hoặc trả về kết quả từ cache."""[m
         normalized = self.normalize_text(text)[m
[31m-        if not normalized:[m
[31m-            raise ValueError("Văn bản không được để trống")[m
 [m
         if not isinstance(lang, str):[m
             raise ValueError("Ngôn ngữ không hợp lệ")[m
 [m
         language = lang.lower()[m
[32m+[m
         if language not in VOICE_BY_LANGUAGE:[m
             raise ValueError(f"Ngôn ngữ chưa được hỗ trợ: {language}")[m
 [m
         voice = VOICE_BY_LANGUAGE[language][m
[32m+[m[32m        text_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[m
         key = self.store.cache_key(normalized, language, voice)[m
         lock = await self._get_lock(key)[m
 [m
         async with lock:[m
             cached = self.store.read(key)[m
[32m+[m
             if cached is not None:[m
                 return {[m
[31m-                    "cache_key": key,[m
[32m+[m[32m                    "lang": language,[m
                     "language": language,[m
[32m+[m[32m                    "voice": voice,[m
[32m+[m[32m                    "text_hash": text_hash,[m
[32m+[m[32m                    "audio_filename": f"{key}.mp3",[m
[32m+[m[32m                    "cache_key": key,[m
                     "audio": cached,[m
                     "cache_hit": True,[m
                 }[m
 [m
             try:[m
                 audio = await synthesize_mp3(normalized, language)[m
[32m+[m
                 if not audio:[m
                     raise RuntimeError("TTS không trả về dữ liệu âm thanh")[m
 [m
[31m-                self.store.write(key, audio)[m
[32m+[m[32m                path = self.store.write(key, audio)[m
[32m+[m
                 return {[m
[31m-                    "cache_key": key,[m
[32m+[m[32m                    "lang": language,[m
                     "language": language,[m
[32m+[m[32m                    "voice": voice,[m
[32m+[m[32m                    "text_hash": text_hash,[m
[32m+[m[32m                    "audio_filename": path.name,[m
[32m+[m[32m                    "cache_key": key,[m
                     "audio": audio,[m
                     "cache_hit": False,[m
                 }[m
[32m+[m
             except Exception as exc:[m
[31m-                logger.exception("Không thể tạo âm thanh bằng TTS")[m
[31m-                raise RuntimeError("tts_unavailable") from exc[m
[32m+[m[32m                logger.exception("Không thể tạo hoặc lưu âm thanh bằng TTS")[m
[32m+[m[32m                raise AppError([m
[32m+[m[32m                    "tts_unavailable",[m
[32m+[m[32m                    "Dịch vụ tạo giọng nói hiện không khả dụng",[m
[32m+[m[32m                    status_code=503,[m
[32m+[m[32m                ) from exc[m
[1mdiff --git a/app/modules/poi/repository.py b/app/modules/poi/repository.py[m
[1mindex c909b32..55d2a23 100644[m
[1m--- a/app/modules/poi/repository.py[m
[1m+++ b/app/modules/poi/repository.py[m
[36m@@ -100,3 +100,17 @@[m [mdef find_in_bounding_box([m
         .order_by(Location.id)[m
     )[m
     return list(session.scalars(statement).all())[m
[32m+[m
[32m+[m
[32m+[m[32mdef get_location_by_source_page([m
[32m+[m[32m    session: Session,[m
[32m+[m[32m    source_lang: str,[m
[32m+[m[32m    source_page_id: int,[m
[32m+[m[32m) -> Location | None:[m
[32m+[m[32m    """Find a Wikimedia location by source language and page ID."""[m
[32m+[m[32m    statement = select(Location).where([m
[32m+[m[32m        Location.source == "wikimedia",[m
[32m+[m[32m        Location.source_lang == source_lang,[m
[32m+[m[32m        Location.source_page_id == source_page_id,[m
[32m+[m[32m    )[m
[32m+[m[32m    return session.scalars(statement).first()[m
[1mdiff --git a/app/modules/poi/schemas.py b/app/modules/poi/schemas.py[m
[1mindex ec0e1aa..d737c97 100644[m
[1m--- a/app/modules/poi/schemas.py[m
[1m+++ b/app/modules/poi/schemas.py[m
[36m@@ -18,7 +18,7 @@[m [mclass LocationCreate(BaseModel):[m
     source: str = "manual"[m
     source_lang: str | None = None[m
     source_title: str | None = None[m
[31m-    source_page_id: str | None = None[m
[32m+[m[32m    source_page_id: int | None = None[m
     source_url: str | None = None[m
     is_ready: bool = False[m
 [m
[36m@@ -58,7 +58,7 @@[m [mclass LocationUpdate(BaseModel):[m
     source: str | None = None[m
     source_lang: str | None = None[m
     source_title: str | None = None[m
[31m-    source_page_id: str | None = None[m
[32m+[m[32m    source_page_id: int | None = None[m
     source_url: str | None = None[m
     is_ready: bool | None = None[m
 [m
[1mdiff --git a/tests/test_audio_service.py b/tests/test_audio_service.py[m
[1mindex f87f09d..edf9712 100644[m
[1m--- a/tests/test_audio_service.py[m
[1m+++ b/tests/test_audio_service.py[m
[36m@@ -1,3 +1,5 @@[m
[32m+[m[32mimport asyncio[m
[32m+[m
 import pytest[m
 [m
 from app.modules.audio.service import AudioService[m
[36m@@ -46,6 +48,7 @@[m [masync def test_synthesize_rejects_unsupported_language(tmp_path):[m
 @pytest.mark.asyncio[m
 async def test_synthesize_reports_tts_unavailable(tmp_path, monkeypatch):[m
     import app.modules.audio.service as module[m
[32m+[m[32m    from app.core.exceptions import AppError[m
 [m
     async def fake_synthesize_mp3(text, language):[m
         raise RuntimeError("upstream failure")[m
[36m@@ -53,5 +56,70 @@[m [masync def test_synthesize_reports_tts_unavailable(tmp_path, monkeypatch):[m
     monkeypatch.setattr(module, "synthesize_mp3", fake_synthesize_mp3)[m
     service = AudioService(AudioStore(tmp_path))[m
 [m
[31m-    with pytest.raises(RuntimeError, match="tts_unavailable"):[m
[32m+[m[32m    with pytest.raises(AppError) as exc_info:[m
         await service.synthesize("Xin chào")[m
[32m+[m
[32m+[m[32m    assert exc_info.value.code == "tts_unavailable"[m
[32m+[m[32m    assert exc_info.value.status_code == 503[m
[32m+[m
[32m+[m
[32m+[m[32m@pytest.mark.asyncio[m
[32m+[m[32masync def test_synthesize_regenerates_audio_when_cache_file_is_deleted(tmp_path, monkeypatch):[m
[32m+[m[32m    import app.modules.audio.service as module[m
[32m+[m
[32m+[m[32m    calls = 0[m
[32m+[m
[32m+[m[32m    async def fake_synthesize_mp3(text, language):[m
[32m+[m[32m        nonlocal calls[m
[32m+[m[32m        calls += 1[m
[32m+[m[32m        return b"fake-mp3"[m
[32m+[m
[32m+[m[32m    monkeypatch.setattr(module, "synthesize_mp3", fake_synthesize_mp3)[m
[32m+[m
[32m+[m[32m    store = AudioStore(tmp_path)[m
[32m+[m[32m    service = AudioService(store)[m
[32m+[m
[32m+[m[32m    first = await service.synthesize("Xin chao", "vi")[m
[32m+[m[32m    assert first["cache_hit"] is False[m
[32m+[m[32m    assert calls == 1[m
[32m+[m
[32m+[m[32m    # Xóa file cache để mô phỏng cache bị mất.[m
[32m+[m[32m    cache_path = tmp_path / f"{first['cache_key']}.mp3"[m
[32m+[m[32m    assert cache_path.is_file()[m
[32m+[m[32m    cache_path.unlink()[m
[32m+[m
[32m+[m[32m    second = await service.synthesize("Xin chao", "vi")[m
[32m+[m
[32m+[m[32m    assert second["cache_hit"] is False[m
[32m+[m[32m    assert second["audio"] == b"fake-mp3"[m
[32m+[m[32m    assert calls == 2[m
[32m+[m[32m    assert cache_path.is_file()[m
[32m+[m
[32m+[m
[32m+[m[32m@pytest.mark.asyncio[m
[32m+[m[32masync def test_concurrent_requests_generate_audio_only_once(tmp_path, monkeypatch):[m
[32m+[m[32m    import app.modules.audio.service as module[m
[32m+[m
[32m+[m[32m    calls = 0[m
[32m+[m
[32m+[m[32m    async def fake_synthesize_mp3(text, language):[m
[32m+[m[32m        nonlocal calls[m
[32m+[m[32m        calls += 1[m
[32m+[m[32m        await asyncio.sleep(0.05)[m
[32m+[m[32m        return b"fake-mp3"[m
[32m+[m
[32m+[m[32m    monkeypatch.setattr(module, "synthesize_mp3", fake_synthesize_mp3)[m
[32m+[m[32m    service = AudioService(AudioStore(tmp_path))[m
[32m+[m
[32m+[m[32m    first, second = await asyncio.gather([m
[32m+[m[32m        service.synthesize("Xin chao", "vi"),[m
[32m+[m[32m        service.synthesize("Xin chao", "vi"),[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m[32m    assert calls == 1[m
[32m+[m[32m    assert first["audio"] == b"fake-mp3"[m
[32m+[m[32m    assert second["audio"] == b"fake-mp3"[m
[32m+[m[32m    assert sorted([first["cache_hit"], second["cache_hit"]]) == [[m
[32m+[m[32m        False,[m
[32m+[m[32m        True,[m
[32m+[m[32m    ][m
