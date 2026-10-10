"""Cấu hình Alembic: lấy DATABASE_URL từ môi trường, dùng metadata của app."""

from __future__ import annotations

from alembic import context

from app.core.config import Settings
from app.core.db import Base, create_db_engine

# Import model để Base.metadata biết các bảng (autogenerate và kiểm tra schema).
from app.modules.poi import models as _poi_models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    # Đọc mới từ môi trường (không cache) để test và deploy đổi được DATABASE_URL.
    return Settings.from_env().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_db_engine(_database_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite cần batch mode để ALTER TABLE.
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
