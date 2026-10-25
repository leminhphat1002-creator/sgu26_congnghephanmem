"""Validated Windows launch configuration; never migrate, seed or download on startup."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "PORT": 8010,
    "BIND_HOST": "127.0.0.1",
    "PUBLIC_BASE_URL": "",
    "DATABASE_URL": "sqlite:///./data/app.db",
    "AUDIO_DIR": "./audio_files",
    "PIPER_MODEL_DIR": "./tts_models",
    "TRUSTED_PROXY_IPS": "127.0.0.1",
}


def load_configuration(root: Path, filename: Path, environment: dict, overrides: dict) -> dict:
    """Defaults < JSON < process environment < explicit command arguments."""
    from sqlalchemy.engine import make_url

    from app.core.config import normalize_database_url

    config = DEFAULTS.copy()
    if filename.exists():
        saved = json.loads(filename.read_text(encoding="utf-8-sig"))
        if not isinstance(saved, dict) or saved.keys() - DEFAULTS.keys():
            raise ValueError("Settings must be an object containing only supported keys")
        config.update(saved)
    config.update({key: environment[key] for key in DEFAULTS if key in environment})
    config.update({key: value for key, value in overrides.items() if value is not None})
    raw_port = config["PORT"]
    if isinstance(raw_port, bool) or not str(raw_port).isdecimal():
        raise ValueError("PORT must be an integer between 1024 and 65535")
    port = int(raw_port)
    if not 1024 <= port <= 65535:
        raise ValueError("PORT must be between 1024 and 65535")
    config["PORT"] = str(port)
    for key in DEFAULTS.keys() - {"PORT"}:
        if not isinstance(config[key], str):
            raise ValueError(f"{key} must be a string")
    ipaddress.ip_address(config["BIND_HOST"])
    for proxy in config["TRUSTED_PROXY_IPS"].split(","):
        ipaddress.ip_network(proxy.strip(), strict=False)
    url = config["PUBLIC_BASE_URL"]
    if not url:
        host = config["BIND_HOST"]
        host = "localhost" if host in {"0.0.0.0", "::"} else host
        host = f"[{host}]" if ":" in host else host
        url = f"http://{host}:{port}"
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or "?" in url
        or "#" in url
        or any(character.isspace() or ord(character) < 32 for character in url)
        or parsed.port == 0
    ):
        raise ValueError("PUBLIC_BASE_URL must be an HTTP(S) origin, without login, path or query")
    config["PUBLIC_BASE_URL"] = url.rstrip("/")
    for key in ("AUDIO_DIR", "PIPER_MODEL_DIR"):
        if not config[key] and key == "AUDIO_DIR":
            raise ValueError("AUDIO_DIR must not be empty")
        path = Path(config[key] or DEFAULTS[key]).expanduser()
        config[key] = str((path if path.is_absolute() else root / path).resolve())
    database = make_url(normalize_database_url(config["DATABASE_URL"]))
    if database.get_backend_name() == "sqlite":
        if not database.database or database.database == ":memory:" or database.query:
            raise ValueError("Local launcher requires a persistent SQLite file without URI options")
        path = Path(database.database).expanduser()
        database = database.set(database=str((root / path).resolve()))
    elif database.get_backend_name() != "postgresql":
        raise ValueError("Supported databases: SQLite and PostgreSQL")
    config["DATABASE_URL"] = database.render_as_string(hide_password=False)
    return config


def check_database(database_url: str, root: Path = ROOT) -> dict:
    """Read-only connection prevents an incorrect path from creating an empty database."""
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        path = Path(url.database)
        if not path.is_file():
            raise ValueError(
                "Database missing. Run migration and seed explicitly; see local-windows.md"
            )
        engine = create_engine(
            "sqlite://",
            creator=lambda: sqlite3.connect(path.as_uri() + "?mode=ro", uri=True),
        )
    else:
        engine = create_engine(url, connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as connection:
            if url.get_backend_name() == "sqlite":
                connection.exec_driver_sql("PRAGMA query_only=ON")
            else:
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            config = Config(str(root / "alembic.ini"))
            config.set_main_option("script_location", str(root / "migrations"))
            expected = set(ScriptDirectory.from_config(config).get_heads())
            actual = set(MigrationContext.configure(connection).get_current_heads())
            if actual != expected:
                raise ValueError(
                    "Database migration is outdated. Back up, then run alembic upgrade head"
                )
            counts = {
                "admins": connection.scalar(text("SELECT count(*) FROM admin_users")),
                "locations": connection.scalar(
                    text("SELECT count(*) FROM locations WHERE is_ready")
                ),
                "narrations": connection.scalar(
                    text(
                        "SELECT count(*) FROM poi_narrations n JOIN locations l "
                        "ON l.id=n.location_id WHERE l.is_ready"
                    )
                ),
            }
            if not counts["admins"]:
                raise ValueError(
                    "No manager account. Run scripts.create_admin; see local-windows.md"
                )
            return counts
    finally:
        engine.dispose()


def preflight(config: dict) -> None:
    from app.core.exceptions import AppError
    from app.modules.audio.offline import OfflineSpeech
    from app.modules.audio.store import AudioStore

    counts = check_database(config["DATABASE_URL"])
    print(
        f"Database OK: {counts['locations']} published places, "
        f"{counts['narrations']} narrations, manager account present.",
        flush=True,
    )
    # AudioStore creates the writable cache directory, but does not alter existing files.
    store = AudioStore(config["AUDIO_DIR"])
    with tempfile.TemporaryFile(dir=store.root) as probe:
        probe.write(b"audio-cache-write-check")
    speech = OfflineSpeech(store, Path(config["PIPER_MODEL_DIR"]))
    for language in ("vi", "en", "ja"):
        try:
            speech.check(language)
        except AppError as error:
            raise ValueError(
                f"Offline voice {language} is not ready. Install requirements and run "
                "scripts.setup_offline_tts with the configured --directory; see local-windows.md"
            ) from error
    print("Offline voices OK: vi, en, ja (SHA-256 verified; no download).", flush=True)
    if not counts["locations"] or not counts["narrations"]:
        print("No published narrations yet. Add places and content in /admin.", flush=True)


def require_free_port(host: str, port: int) -> None:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind((host, port))
        except OSError as error:
            raise ValueError(
                f"Cannot listen on {host}:{port}. Stop the existing app or choose -Port."
            ) from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "local.settings.json")
    parser.add_argument("--port", type=int)
    parser.add_argument("--host")
    parser.add_argument("--public-url")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check", action="store_true")
    actions.add_argument("--prepare-audio", action="store_true")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
        print("Use Python 3.12 x64 with requirements-dev.txt installed.", file=sys.stderr)
        return 1
    try:
        if not args.config.is_file():
            raise ValueError("Settings file missing. Copy local.settings.example.json first.")
        config = load_configuration(
            ROOT,
            args.config,
            os.environ,
            {"PORT": args.port, "BIND_HOST": args.host, "PUBLIC_BASE_URL": args.public_url},
        )
        os.chdir(ROOT)
        os.environ.update(config)
        preflight(config)
        print(f"Visitor: {config['PUBLIC_BASE_URL']}/", flush=True)
        print(f"Manager: {config['PUBLIC_BASE_URL']}/admin", flush=True)
        print(f"QR page: {config['PUBLIC_BASE_URL']}/share", flush=True)
        if args.check:
            print("Configuration ready. No server started; port availability is checked on run.")
            return 0
        if args.prepare_audio:
            return subprocess.call([sys.executable, "-m", "scripts.prepare_narration_audio"])
        require_free_port(config["BIND_HOST"], int(config["PORT"]))
        print("Keep this terminal open. Ctrl+C stops the website.", flush=True)
        return subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                config["BIND_HOST"],
                "--port",
                config["PORT"],
                "--proxy-headers",
                "--forwarded-allow-ips",
                config["TRUSTED_PROXY_IPS"],
            ]
        )
    except (ValueError, ImportError, OSError) as error:
        # No connection URL / exception traceback: PostgreSQL credentials must stay private.
        print(f"Startup failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(
            f"Preflight failed ({type(error).__name__}). "
            "Check database/dependencies/voice setup in docs/local-windows.md.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
