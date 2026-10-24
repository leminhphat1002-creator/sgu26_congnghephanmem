"""Nghiệp vụ quản trị và thống kê."""

from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.admin.repository import AdminRepository
from app.modules.poi import repository as poi_repository


class AdminService:
    def __init__(self, repository: AdminRepository):
        self.repository = repository

    def require_location(self, location_id: int):
        if poi_repository.get_location(self.repository.session, location_id) is None:
            raise AppError("location_not_found", "Không tìm thấy địa điểm.", 404)

    def save_narration(self, location_id: int, language: str, title: str, content: str, actor: str):
        self.require_location(location_id)
        self.repository.save_narration(location_id, language, title, content)
        self.repository.record(actor, "save_narration", f"{location_id}/{language}")

    def dashboard(self):
        result = self.repository.dashboard()
        files = list(Path(get_settings().audio_dir).glob("*.mp3"))
        result["audio_files"] = len(files)
        result["audio_bytes"] = sum(path.stat().st_size for path in files if path.is_file())
        result["missing_translations"] = sum(
            3 - len(set(row["languages"]) & {"vi", "en", "ja"})
            for row in self.repository.locations()
        )
        return result
