"""Backup/restore SQLite nhất quán khi triển khai; không copy DB đang ghi bằng cp."""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import get_settings


def snapshot(database: Path, destination: Path) -> bool:
    if not database.is_file():
        return False
    if destination.exists():
        raise FileExistsError("Snapshot already exists; refusing to overwrite it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as source:
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Snapshot integrity check failed")
    return True


def restore(database: Path, source: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError("Snapshot not found")
    if source.resolve() == database.resolve():
        raise ValueError("Source and database must be different")
    with closing(sqlite3.connect(source)) as saved:
        if saved.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Snapshot integrity check failed")
        database.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database)) as target:
            saved.backup(target)


def main():
    parser = argparse.ArgumentParser(description="Deployment database snapshot")
    parser.add_argument("operation", choices=("backup", "restore"))
    parser.add_argument("filename", help="Snapshot filename inside the database backups directory")
    args = parser.parse_args()
    if Path(args.filename).name != args.filename or not args.filename.endswith(".db"):
        parser.error("Use a .db filename, without directory components")
    url = make_url(get_settings().database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        parser.error("A file-based SQLite database is required")
    database = Path(url.database).resolve()
    backup = database.parent / "backups" / args.filename
    if args.operation == "backup":
        print("created" if snapshot(database, backup) else "skipped")
    else:
        restore(database, backup)
        print("restored")


if __name__ == "__main__":
    main()
