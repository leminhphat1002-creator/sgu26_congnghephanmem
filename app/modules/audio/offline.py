"""Giọng Piper tại máy chủ: phát từng đoạn và lưu cache, không gọi mạng."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import threading
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import anyio

from app.core.exceptions import AppError
from app.modules.audio.service import AudioService
from app.modules.audio.store import AudioStore

MANIFEST_PATH = Path(__file__).with_name("offline_voices.json")
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[3] / "tts_models"


class OfflineSpeech:
    def __init__(self, store: AudioStore, model_dir: Path | None = None) -> None:
        self.store = store
        self.model_dir = model_dir or Path(os.environ.get("PIPER_MODEL_DIR") or DEFAULT_MODEL_DIR)
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self._verified: set[str] = set()
        self._voices: dict = {}
        self._guard = threading.Lock()
        self._setup_guard = threading.Lock()
        self._stream_slot = asyncio.Lock()

    def cache_key(self, text: str, language: str) -> str:
        voice = self.manifest["voices"].get(language)
        if voice is None:
            raise ValueError("Ngôn ngữ không được hỗ trợ")
        identity = f"piper-1.8.0:{voice['files'][0]['sha256']}:mp3-v1"
        return self.store.cache_key(AudioService.normalize_text(text), language, identity)

    def check(self, language: str) -> None:
        """Chỉ kiểm tra file cục bộ; không tự tải tài nguyên khi khách truy cập."""
        if language not in self.manifest["voices"]:
            raise ValueError("Ngôn ngữ không được hỗ trợ")
        with self._setup_guard:
            if language in self._verified:
                return
            packages = ["piper", "lameenc"] + (["pyopenjtalk"] if language == "ja" else [])
            if any(importlib.util.find_spec(package) is None for package in packages):
                raise AppError("offline_tts_setup", "Máy chủ chưa cài đủ bộ đọc cục bộ.", 503)
            for entry in self.manifest["voices"][language]["files"]:
                path = self.model_dir / entry["filename"]
                if not path.is_file():
                    raise AppError("offline_tts_setup", "Máy chủ chưa có mô hình giọng đọc.", 503)
                with path.open("rb") as stream:
                    actual = hashlib.file_digest(stream, "sha256").hexdigest()
                if actual != entry["sha256"]:
                    raise AppError(
                        "offline_tts_setup", "Mô hình giọng đọc không đúng checksum.", 503
                    )
            self._verified.add(language)

    def _load_voice(self, language: str):
        if language not in self._voices:
            import onnxruntime
            from piper import PiperVoice
            from piper.config import PiperConfig

            self.check(language)
            model = self.model_dir / self.manifest["voices"][language]["files"][0]["filename"]
            config = json.loads(model.with_suffix(".onnx.json").read_text(encoding="utf-8"))
            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            onnxruntime.disable_telemetry_events()
            self._voices[language] = PiperVoice(
                config=PiperConfig.from_dict(config),
                session=onnxruntime.InferenceSession(
                    str(model), sess_options=options, providers=["CPUExecutionProvider"]
                ),
            )
        return self._voices[language]

    def stream(self, text: str, language: str) -> Iterator[bytes]:
        """Mỗi câu được mã hóa và gửi ngay; chỉ lưu cache khi bài hoàn tất."""
        import lameenc

        normalized = AudioService.normalize_text(text)
        key = self.cache_key(normalized, language)
        # Khóa đồng bộ được giữ trong worker, không chặn event loop phục vụ bài viết/GPS.
        with self._guard:
            cached = self.store.read(key)
            if cached:
                yield cached
                return
            voice = self._load_voice(language)
            encoder = lameenc.Encoder()
            encoder.set_bit_rate(64)
            encoder.set_in_sample_rate(voice.config.sample_rate)
            encoder.set_channels(1)
            encoder.set_quality(2)
            pieces = []
            for chunk in voice.synthesize(normalized):
                encoded = bytes(encoder.encode(chunk.audio_int16_bytes))
                if encoded:
                    pieces.append(encoded)
                    yield encoded
            final = bytes(encoder.flush())
            if final:
                pieces.append(final)
                yield final
            if not pieces:
                raise RuntimeError("Bộ đọc cục bộ không tạo được âm thanh")
            self.store.write(key, b"".join(pieces))

    async def stream_async(self, text: str, language: str) -> AsyncIterator[bytes]:
        # Chờ lượt trên event loop, không chiếm hết worker khi nhiều khách cùng nghe.
        async with self._stream_slot:
            iterator = self.stream(text, language)
            try:
                while (part := await anyio.to_thread.run_sync(next, iterator, None)) is not None:
                    yield part
            finally:
                iterator.close()
