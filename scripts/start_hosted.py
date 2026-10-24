"""Bootstrap PostgreSQL tùy chọn trên Windows; triển khai mặc định dùng SQLite."""

import os
import subprocess
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import create_db_engine
from app.modules.admin.models import AdminUser, AppSetting
from app.modules.admin.passwords import hash_password
from scripts.seed_bat_trang import seed


def initialize(session: Session, username: str, password: str | None, demo: bool):
    if not session.scalar(select(func.count()).select_from(AdminUser)):
        if not password:
            raise ValueError("Set INITIAL_ADMIN_PASSWORD in the hosting secret environment first")
        if not username.strip() or len(username.strip()) > 80:
            raise ValueError("INITIAL_ADMIN_USERNAME must have 1-80 characters")
        session.add(AdminUser(username=username.strip(), password_hash=hash_password(password)))
        session.commit()
    if demo and session.get(AppSetting, "initial_bat_trang_seed") is None:
        seed(session)
        session.add(AppSetting(key="initial_bat_trang_seed", value="done"))
        session.commit()


def prepare_database():
    settings = Settings.from_env()
    engine = create_db_engine(settings.database_url)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise ValueError("This optional bootstrap requires PostgreSQL")
    # Khóa giao dịch tránh hai process bootstrap đồng thời.
    try:
        with engine.connect() as lock:
            lock.execute(text("SELECT pg_advisory_xact_lock(20261025)"))
            root = Path(__file__).resolve().parents[1]
            config = Config(str(root / "alembic.ini"))
            config.set_main_option("script_location", str(root / "migrations"))
            command.upgrade(config, "head")
            with Session(engine) as session:
                initialize(
                    session,
                    os.environ.get("INITIAL_ADMIN_USERNAME", "admin"),
                    os.environ.get("INITIAL_ADMIN_PASSWORD"),
                    os.environ.get("SEED_DEMO_DATA", "false").lower() == "true",
                )
    finally:
        engine.dispose()


def main():
    port = int(os.environ.get("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid PORT")
    prepare_database()
    os.environ.pop("INITIAL_ADMIN_PASSWORD", None)
    print("Hosted database initialized; starting web service.", flush=True)
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--proxy-headers",
            "--forwarded-allow-ips",
            os.environ.get("TRUSTED_PROXY_IPS", "127.0.0.1"),
        ],
    )


if __name__ == "__main__":
    raise SystemExit(main())
